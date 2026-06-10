import math

class Station:
    """
    Represents a cluster of charging points.
    """
    def __init__(self, name, station_type="solar", capacity=2, panels=14, panel_peak_kw=0.4,
             charger_power_rate=11.0, op_start=0.0, op_end=1440.0, solar_profile=None):
        self.name = name
        self.station_type = station_type    # "solar" or "grid"
        self.capacity = capacity            # number of charging spots
        self.occupied_spots = 0             # current spots occupied
        self.panels = panels
        self.solar_profile = solar_profile

        self.solar_peak_power = panels * panel_peak_kw if station_type == "solar" else 0.0
        self.charger_power_rate = charger_power_rate

        self.total_solar_generated_kwh = 0.0
        self.total_grid_drawn_kwh = 0.0

        # statistics
        self.op_start = op_start            # operating window
        self.op_end = op_end
        self.occupied_spot_minutes = 0.0    # total time spots are occupied (e.g. 2*30 + 1*60)
        self.hourly_solar_kwh = [0.0] * 24  # energy split per hour of day
        self.hourly_grid_kwh = [0.0] * 24

    def occupy(self):
        if self.occupied_spots < self.capacity:
            self.occupied_spots += 1
            return True
        return False

    def release(self):
        if self.occupied_spots > 0:
            self.occupied_spots -= 1

    def has_free_spot(self) -> bool:
        return self.occupied_spots < self.capacity

    def get_solar_power(self, current_time_minutes: float) -> float:
        if self.station_type != "solar":
         return 0.0

        if self.solar_profile is not None:
         return self.solar_profile.get_power_kw(current_time_minutes)

        return 0.0

    def grid_demand(self, current_time_minutes: float) -> float:
        """
        Grid draw (kW)
        """
        demand = self.occupied_spots * self.charger_power_rate
        solar = self.get_solar_power(current_time_minutes)
        return max(0.0, demand - solar)

    def calculate_energy_draw(self, t0: float, t1: float):
        """
        Updates the total energy drawn (kWh) from solar vs grid over [t0, t1].
        Solar is sampled at the interval midpoint
        """
        delta = t1 - t0
        if delta <= 0 or self.occupied_spots == 0:
            return

        mid = 0.5 * (t0 + t1)
        demand = self.occupied_spots * self.charger_power_rate
        solar = self.get_solar_power(mid)

        hours = delta / 60.0
        solar_used = min(demand, solar)
        grid_used = max(0.0, demand - solar_used)

        if grid_used < 0 or solar_used < 0:
            print(f"NEGATIVE: t0={t0:.1f} t1={t1:.1f} demand={demand:.3f} solar={solar:.3f} solar_used={solar_used:.3f} grid_used={grid_used:.3f}")

        self.total_solar_generated_kwh += solar_used * hours
        self.total_grid_drawn_kwh += grid_used * hours

        hour = int((mid // 60) % 24)
        self.hourly_solar_kwh[hour] += solar_used * hours
        self.hourly_grid_kwh[hour] += grid_used * hours

        if min(t1, self.op_end) > max(t0, self.op_start):
            self.occupied_spot_minutes += self.occupied_spots * (min(t1, self.op_end) - max(t0, self.op_start))

    def utilisation(self) -> float:
        """
        Return: fraction of spot*time occupied over the operating window
        """
        window = self.op_end - self.op_start
        denom = self.capacity * window
        return self.occupied_spot_minutes / denom if denom > 0 else 0.0
    
   
    