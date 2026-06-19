"""
Run to get .png files showing the arrival and departure distributions.
Outputs:
    - arrivals_model_plot.png: observed vs piecewise Poisson model
    - arrivals_vs_departures_plot.png: arrivals vs departures comparison
    - number of BEV and PHEV in the dataset (restricted to Noord-Brabant)

! dataset odin_2022.csv needed (see README.md)
"""
import os
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
import random

# load data
script_dir = os.path.dirname(os.path.abspath(__file__))
csv_path   = os.path.join(script_dir, 'odin_2022.csv')

df = pd.read_csv(csv_path, sep=';', low_memory=False, encoding='latin1')

num_cols = ['Doel', 'MotiefV', 'Hvm', 'AankProv', 'VertProv',
            'AankUur', 'AankMin', 'VertUur', 'VertMin',
            'BrandstofPa1', 'XBrandstofPa1', 'BrandstofEPa1']
for col in num_cols:
    if col in df.columns:
        df[col] = pd.to_numeric(df[col], errors='coerce')

# car commuters arriving in Noord-Brabant for work
all_arr = df[(df['Doel'] == 2) & (df['Hvm'] == 1) & (df['AankProv'] == 11)].copy()
all_arr = all_arr.dropna(subset=['AankUur', 'AankMin'])
all_arr['arrival_min'] = all_arr['AankUur'] * 60 + all_arr['AankMin']

# BrandstofEPa1 == 1 (fully electric), == 2 (hybrid)
ev_arr   = all_arr[all_arr['BrandstofEPa1'].isin([1, 2])].copy()
bev_arr  = all_arr[all_arr['BrandstofEPa1'] == 1].copy()
phev_arr = all_arr[all_arr['BrandstofEPa1'] == 2].copy()

# Departures
all_dep = df[(df['Doel'] == 1) & (df['MotiefV'] == 1) &
             (df['Hvm'] == 1) & (df['VertProv'] == 11)].copy()
all_dep = all_dep.dropna(subset=['VertUur', 'VertMin'])
all_dep['departure_min'] = all_dep['VertUur'] * 60 + all_dep['VertMin']

print(f"All car arrivals:           {len(all_arr)}")
print(f"    EV/PHEV:                {len(ev_arr)}  ({len(ev_arr)/len(all_arr)*100:.1f}%)")
print(f"    BEV (fully electric):   {len(bev_arr)}")
print(f"    PHEV (plug-in hybrid):  {len(phev_arr)}")

# Fit
SIM_START = 390   # 06:30 in minutes since midnight
windows = [
    (SIM_START,         SIM_START + 45,  "early\n06:30–07:15",  "#6C9536"),
    (SIM_START + 45,    SIM_START + 75, "\n07:15-07:45", "#8D9536" ),
    (SIM_START + 75,    SIM_START + 135, "peak\n07:45-08:45", "#DFA323" ),
    (SIM_START + 135,   SIM_START + 165, "\n08:45-09:15", "#A55279" ),
    (SIM_START + 165,   SIM_START + 225, "late\n09:15–10:15",  "#573377"),
    (SIM_START + 225,   SIM_START + 720, "tail\n10:15–18:30",  "#334F77")
    # (SIM_START + 45,    SIM_START + 165, "peak\n07:15–09:15",  "#DFA323"),
    # (SIM_START + 165,   SIM_START + 720, "tail\n09:15–18:30",  "#334F77"),
]

# compute rates
arrival_rates = []
for (w_start, w_end, label, color) in windows:
    count = ((all_arr['arrival_min'] >= w_start) &
             (all_arr['arrival_min'] <  w_end)).sum()
    duration_min = w_end - w_start
    rate = count / duration_min
    arrival_rates.append({
        'label': label, 'start': w_start, 'end': w_end,
        'rate': rate, 'color': color,
        'count': int(count),
    })

# simulated arrivals from piecewise Poisson
random.seed(42)
N_SIM_DAYS = 50

def simulate_arrivals(rates, n_days, scale=1.0):
    times = []
    for _ in range(n_days):
        for r in rates:
            t = r['start']
            scaled_rate = r['rate'] * scale
            while t < r['end']:
                dt = random.expovariate(scaled_rate)
                t += dt
                if t < r['end']:
                    times.append(t)
    return np.array(times)

sim_times = simulate_arrivals(arrival_rates, N_SIM_DAYS)

# shared settings
BIN_WIDTH = 15
bins = np.arange(300, 1140 + BIN_WIDTH, BIN_WIDTH)

def min_to_label(m):
    return f"{int(m//60):02d}:{int(m%60):02d}"

x_ticks      = np.arange(300, 1141, 60)
x_ticklabels = [min_to_label(m) for m in x_ticks]


# PLOT: Arrivals vs Piecewise Poisson Model
fig, ax = plt.subplots(figsize=(12, 6))

counts_obs, _, patches = ax.hist(
    all_arr['arrival_min'], bins=bins,
    color="#7BB350", alpha=0.75, label='Observed arrivals'
)
sim_counts, _ = np.histogram(sim_times, bins=bins)
ax.stairs(sim_counts / N_SIM_DAYS, bins, color="#000000",
          linewidth=2, label='Simulated arrivals')

total_observed   = len(all_arr)
total_sim_per_day = sum(r['rate'] * (r['end'] - r['start']) for r in arrival_rates)

y_max = counts_obs.max()

