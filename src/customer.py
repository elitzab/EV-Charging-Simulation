import random

class Customer:
    """
    Represents an EV or PHEV arriving at the parking lot
    """
    def __init__(self, cust_id: int, arrival_time: float, car_type: str, energy_needed: float, departure_time: float):
        self.id = cust_id                       
        self.arrival_time = arrival_time
        self.car_type = car_type                # EV or PHEV
        self.energy_needed = energy_needed      # total kWh needed to charge
        self.departure_time = departure_time

        self.energy_received = 0.0              # current charge received so far (kWh)
        self.station_start_time = None          # time when they plugged in
        self.station_end_time = None            # time when they unplugged

    def charge(self, max_charger_power: float, duration_minutes: float) -> float:
        """
        Simulates charging the vehicle over a specific duration of time.
        Return: energy added to the battery (kWh).
        """
        if self.is_charging_complete() or duration_minutes <= 0:
            return 0.0

        charging_rate = max_charger_power
        if self.car_type == "PHEV":
            charging_rate = min(max_charger_power, 3.7) # PHEVs chargers limited to ~3.7 kW

        hours = duration_minutes / 60.0
        possible_energy = charging_rate * hours

        energy_to_add = min(possible_energy, self.energy_needed - self.energy_received)
        
        self.energy_received += energy_to_add
        return energy_to_add

    def is_charging_complete(self) -> bool:
        """
        Return: True if the vehicle's energy needs are fully met.
        """
        return (self.energy_needed - self.energy_received) < 0.01
        
    def get_remaining_need(self) -> float:
        """
        Return: the remaining energy needed (kWh).
        """
        return max(0.0, self.energy_needed - self.energy_received)

