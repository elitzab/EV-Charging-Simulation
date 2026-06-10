import os
import pandas as pd

script_dir = os.path.dirname(os.path.abspath(__file__))
csv_path = os.path.join(script_dir, '..', 'data', 'seasonal_solar_profile_per_panel.csv')


class SolarProfile:
    """
    Gives available solar power based on season and hour.
    Multiplies the seasonal solar profile csv by the number of panels used in the simulation.
    """

    def __init__(self, season="summer", num_panels=14):
        self.season = season
        self.num_panels = num_panels

        df = pd.read_csv(csv_path)
        self.lookup = {
            (row.season, int(row.hour)): float(row.kW_per_panel)
            for row in df.itertuples()
        }

    def get_power_kw(self, clock_min):
        
        hour = int(clock_min // 60)

        kw_per_panel = self.lookup.get((self.season, hour), 0.0)
        return kw_per_panel * self.num_panels