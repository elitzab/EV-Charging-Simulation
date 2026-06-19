"""
Run to get a .png file showing the distribution of daily energy charged per EV,
as used in the simulation (lognormal fit on daily totals per car).

! dataset 202410DatasetEVOfficeParking_v0.csv needed (see README.md)
"""
import os
import sys
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from scipy.stats import lognorm

script_dir = os.path.dirname(os.path.abspath(__file__))
csv_path   = os.path.join(script_dir, '202410DatasetEVOfficeParking_v0.csv')

sys.path.append(os.path.join(script_dir, '..', 'src'))
from extract_energy_distr import EnergyDistribution

# load and aggregate daily totals per car (same as the simulation does)
df = pd.read_csv(csv_path, sep=';', low_memory=False)
df['total_energy'] = pd.to_numeric(df['total_energy'], errors='coerce')
df['day'] = pd.to_datetime(df['start_datetime'], errors='coerce').dt.date

daily = (df.dropna(subset=['total_energy', 'day'])
           .groupby(['EV_id_x', 'day'])['total_energy'].sum())
daily = daily[daily > 0]

# get fitted parameters from the simulation's distribution
dist = EnergyDistribution(verbose=True)
mu, sigma = dist.mu, dist.sigma

# plot
fig, ax = plt.subplots(figsize=(9, 4.5))

cap = daily.quantile(0.99)
daily_clipped = daily[daily <= cap]

ax.hist(daily_clipped.values, bins=60, density=True, color="#2D6D5F", alpha=0.75,
        label=f'Observed daily energy per car')

x = np.linspace(0.1, cap, 400)
ax.plot(x, lognorm.pdf(x, s=sigma, scale=np.exp(mu)),
        color="#FFB20A", linewidth=2,
        label=f'Lognormal fit (μ={mu:.2f}, σ={sigma:.2f})')

ax.set_xlim(0, cap)

ax.axvline(daily.mean(), color="#DD9E00", linewidth=1.5, linestyle='--',
           label=f'Mean = {daily.mean():.1f} kWh')
ax.axvline(daily.median(), color="#000000", linewidth=1.5, linestyle='--',
           label=f'Median = {daily.median():.1f} kWh')

ax.set_xlabel('Energy charged per car per day (kWh)', size=12)
ax.set_ylabel('Density', size=12)
ax.set_title('Daily EV Charging Energy Distribution', fontsize=14, weight='bold')
ax.legend(fontsize=9)
ax.grid(axis='y', alpha=0.3)
ax.spines['top'].set_visible(False)
ax.spines['right'].set_visible(False)

fig.tight_layout()
out_path = os.path.join(script_dir, '4.4 - charged energy.png')
fig.savefig(out_path, dpi=150, bbox_inches='tight')
plt.close(fig)
print(f"Saved: {out_path}")