import math

class Station:
    """
    Represents a cluster of charging points. 

    The class tracks the station object and its occupancy by following the
    influx of parked cars.
    """
    def __init__(self, name, capacity = 2, panels = 14, panel_peak_kw = 0.4):
        self.name = name
        self.capacity = capacity        # number of parking spots
        self.occupied_spots = 0         # current parkings occupied
        self.waiting_queue = []         # customers blocked waiting for this station
        self.service_time_dist = None   # will be set from data, dk if relevant

        self.solar_peak_power = panels * panel_peak_kw  # Peak solar output in kW
        self.charger_power_rate = 11.0                  # Each active charger draws X kW

        self.total_solar_generated_kwh = 0.0
        self.total_grid_drawn_kwh = 0.0
    
    def occupy(self):
        if self.occupied_spots < self.capacity:
            self.occupied_spots += 1
            return True
        return False
    
    def release(self):
        if self.occupied_spots > 0:
            self.occupied_spots -= 1

    def get_solar_power(self, current_time_minutes: float) -> float:
        """
        Calculates the instantaneous solar power generation (kW) 
        using a synthetic sine wave peaking at 12:00.
        """
        hour = (current_time_minutes / 60.0) % 24
 
        if 6.0 < hour < 20.0: # = daylight hours
            # sine wave peaking at 12:00
            sine_value = math.sin(math.pi * (hour - 6.0) / 12.0)
            return self.solar_peak_power * sine_value
        return 0.0

    def calculate_energy_draw(self, current_time_minutes: float, delta_time_minutes: float):
        """
        Updates the total energy drawn (kWh) from solar vs grid over a time step.
        """
        if delta_time_minutes <= 0:
            return

        current_demand = self.occupied_spots * self.charger_power_rate
        current_solar = self.get_solar_power(current_time_minutes)

        time_step_hours = delta_time_minutes / 60.0

        solar_used = min(current_demand, current_solar)
        grid_used = max(0.0, current_demand - solar_used)

        self.total_solar_generated_kwh += solar_used * time_step_hours
        self.total_grid_drawn_kwh += grid_used * time_step_hours

    def has_waiting_customers(self) -> bool:
        return len(self.waiting_queue) > 0