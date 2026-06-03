"""
Run to get a .png file showing the requested-energy distribution.
Outputs:
    - parameters for different distribution fits + their scores.

! dataset 202410DatasetEVOfficeParking_v0.csv needed (see README.md)
"""
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import os

from scipy.stats import norm, gamma, lognorm, weibull_min, kstest

script_dir = os.path.dirname(os.path.abspath(__file__))
df = pd.read_csv(os.path.join(script_dir, '202410DatasetEVOfficeParking_v0.csv'), sep=";")

energy = df["total_energy"]

#print(energy.head())
#print(df.columns)

# removes missing and invalid values
energy = energy.dropna()
energy = energy[energy > 0]

# distributions to compare
distributions = {
    "Normal": norm,
    "Gamma": gamma,
    "Log-normal": lognorm,
    "Weibull": weibull_min
}

fit_results = {}

# fits each distribution to the data
for name, dist in distributions.items():
    params = dist.fit(energy)
    fit_results[name] = params
    print(name, params)

x = np.linspace(energy.min(), energy.max(), 500)

# plots the data histogram
plt.hist(energy, bins=50, density=True, alpha=0.5, label="Real data")

# plots the fitted probability density functions
for name, dist in distributions.items():
    params = fit_results[name]
    y = dist.pdf(x, *params)
    plt.plot(x, y, label=name)


plt.xlabel("Energy used per charging session (kWh)")
plt.ylabel("Density")
plt.title("Fitted distributions")
plt.legend()

out_path = os.path.join(script_dir, 'energy_distribution_plot.png')
plt.savefig(out_path, dpi=150, bbox_inches='tight')
plt.close()
print(f"Plot saved to: {out_path}")

best_dist = None
best_stat = np.inf

print("\nGoodness of fit:")

# compares distributions using the KS test
for name, dist in distributions.items():
    params = fit_results[name]
    ks_stat, p_value = kstest(energy, dist.name, args=params)

    print(f"{name}:")
    print(f"    KS statistic = {ks_stat:.5f}")
    print(f"    p-value      = {p_value:.5e}")

    if ks_stat < best_stat:
        best_stat = ks_stat
        best_dist = name

print("\nBest fit:")
print(best_dist)

print("Parameters:")
print(fit_results[best_dist])