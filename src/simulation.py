import random
from collections import deque
import sys

from event import FutureEventSet, Event, EventType
from customer import Customer
from station import Station

class Simulation:
    def __init__(self, stations: dict, arrival_dist, station_service_dists: dict = None):
        self.fes = FutureEventSet()     # priority queue
        self.clock = 0.0
        self.stations = stations        # dict: name -> Station
        self.arrival_dist = arrival_dist

        self.total_customers = 0
        self.completed_customers = []
        self.abandoned_customers = 0
        self.last_energy_record_time = 0.0

    def schedule(self, event: Event):
        self.fes.add(event)

    def _generate_synthetic_customer(self) -> Customer:
        """
        Helper to generate a random customer with EV or PHEV properties
        """
        self.total_customers += 1

        is_bev = random.random() < 0.70
        car_type = "BEV" if is_bev else "PHEV"

        if is_bev:
            energy_needed = random.uniform(15.0, 45.0) # between 15 and 45 kWh to top up
        else:
            energy_needed = random.uniform(5.0, 12.0) # between 5 and 12 kWh to top up

        work_duration = random.normalvariate(510.0, 30.0) # TODO: fix values 
        departure_time = self.clock + work_duration
        
        return Customer(
            cust_id=self.total_customers,
            arrival_time=self.clock,
            car_type=car_type,
            energy_needed=energy_needed,
            departure_time=departure_time
        )

    def _handle_arrival(self):
        """
        Handles a vehicle arriving at the parking lot
        """
        customer = self._generate_synthetic_customer()

        station = self.stations["Workplace_Station"]
        
        print(f"[{self.clock:.1f}:] Customer {customer.id} ({customer.car_type}). {customer.energy_needed:.1f} kWh. Departure at {customer.departure_time:.1f}")
        
        # updating energy consumption of the station:
        time_elapsed = self.clock - self.last_energy_record_time
        station.calculate_energy_draw(self.clock, time_elapsed)
        self.last_energy_record_time = self.clock

        # try to occupy a charging spot
        if station.occupied_spots < station.capacity:
            station.occupy()
            customer.station_start_time = self.clock
            
            charge_rate = station.charger_power_rate if customer.car_type == "BEV" else 3.7
            charge_duration_hours = customer.energy_needed / charge_rate
            charge_duration_minutes = charge_duration_hours * 60.0
            
            completion_time = self.clock + charge_duration_minutes

            if completion_time < customer.departure_time: # charging finishes before they leave work
                self.schedule(Event(time=completion_time, type=EventType.CHARGING, customer=customer, station=station))
            else:
                self.schedule(Event(time=customer.departure_time, type=EventType.DEPARTURE, customer=customer, station=station))
            
            print(f"  -> Started charging. Will finish at {completion_time:.1f}")
        else:
            # no spots available, so join the queue
            station.waiting_queue.append(customer)
            print(f"  -> Joined the waiting queue (length: {len(station.waiting_queue)})")

        next_arrival_delay = self.arrival_dist.sample(self.clock)
        self.schedule(Event(
            time=self.clock + next_arrival_delay,
            type=EventType.ARRIVAL,
            customer=None
        ))

    def _handle_charging_complete(self, event):
        """
        Handles the event where a car finishes charging.
        The driver moves their car immediately to a regular parking spot,
        releasing the charger
        """
        customer = event.customer
        station = event.station

        if customer.station_end_time is not None:
            return

        time_elapsed = self.clock - self.last_energy_record_time
        station.calculate_energy_draw(self.clock, time_elapsed)
        self.last_energy_record_time = self.clock

        # charge the customer's battery
        charge_rate = station.charger_power_rate if customer.car_type == "BEV" else 3.7
        actual_time_charging = self.clock - customer.station_start_time
        customer.charge(charge_rate, actual_time_charging)
        
        customer.station_end_time = self.clock
        
        print(f"[{self.clock:.1f}:] Customer {customer.id} ({customer.car_type}) charged {customer.energy_received:.1f} kWh")

        station.release()
        self._complete_customer(customer)
        self._process_queue(station)


    def _handle_workplace_departure(self, event):
        """
        Handles the event where an employee leaves work at the end of the day.
        If they were still plugged in, they unplug (even if not fully charged).
        """
        customer = event.customer
        station = event.station

        if customer.station_end_time is not None:
            return

        time_elapsed = self.clock - self.last_energy_record_time
        station.calculate_energy_draw(self.clock, time_elapsed)
        self.last_energy_record_time = self.clock

        # charge the battery with whatever energy they got before leaving
        charge_rate = station.charger_power_rate if customer.car_type == "BEV" else 3.7
        actual_time_charging = self.clock - customer.station_start_time
        customer.charge(charge_rate, actual_time_charging)
        
        customer.station_end_time = self.clock
        
        print(f"[{self.clock:.1f}:] Customer {customer.id} ({customer.car_type}) left. Charged to {customer.energy_received:.1f}/{customer.energy_needed:.1f} kWh.")

        station.release()
        self._complete_customer(customer)
        self._process_queue(station)


    def _process_queue(self, station: Station):
        """
        Checks the queue and starts charging the next customer if a spot is free
        """
        if len(station.waiting_queue) > 0 and station.occupied_spots < station.capacity:
            next_customer = station.waiting_queue.pop(0)
            
            station.occupy()
            next_customer.station_start_time = self.clock

            charge_rate = station.charger_power_rate if next_customer.car_type == "BEV" else 3.7
            remaining_need = next_customer.get_remaining_need()
            charge_duration_hours = remaining_need / charge_rate
            charge_duration_minutes = charge_duration_hours * 60.0
            
            completion_time = self.clock + charge_duration_minutes

            if completion_time < next_customer.departure_time: # charging finished before they leave work
                self.schedule(Event(time=completion_time, type=EventType.CHARGING, customer=next_customer, station=station))
                print(f"  -> Customer {next_customer.id} started charging. Will finish at {completion_time:.1f}")
            else:
                self.schedule(Event(time=next_customer.departure_time, type=EventType.DEPARTURE, customer=next_customer, station=station))
                print(f"  -> Customer {next_customer.id} started charging. Will depart partially charged at {next_customer.departure_time:.1f}")


    def _complete_customer(self, customer: Customer):
        self.completed_customers.append(customer)

    # ~~~~~~~ RUN METHOD ~~~~~~~

    def run(self, duration: float):
        """
        Runs the simulation loop.
        """
        first_arrival_time = self.arrival_dist.sample(420.0) # = 7:00
        self.schedule(Event(
            time=first_arrival_time,
            type=EventType.ARRIVAL,
            customer=None
        ))
        
        self.last_energy_record_time = self.clock
        
        while not self.fes.is_empty() and self.clock < duration:
            event = self.fes.next()
            self.clock = event.time
            
            if event.type == EventType.ARRIVAL:
                self._handle_arrival()
            elif event.type == EventType.CHARGING:
                self._handle_charging_complete(event)
            elif event.type == EventType.DEPARTURE:
                self._handle_workplace_departure(event)