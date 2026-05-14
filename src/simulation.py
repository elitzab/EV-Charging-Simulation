import random
from collections import deque
import os
import sys

from event import FutureEventSet
from event import Event
from event import EventType
from customer import Customer
from station import Station


class Simulation:
    def __init__(self, stations: dict, arrival_dist, station_service_dists: dict):
        """
        Initialize the simulation environment.
        
        :param stations: Dictionary mapping station names to Station objects
        :param arrival_dist: Distribution object for customer arrival times
        :param station_service_dists: Dictionary mapping station names to service time distributions
        """
        self.fes = FutureEventSet()     # priority queue
        self.clock = 0.0
        self.stations = stations        # dict: name -> Station
        self.arrival_dist = arrival_dist
        self.station_service_dists = station_service_dists
        self.abandoned_customers = 0
        self.is_open = False
        
        # Statistics for the analysis later
        self.completed_customers = []
        self.total_customers = 0
        self.last_queue_record_time = 0.0

    def schedule(self, event: Event):
        """
        Add an event to the future event set.
        
        :param event: Event object to be scheduled
        """
        self.fes.add(event)
    
    def add_to_queue(customer: Customer, station: Station):
        """
        Add customer to the queue.
        :param customer: customer object to add to the queue.
        """
        station.waiting_queue.append(customer)
    
    def pop_from_entrance_queue(self, station):
        """
        Pop next customer from the queue.

        :return: next Customer object, or None if queue empty
        """
        while station.waiting_queue:
            customer = station.waiting_queue.popleft()
            return customer
            
        return None
    
    
    def _handle_arrival(self):
        """
        Handle customer arrival at some station.
        
        Creates a new customer, adds them to a queue and schedules next arrival.
        """
        
        # Create new customer
        self.total_customers += 1

        #TODO: car_type = ?

        customer = Customer(
            cust_id=self.total_customers,
            arrival_time=self.clock,
            # TODO: car_type=car_type,
        )

        # TODO: customer.cur_station.waiting_queue(customer)
        
        # Schedule next arrival
        next_arrival_time = self.arrival_dist.sample(self.clock)
        self.schedule(Event(
            time=self.clock + next_arrival_time,
            type=EventType.ARRIVAL,
            customer=None
        ))
    
    def _handle_station_departure(self, event):
        """
        Handle customer finishing at a station.
        
        Release the parking spot, attempts to release blocked
        customers and moves customer to their next station.
        
        :param event: event object containing the customer and station
        """
        # TODO: adapt to EV charging scenario
        customer = event.customer
        current_station_name = event.station_name
        next_station_name = customer.get_next_station()
        
        if next_station_name:
            next_station = self.stations[next_station_name]
            # Try to enter next station
            if next_station.can_enter(customer.car_type):
                # Release old spot(s)
                self.stations[current_station_name].release(customer)
                
                # Move to next station
                customer.advance_to_next_station()
                next_station.occupy(customer.car_type, customer.is_priority)
                customer.station_entry_times[next_station] = self.clock

                # Schedule departure from next station
                service_time = self.station_service_dists[next_station_name][customer.car_type].sample()
                self.schedule(Event(
                    time=self.clock + service_time,
                    type=EventType.DEPARTURE,
                    customer=customer,
                    station_name=next_station_name
                ))

                self._release_blocked_customers(current_station_name)
            else:
                # Blocked, so add to waiting queue of next station
                customer.blocking_at_station = current_station_name
                next_station.waiting_queue.append(customer)
        else:
            self.stations[current_station_name].release(customer.car_type)
            self._release_blocked_customers(current_station_name)

            self._complete_customer(customer)
    
    def _release_blocked_customers(self, station_name: str):
        """
        Release blocked customers waiting for a station.
        
        Processes the waiting queue in order, allowing customers to enter
        the station as capacity becomes available.
        
        :param station_name: Name of the station that has freed up capacity
        """
        # TODO
    
    def _complete_customer(self, customer: Customer):
        """
        Record final sojourn time and statistics for a completed customer.
        
        :param customer: Customer object who has finished all waste disposal
        """
        # TODO

    def run(self, duration: float):
        """
        Run simulation for specified duration with optional improvement parameters.
        
        :param duration: total simulation time in minutes
        """
        
        # Schedule first arrival
        first_arrival_time = self.arrival_dist.sample(0)
        self.schedule(Event(
            time=first_arrival_time,
            type=EventType.ARRIVAL,
            customer=None
        ))
        
        self.last_queue_record_time = self.clock
        
        while not self.fes.is_empty() and self.clock < duration:
            event = self.fes.next()
            
            self.clock = event.time
            
            if event.type == EventType.ARRIVAL:
                self._handle_arrival()
            elif event.type == EventType.CHARGING:
                self._handle_gate_departure(event)
            elif event.type == EventType.DEPARTURE:
                self._handle_station_departure(event)

