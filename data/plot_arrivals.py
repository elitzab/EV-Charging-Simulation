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
ev_arr = all_arr[all_arr['BrandstofEPa1'].isin([1, 2])].copy()
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
    (SIM_START,        SIM_START + 45,  "early\n06:30–07:15",  "#4C9BE8"),
    (SIM_START + 45,   SIM_START + 165, "peak\n07:15–9:15",   "#E8854C"),
    (SIM_START + 165,  SIM_START + 720, "tail\n9:15–18:30",   "#6DBE6D"),
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

# plot
BIN_WIDTH = 15   # minutes per histogram bin
bins = np.arange(300, 1140 + BIN_WIDTH, BIN_WIDTH)   # 05:00 – 19:00

def min_to_label(m):
    return f"{int(m//60):02d}:{int(m%60):02d}"

x_ticks     = np.arange(300, 1141, 60)
x_ticklabels = [min_to_label(m) for m in x_ticks]

fig, axes = plt.subplots(2, 1, figsize=(12, 13))
fig.suptitle("Workplace Arrival and Departure Analysis (Noord-Brabant)",
             fontsize=14, fontweight='bold', y=0.98)

# Arrivals + piecewise model
ax = axes[0]
counts_obs, _, patches = ax.hist(
    all_arr['arrival_min'], bins=bins,
    color='#5B8DB8', alpha=0.75, label=f'Observed arrivals (n={len(all_arr)})'
)
sim_counts, _ = np.histogram(sim_times, bins=bins)
ax.stairs(sim_counts / N_SIM_DAYS, bins, color="#ffb700",
          linewidth=2, label='Simulated arrivals (1-day avg)')

total_observed = len(all_arr)
total_sim_per_day = sum(r['rate'] * (r['end'] - r['start']) for r in arrival_rates)

for r in arrival_rates:
    xs = np.arange(r['start'], r['end'] + BIN_WIDTH, BIN_WIDTH)
    expected_per_bin = r['rate'] * BIN_WIDTH * (total_observed / total_sim_per_day)
    ax.hlines(expected_per_bin, r['start'], r['end'],
              colors=r['color'], linewidths=2.5, linestyles='--')
    ax.axvspan(r['start'], r['end'], alpha=0.08, color=r['color'])
    mid = (r['start'] + r['end']) / 2
    ax.text(mid, ax.get_ylim()[1] if ax.get_ylim()[1] > 0 else 10,
            r['label'].split('\n')[0], ha='center', va='bottom',
            fontsize=8, color=r['color'], fontweight='bold')

for w_start, w_end, _, color in windows:
    ax.axvline(w_start, color=color, linewidth=1, linestyle=':')
ax.axvline(windows[-1][1], color=windows[-1][3], linewidth=1, linestyle=':')

ax.set_xlim(300, 1140)
ax.set_xticks(x_ticks); ax.set_xticklabels(x_ticklabels, fontsize=8)
ax.set_ylabel("# trips per 15-min bin")
ax.set_title("Arrivals: Observed vs Piecewise Poisson Model ", fontsize=11)
ax.legend(fontsize=9)

# rate annotations
for r in arrival_rates:
    mid = (r['start'] + r['end']) / 2
    ax.text(mid, 2, f"λ={r['rate']:.2f}/min\n(1 per {1/r['rate']:.1f} min)",
            ha='center', va='bottom', fontsize=7.5, color=r['color'],
            bbox=dict(boxstyle='round,pad=0.2', fc='white', alpha=0.7))


# Arrivals vs Departures comparison
ax = axes[1]
ax.hist(all_arr['arrival_min'],  bins=bins, color='#2E86AB', alpha=0.7,
        label=f'Arrivals at work (n={len(all_arr)})')
ax.hist(all_dep['departure_min'], bins=bins, color='#E84C4C', alpha=0.7,
        label=f'Departures from work (n={len(all_dep)})')

mean_arr = all_arr['arrival_min'].mean()
mean_dep = all_dep['departure_min'].mean()
ax.axvline(mean_arr, color='#2E86AB', linewidth=2, linestyle='--',
           label=f'Mean arrival {min_to_label(mean_arr)}')
ax.axvline(mean_dep, color='#E84C4C', linewidth=2, linestyle='--',
           label=f'Mean departure {min_to_label(mean_dep)}')

ax.set_xlim(300, 1200)
x_ticks2 = np.arange(300, 1201, 60)
ax.set_xticks(x_ticks2)
ax.set_xticklabels([min_to_label(m) for m in x_ticks2], fontsize=8)
ax.set_ylabel("# trips per 15-min bin")
ax.set_title("Arrivals vs Departures", fontsize=11)
ax.legend(fontsize=9)

# final formatting
for ax in axes:
    ax.grid(axis='y', alpha=0.3)
    ax.spines['top'].set_visible(False)
    ax.spines['right'].set_visible(False)

plt.tight_layout(rect=[0, 0, 1, 0.97])
out_path = os.path.join(script_dir, 'arrivals_plot.png')
plt.savefig(out_path, dpi=150, bbox_inches='tight')
print(f"\nPlot saved to: {out_path}")
plt.close()