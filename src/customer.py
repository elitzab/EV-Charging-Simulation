import random

class Customer:
    """
    Represents a customer arriving at the WRP. 
    """
    def __init__(self, cust_id, arrival_time, car_type, needs, departure_time):
        self.id = cust_id                       
        self.arrival_time = arrival_time        # at work
        self.car_type = car_type                # hybrid?
        self.needs = needs                      # electricity
        self.departure_time = departure_time    # from work
        self.station_start_time = None          # start of charging
        self.station_end_time = None            # end of charging

