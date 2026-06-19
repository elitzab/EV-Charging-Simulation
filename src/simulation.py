"""
(Run main.py to get results)
"""
import random
from collections import deque

from event import FutureEventSet, Event, EventType
from customer import Customer
from station import Station

class Simulation:
    def __init__(self, stations: list, arrival_dist, energy_dist,
                 work_duration_dist, config, verbose=False):
        self.fes = FutureEventSet()     # priority queue
        self.clock = config['sim_start_min']
        self.stations = stations        # list, ordered solar-first
        self.arrival_dist = arrival_dist
        self.energy_dist = energy_dist
        self.work_duration_dist = work_duration_dist
        self.config = config
        self.verbose = verbose

        self.waiting_queue = deque()
        self.total_customers = 0
        self.completed_customers = []
        self.abandoned_customers = 0    # queued, but left work without charging
        self.last_record_time = self.clock
        self.peak_grid_kw = 0.0
        self.history = []               # monitor snapshots for the plot

    def schedule(self, event: Event):
        self.fes.add(event)

    def _charge_rate(self, customer: Customer) -> float:
        """
        Actual charging rate (kW): PHEVs -- capped, EVs -- full charger
        """
        rate = self.config['charger_power_rate']
        if customer.car_type == "PHEV":
            rate = min(rate, self.config['phev_max_charge_kw'])
        return rate

    def _generate_synthetic_customer(self) -> Customer:
        """
        Helper to generate a random customer
        """
        self.total_customers += 1

        is_bev = random.random() >= self.config['phev_fraction']
        car_type = "BEV" if is_bev else "PHEV"

        energy_needed = self.energy_dist.sample(car_type)

        work_duration = self.work_duration_dist.sample()
        departure_time = min(self.clock + work_duration, self.config['monitor_end_min'])

        return Customer(
            cust_id=self.total_customers,
            arrival_time=self.clock,
            car_type=car_type,
            energy_needed=energy_needed,
            departure_time=departure_time
        )

    def _find_free_station(self):
        """
        Returns: first station with a free spot (solar-first ordering), else None
        """
        for station in self.stations:
            if station.has_free_spot():
                return station
        return None

    def _record_energy(self, now: float):
        """
        Helper for statistics: records energy drawn so far
        """
        for station in self.stations:
            station.calculate_energy_draw(self.last_record_time, now)
        self.last_record_time = now

    def _start_charging(self, customer: Customer, station: Station):
        """
        Plug a customer into a station and schedule its charging-complete event
        (the customer's departure event is scheduled separately upon arrival)
        """
        station.occupy()
        customer.station = station
        customer.station_start_time = self.clock

        charge_rate = self._charge_rate(customer)
        charge_minutes = (customer.get_remaining_need() / charge_rate) * 60.0
        completion_time = self.clock + charge_minutes

        if completion_time < customer.departure_time:
            self.schedule(Event(time=completion_time, type=EventType.CHARGING,
                                customer=customer, station=station))
            if self.verbose:
                print(f"  -> Customer {customer.id} charging at {station.name}. Finishes {completion_time:.1f}")
        elif self.verbose:
            print(f"  -> Customer {customer.id} charging at {station.name}. Leaves partial at {customer.departure_time:.1f}")

    def _handle_arrival(self):
        """
        Handles a vehicle arriving at the parking lot
        """
        customer = self._generate_synthetic_customer()

        if self.verbose:
            print(f"[{self.clock:.1f}:] Customer {customer.id} ({customer.car_type}). "
                  f"{customer.energy_needed:.1f} kWh. Departure at {customer.departure_time:.1f}")

        ### S ### schedule departure
        self.schedule(Event(time=customer.departure_time, type=EventType.DEPARTURE,
                            customer=customer))

        # assign to a free spot, or join the queue
        station = self._find_free_station()
        if station is not None:
            self._start_charging(customer, station)
        else:
            self.waiting_queue.append(customer)
            if self.verbose:
                print(f"  -> Joined the waiting queue (length: {len(self.waiting_queue)})")

        ### S ### schedule next arrival
        next_arrival_time = self.clock + self.arrival_dist.sample(self.clock)
        if next_arrival_time <= self.config['arrival_cutoff_min']: # = arrival before 18:30
            self.schedule(Event(time=next_arrival_time, type=EventType.ARRIVAL, customer=None))

    def _handle_charging_complete(self, event):
        """
        Handles the event where a car finishes charging.
        Assumed: the driver moves their car immediately to a regular parking spot,
        releasing the charger
        """
        customer = event.customer
        station = event.station

        if customer.station_end_time is not None:
            return

        charge_rate = self._charge_rate(customer)
        customer.charge(charge_rate, self.clock - customer.station_start_time)
        customer.station_end_time = self.clock

        if self.verbose:
            print(f"[{self.clock:.1f}:] Customer {customer.id} ({customer.car_type}) "
                  f"charged {customer.energy_received:.1f} kWh")

        station.release()
        self._complete_customer(customer)
        self._process_queue()

    def _handle_workplace_departure(self, event):
        """
        Handles the event where an employee leaves work at the end of the day.
            - if they were still plugged in, they unplug
            - if they never got a spot, they leave the queue
        """
        customer = event.customer

        if customer.station_end_time is not None: # = already left
            return

        if customer.station_start_time is None: # = waiting, never charged
            if customer in self.waiting_queue:
                self.waiting_queue.remove(customer)
            customer.station_end_time = self.clock
            self.abandoned_customers += 1
            if self.verbose:
                print(f"[{self.clock:.1f}:] Customer {customer.id} left WITHOUT charging.")
            self._complete_customer(customer)
            return

        # if currently charging: take whatever energy they got before leaving
        charge_rate = self._charge_rate(customer)
        customer.charge(charge_rate, self.clock - customer.station_start_time)
        customer.station_end_time = self.clock

        if self.verbose:
            print(f"[{self.clock:.1f}:] Customer {customer.id} ({customer.car_type}) left. "
                  f"Charged {customer.energy_received:.1f}/{customer.energy_needed:.1f} kWh.")

        customer.station.release()
        self._complete_customer(customer)
        self._process_queue()

    def _handle_monitor(self):
        """
        Periodic sampler: records peak grid demand for statistics,
        and reschedules itself
        """
        grid_kw = sum(s.grid_demand(self.clock) for s in self.stations)
        solar_kw = sum(s.get_solar_power(self.clock) for s in self.stations)
        self.peak_grid_kw = max(self.peak_grid_kw, grid_kw)

        self.history.append({
            'time': self.clock,
            'queue': len(self.waiting_queue),
            'occupied': sum(s.occupied_spots for s in self.stations),
            'grid_kw': grid_kw,
            'solar_kw': solar_kw,
        })

        ### S ### schedule next snapshot
        next_time = self.clock + self.config['monitor_interval_min']
        if next_time <= self.config['monitor_end_min']:
            self.schedule(Event(time=next_time, type=EventType.MONITOR, customer=None))

    def _process_queue(self):
        """
        Assign queued customers to any free spots (FIFO)
        """
        while self.waiting_queue:
            station = self._find_free_station()
            if station is None:
                break
            next_customer = self.waiting_queue.popleft()
            self._start_charging(next_customer, station)

    def _complete_customer(self, customer: Customer):
        self.completed_customers.append(customer)

    
    # ~~~~~~~ RUN METHOD ~~~~~~~
    def run(self):
        """
        Runs the simulation loop until the future event set is empty.
        """
        first_arrival_time = self.clock + self.arrival_dist.sample(self.clock)
        self.schedule(Event(time=first_arrival_time, type=EventType.ARRIVAL, customer=None))
        self.schedule(Event(time=self.clock, type=EventType.MONITOR, customer=None))

        self.last_record_time = self.clock

        while not self.fes.is_empty():
            event = self.fes.next()
            self.clock = event.time
            self._record_energy(self.clock)

            if event.type == EventType.ARRIVAL:
                self._handle_arrival()
            elif event.type == EventType.CHARGING:
                self._handle_charging_complete(event)
            elif event.type == EventType.DEPARTURE:
                self._handle_workplace_departure(event)
            elif event.type == EventType.MONITOR:
                self._handle_monitor()


    # ~~~~~~~ METRICS ~~~~~~~
    def compute_metrics(self) -> dict:
        """
        (Used for the comparison of scenarios)
        """
        served = [c for c in self.completed_customers if c.station_start_time is not None]
        fully = [c for c in served if c.is_charging_complete()]
        waits = [c.station_start_time - c.arrival_time for c in served]

        solar_stations = [s for s in self.stations if s.station_type == "solar"]
        grid_stations = [s for s in self.stations if s.station_type == "grid"]

        total_solar = sum(s.total_solar_generated_kwh for s in self.stations)
        total_grid = sum(s.total_grid_drawn_kwh for s in self.stations)
        total_battery = sum(s.total_battery_discharged_kwh for s in self.stations)
        grid_at_solar = sum(s.total_grid_drawn_kwh for s in solar_stations)
        grid_at_grid = sum(s.total_grid_drawn_kwh for s in grid_stations)
        delivered_by_solar_stations = sum(s.total_solar_generated_kwh + s.total_grid_drawn_kwh
                                          for s in solar_stations)

        def util(group):
            cap = sum(s.capacity for s in group)
            if cap == 0:
                return 0.0
            return sum(s.utilisation() * s.capacity for s in group) / cap

        return {
            'arrived':              self.total_customers,
            'served':               len(served),
            'abandoned':            self.abandoned_customers,
            'fully_charged':        len(fully),
            'prop_fully_charged':   len(fully) / len(served) if served else 0.0,
            'avg_wait_min':         sum(waits) / len(waits) if waits else 0.0,
            'total_solar_kwh':      total_solar,
            'total_grid_kwh':       total_grid,
            'grid_kwh_solar_stns':  grid_at_solar,
            'grid_kwh_grid_stns':   grid_at_grid,
            'total_delivered_kwh':  total_solar + total_grid + total_battery,
            'solar_station_kwh':    sum(s.total_solar_generated_kwh + s.total_grid_drawn_kwh 
                            + s.total_battery_discharged_kwh for s in solar_stations),
            'total_battery_kwh':    total_battery,
            'peak_grid_kw':         self.peak_grid_kw,
            'util_solar':           util(solar_stations),
            'util_grid':            util(grid_stations),
        }