for r in arrival_rates:
    expected_per_bin = r['rate'] * BIN_WIDTH
    # ax.hlines(expected_per_bin, r['start'], r['end'],
    #           colors=r['color'], linewidths=2.5, linestyles='--')
    ax.axvspan(r['start'], r['end'], alpha=0.08, color=r['color'])
    mid = (r['start'] + r['end']) / 2

    ax.text(mid, y_max * 0.92, r['label'].split('\n')[0],
            ha='center', va='top', fontsize=10, color=r['color'], fontweight='bold')

for w_start, w_end, _, color in windows:
    ax.axvline(w_start, color=color, linewidth=1, linestyle=':')
ax.axvline(windows[-1][1], color=windows[-1][3], linewidth=1, linestyle=':')

# rate annotations
for i, r in enumerate(arrival_rates):
    mid = (r['start'] + r['end']) / 2
    y_pos = 6 if (i == 1 or i == 3) else 2
    ax.text(mid, y_pos, f"λ={r['rate']:.2f}/min",
            ha='center', va='bottom', fontsize=7.5, color=r['color'],
            bbox=dict(boxstyle='round,pad=0.2', fc='white', alpha=0.7))

ax.set_xlim(300, 1140)
ax.set_xticks(x_ticks)
ax.set_xticklabels(x_ticklabels)
ax.tick_params(axis='both', labelsize=11)
ax.set_ylabel("Number of trips (per 15-min bin)", size = 12)
ax.set_title("Arrivals: Observed vs Piecewise Poisson Model", fontsize=14, pad=12, weight = 'bold')
ax.legend(fontsize=11)
ax.grid(axis='y', alpha=0.3)
ax.spines['top'].set_visible(False)
ax.spines['right'].set_visible(False)

fig.tight_layout()
out1 = os.path.join(script_dir, '4.1 - poisson arrivals.png')
fig.savefig(out1, dpi=150, bbox_inches='tight')
plt.close(fig)
print(f"Saved: {out1}")


# PLOT: Arrivals vs Departures
fig, ax = plt.subplots(figsize=(12, 6))

ax.hist(all_arr['arrival_min'],   bins=bins, color="#7BB350", alpha=0.7,
        label=f'Arrivals at work (n={len(all_arr)})')
ax.hist(all_dep['departure_min'], bins=bins, color='#2C4688', alpha=0.7,
        label=f'Departures from work (n={len(all_dep)})')

mean_arr = all_arr['arrival_min'].mean()
mean_dep = all_dep['departure_min'].mean()
ax.axvline(mean_arr, color="#81B35C", linewidth=2, linestyle='--',
           label=f'Mean arrival {min_to_label(mean_arr)}')
ax.axvline(mean_dep, color="#264084", linewidth=2, linestyle='--',
           label=f'Mean departure {min_to_label(mean_dep)}')

ax.set_xlim(300, 1200)
x_ticks2 = np.arange(300, 1201, 60)
ax.set_xticks(x_ticks2)
ax.set_xticklabels([min_to_label(m) for m in x_ticks2], fontsize=11)
ax.set_ylabel("Number of trips (per 15-min bin)", size=12)
ax.set_title("Arrivals vs Departures", fontsize=14, pad=12, weight='bold')
ax.legend(fontsize=9)
ax.grid(axis='y', alpha=0.3)
ax.spines['top'].set_visible(False)
ax.spines['right'].set_visible(False)

fig.tight_layout()
out2 = os.path.join(script_dir, '4.1 - worktime.png')
fig.savefig(out2, dpi=150, bbox_inches='tight')
plt.close(fig)
print(f"Saved: {out2}")


# PLOT: Work duration distribution 
import sys
sys.path.append(os.path.join(script_dir, '..', 'src'))
from arrivals import load_and_fit
from arrivals import load_and_fit
from scipy.stats import norm

fit  = load_and_fit()
mean = fit['work_duration']['mean_min']
std  = fit['work_duration']['std_min']

def sample_duration(mean, std):
    while True:
        val = random.normalvariate(mean, std)
        if 60.0 <= val <= 930.0:
            return val

samples = [sample_duration(mean, std) for _ in range(10000)]

fig, ax = plt.subplots(figsize=(9, 4.5))
ax.hist(samples, bins=60, density=True, color="#4B8BA7", alpha=0.75,
        label='Simulated work durations (n=10,000)')

x = np.linspace(max(60, mean - 3*std), mean + 3*std, 300)
ax.plot(x, norm.pdf(x, mean, std), color="#0C2942", linewidth=2,
        label=f'Normal fit (μ={mean:.0f} min, σ={std:.0f} min)')
ax.axvline(mean, color='#0C2942', linewidth=1.5, linestyle='--',
           label=f'Mean = {mean:.0f} min ({mean/60:.1f} h)')

ax.set_xlim(0, 960)
ax.set_xlabel('Work duration (minutes)', size=12)
ax.set_ylabel('Density', size=12)
ax.set_title('Simulated work day durations', fontsize=14, weight = 'bold')
ax.legend(fontsize=9)
ax.grid(axis='y', alpha=0.3)
ax.spines['top'].set_visible(False)
ax.spines['right'].set_visible(False)

fig.tight_layout()
out3 = os.path.join(script_dir, '4.1 - duration.png')
fig.savefig(out3, dpi=150, bbox_inches='tight')
plt.close(fig)
print(f"Saved: {out3}")