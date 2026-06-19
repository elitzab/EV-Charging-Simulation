import os
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

"""
This file was written with the help of Claude
"""

script_dir = os.path.dirname(os.path.abspath(__file__))
out_dir = os.path.join(script_dir, '..', 'data')

ROWS = [
    ('arrived',            'Cars arrived',            ''),
    ('served',             'Cars charged',            ''),
    ('abandoned',          'Left without charging',   ''),
    ('prop_fully_charged', 'Fully charged',           '(frac)'),
    ('avg_wait_min',       'Avg wait',                'min'),
    ('total_delivered_kwh','Energy delivered',        'kWh'),
    ('total_solar_kwh',    'Solar energy used',       'kWh'),
    ('total_battery_kwh',  'Battery energy used',     'kWh'),
    ('total_grid_kwh',     'Grid energy drawn',       'kWh'),
    ('solar_station_kwh',  'Evening peak relief',     'kWh'),
    ('peak_grid_kw',       'Peak grid demand',        'kW'),
    ('util_solar',         'Solar utilisation',       '(frac)'),
    ('util_grid',          'Grid utilisation',        '(frac)'),
]


def print_comparison(baseline, startup, config):
    print("\n" + "=" * 80)
    print(f"COMPARISON  (n = {config['num_replications']} replications)")
    print("=" * 80)
    print(f"{'Metric':28s}{'Baseline':>20s}{'Start-up':>20s}")
    print("-" * 80)
    for key, label, unit in ROWS:
        bm, bh = baseline[key] # = baseline mean / CI
        sm, sh = startup[key] # = startup mean / CI
        print(f"{label:28s}{bm:9.2f} +/-{bh:6.2f}   {sm:9.2f} +/-{sh:6.2f}  {unit}")
    print("=" * 80 + "\n")


def plot_all(startup_history, startup_stations, baseline_history, baseline, startup, label_b="Start-up"):
    """
        - hourly solar vs grid energy at the solar station
        - queue length over the day
        - headline KPI comparison
    """
    # hourly solar vs grid energy
    solar = [s for s in startup_stations if s.station_type == "solar"]
    hours = list(range(24))
    solar_kwh = [sum(st.hourly_solar_kwh[h] for st in solar) for h in hours]
    grid_kwh = [sum(st.hourly_grid_kwh[h] for st in solar) for h in hours]

    fig, ax = plt.subplots(figsize=(9, 4.5))
    ax.bar(hours, solar_kwh, label='Solar', color='#f4a300')
    ax.bar(hours, grid_kwh, bottom=solar_kwh, label='Grid', color="#1c4572")
    ax.set_xlabel('Hour of day', size=12)
    ax.set_ylabel('Energy delivered (kWh)', size=12)
    ax.set_title('Start-up Solar Station: Solar vs Grid Energy per Hour', fontsize=14, weight='bold')
    ax.set_xlim(5, 23)
    ax.legend()
    fig.tight_layout()
    fig.savefig(os.path.join(out_dir, '4.6 - energy per hour.png'), dpi=120)
    plt.close(fig)

    # queue length over the day, both scenarios
    fig, ax = plt.subplots(figsize=(9, 4.5))
    for hist, label, color in [(baseline_history, 'Baseline', "#1c4572"), 
                               (startup_history, 'Start-up', "#6bc196")]:
        t = [h['time'] / 60.0 for h in hist]
        q = [h['queue'] for h in hist]
        ax.plot(t, q, label=label, color=color)
    ax.set_xlabel('Hour of day', size=12)
    ax.set_ylabel('Cars waiting', size=12)
    ax.set_title('Queue Length Over the Day', fontsize=14, weight='bold')
    ax.legend()
    fig.tight_layout()
    fig.savefig(os.path.join(out_dir, '4.6 - queue.png'), dpi=120)
    plt.close(fig)

    # kpi comparison: side-by-side bars with 95% CI error bars
    relief_key = 'solar_station_kwh' if label_b != 'Solar-only' else 'total_delivered_kwh'

    headline = [
        ('avg_wait_min',      'Avg wait (min)'),
        ('total_grid_kwh',    'Grid drawn (kWh)'),
        ('total_solar_kwh',   'Solar used (kWh)'),
        ('total_battery_kwh', 'Battery used (kWh)'),
        (relief_key,          'Evening relief (kWh)'),
        ('peak_grid_kw',      'Peak grid demand (kW)'),
    ]
 
    fig, ax = plt.subplots(figsize=(11, 5))
    n = len(headline)
    x = range(n)
    w = 0.35
 
    base_means = [baseline[k][0] for k, _ in headline]
    start_means = [startup[k][0] for k, _ in headline]
 
    ax.bar([i - w/2 for i in x], base_means,  width=w,
           label='Baseline', color="#1c4572", capsize=4)
    ax.bar([i + w/2 for i in x], start_means, width=w,
           label='Start-up', color="#6bc196", capsize=4)
 
    ax.set_xticks(list(x))
    ax.set_xticklabels([label for _, label in headline], fontsize=10)
    ax.set_title('Optimal vs Realistic Grid-only Set-up KPI comparison (mean ± 95% CI)', fontsize=14, weight='bold')
    ax.legend()
    ax.grid(axis='y', alpha=0.3)
    ax.spines['top'].set_visible(False)
    ax.spines['right'].set_visible(False)
    fig.tight_layout()
    fig.savefig(os.path.join(out_dir, '4.6 - KPI.png'), dpi=120)
    plt.close(fig)

    print(f"Saved plots to {os.path.normpath(out_dir)}")