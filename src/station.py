class Station:
    """
    Represents a cluster of charging points. 

    The class tracks the station object and its occupancy by following the
    influx of parked cars.
    """
    def __init__(self, name: str, capacity: int):
        self.name = name
        self.capacity = capacity        # number of parking spots
        self.occupied_spots = 0         # current parkings occupied
        self.waiting_queue = []         # customers blocked waiting for this station
        self.service_time_dist = None   # will be set from data, dk if relevant
    
    def occupy(self):
        self.occupied_spots += 1
    
    def release(self):
        self.occupied_spots -= 1

    def has_waiting_customers(self) -> bool:
        return len(self.waiting_queue) > 0