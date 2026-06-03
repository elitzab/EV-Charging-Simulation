import os
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

"""
This file was written with the help of Claude
"""

script_dir = os.path.dirname(os.path.abspath(__file__))
out_dir = os.path.join(script_dir, '..', 'data')

# rows (for a table)
ROWS = [
    ('arrived',            'Cars arrived',            ''),
    ('served',             'Cars charged',            ''),
    ('abandoned',          'Left without charging',   ''),
    ('prop_fully_charged', 'Fully charged',           '(frac)'),
    ('avg_wait_min',       'Avg wait',                'min'),
    ('total_delivered_kwh','Energy delivered',        'kWh'),
    ('total_solar_kwh',    'Solar energy used',       'kWh'),
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


def plot_all(startup_history, startup_stations, baseline_history, baseline, startup):
    """
    Three figures: 
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
    ax.bar(hours, grid_kwh, bottom=solar_kwh, label='Grid', color='#3b6ea5')
    ax.set_xlabel('Hour of day')
    ax.set_ylabel('Energy delivered (kWh)')
    ax.set_title('Start-up solar station: solar vs grid energy per hour')
    ax.legend()
    fig.tight_layout()
    fig.savefig(os.path.join(out_dir, 'plt_energy_by_hour.png'), dpi=120)
    plt.close(fig)

    # queue length over the day, both scenarios
    fig, ax = plt.subplots(figsize=(9, 4.5))
    for hist, label, color in [(baseline_history, 'Baseline', '#3b6ea5'),
                               (startup_history, 'Start-up', '#f4a300')]:
        t = [h['time'] / 60.0 for h in hist]
        q = [h['queue'] for h in hist]
        ax.plot(t, q, label=label, color=color)
    ax.set_xlabel('Hour of day')
    ax.set_ylabel('Cars waiting')
    ax.set_title('Queue length over the day')
    ax.legend()
    fig.tight_layout()
    fig.savefig(os.path.join(out_dir, 'plt_queue.png'), dpi=120)
    plt.close(fig)

    # Metrics comparison: side-by-side bars with 95% CI error bars
    headline = [
        ('avg_wait_min',       'Avg wait (min)'),
        ('total_grid_kwh',     'Grid drawn (kWh)'),
        ('total_solar_kwh',    'Solar used (kWh)'),
        ('solar_station_kwh',  'Evening relief (kWh)'),
        ('peak_grid_kw',       'Peak grid demand (kW)'),
    ]
 
    fig, ax = plt.subplots(figsize=(11, 5))
    n = len(headline)
    x = range(n)
    w = 0.35
 
    base_means = [baseline[k][0] for k, _ in headline]
    base_cis   = [baseline[k][1] for k, _ in headline]
    start_means = [startup[k][0] for k, _ in headline]
    start_cis   = [startup[k][1] for k, _ in headline]
 
    ax.bar([i - w/2 for i in x], base_means,  width=w, yerr=base_cis,
           label='Baseline', color='#3b6ea5', capsize=4)
    ax.bar([i + w/2 for i in x], start_means, width=w, yerr=start_cis,
           label='Start-up', color='#f4a300', capsize=4)
 
    ax.set_xticks(list(x))
    ax.set_xticklabels([label for _, label in headline], fontsize=9)
    ax.set_title('Metrics comparison (mean ± 95% CI)')
    ax.legend()
    ax.grid(axis='y', alpha=0.3)
    ax.spines['top'].set_visible(False)
    ax.spines['right'].set_visible(False)
    fig.tight_layout()
    fig.savefig(os.path.join(out_dir, 'plt_metrics_comparison.png'), dpi=120)
    plt.close(fig)

    print(f"Saved plots to {os.path.normpath(out_dir)}")