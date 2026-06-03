"""
Run this file to get the parameters of the distribution, used in the simulation, of the 
energy charged by vehicles. (Lognormal based on data/energy_distribution.py analyis)
"""
import os
import random
import pandas as pd

script_dir = os.path.dirname(os.path.abspath(__file__))
csv_path = os.path.join(script_dir, '..', 'data', '202410DatasetEVOfficeParking_v0.csv')

# caps, so draws are sensible
BEV_MIN, BEV_MAX = 2.0, 80.0
PHEV_MIN, PHEV_MAX = 1.0, 14.0


class EnergyDistribution:
    """
    Lognormal fit on daily energy percar. 
    sample(car_type) -- Returns: kWh needed
    (PHEVs draw from the same shape but clamped to a small-battery range)
    """
    def __init__(self, verbose=False):
        self.mu, self.sigma = self._fit(verbose)

    def _fit(self, verbose):
        try:
            df = pd.read_csv(csv_path, sep=';', low_memory=False)
            df['total_energy'] = pd.to_numeric(df['total_energy'], errors='coerce')
            df['day'] = pd.to_datetime(df['start_datetime'], errors='coerce').dt.date

            # some cars charged more than once a day, but the simulation assumes they only charge once
            # so we sum up the total energy they drew
            daily = (df.dropna(subset=['total_energy', 'day']).groupby(['EV_id_x', 'day'])['total_energy'].sum())
            daily = daily[daily > 0]

            import numpy as np
            logs = np.log(daily.values)
            mu, sigma = float(logs.mean()), float(logs.std())

            if verbose:
                print("=" * 50)
                print(f"Charging sessions:        {len(df)}")
                print(f"Car-days (energy needs):  {len(daily)}")
                print(f"Mean daily energy:        {daily.mean():.2f} kWh")
                print(f"Median daily energy:      {daily.median():.2f} kWh")
                print(f"Lognormal fit:            mu={mu:.3f}, sigma={sigma:.3f}")
                print("=" * 50)
            return mu, sigma
        except (FileNotFoundError, KeyError, ValueError):
            # parameters set to results drawn from data/energy_distribution.py
            if verbose:
                print("energy_distribution: dataset not found, using fallback params")
            return 2.81, 0.76

    def sample(self, car_type="BEV") -> float:
        value = random.lognormvariate(self.mu, self.sigma)
        if car_type == "PHEV":
            return min(max(value, PHEV_MIN), PHEV_MAX)
        return min(max(value, BEV_MIN), BEV_MAX)


if __name__ == "__main__":
    EnergyDistribution(verbose=True)