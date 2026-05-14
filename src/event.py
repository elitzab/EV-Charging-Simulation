import heapq
from enum import Enum


class EventType(Enum):
    """
    Establish the types of events that can occcur.
    """
    ARRIVAL = 1         # Customer arrives at charging point
    CHARGING = 2        # Customer begins charging
    DEPARTURE = 3       # Customer leaves the charging point

class Event:
    def __init__(self, time, type, customer, station=None):
        self.time = time
        self.type = type
        self.customer = customer
        self.station = station

    def __lt__(self, other):
        return self.time < other.time

class FutureEventSet:
    """
    A priority queue-based container for managing future events in the simulation.

    Uses min-heap here.
    """
    def __init__(self):
        self._queue = []
    
    def add(self, event: Event):
        heapq.heappush(self._queue, event)
    
    def next(self) -> Event:
        return heapq.heappop(self._queue)
    
    def is_empty(self) -> bool:
        return len(self._queue) == 0
