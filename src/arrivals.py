import os
import pandas as pd
import numpy as np
from scipy import stats

"""
Reads the ODIN 2022 mobility survey and fits distributions for:
   - inter-arrival times (three time windows)
   - work duration (lognormal)
"""

script_dir = os.path.dirname(os.path.abspath(__file__))
csv_path = os.path.join(script_dir, '..', 'data', 'odin_2022.csv')


def load_and_fit(verbose=False):
    """
    Return: a dict with fitted distribution parameters:
        arrival_rates - list of dicts {window, start_min, end_min, rate (arrivals/min)}
        work_duration - dict {mean_min, std_min} (normal fit on departure - arrival)
    """
    df = pd.read_csv(csv_path, sep=';', low_memory=False, encoding='latin1')

    relevant_cols = ['Doel', 'MotiefV', 'Hvm', 'AankProv', 'VertProv',
                     'AankUur', 'AankMin', 'VertUur', 'VertMin']
    for col in relevant_cols:
        df[col] = pd.to_numeric(df[col], errors='coerce')

    # Arrivals
    #   Doel:       2 = Work (Destination)
    #   Hvm:        1 = Car (Method of transportation)
    #   AankProv:   11 = Noord-Brabant (Arrival Province)
    arrivals = df[(df['Doel'] == 2) & (df['Hvm'] == 1) & (df['AankProv'] == 11)].copy()
    arrivals = arrivals.dropna(subset=['AankUur', 'AankMin'])
    arrivals['arrival_min'] = arrivals['AankUur'] * 60 + arrivals['AankMin']

    # Departures
    #   Doel:       1 = Home (Destination)
    #   MotiefV:    1 = Commute (Purpose)
    #   Hvm:        1 = Car (Method of transportation)
    #   VertProv:   11 = Noord-Brabant (Departure Province)
    departures = df[(df['Doel'] == 1) & (df['MotiefV'] == 1) &
                    (df['Hvm'] == 1) & (df['VertProv'] == 11)].copy()
    departures = departures.dropna(subset=['VertUur', 'VertMin'])
    departures['departure_min'] = departures['VertUur'] * 60 + departures['VertMin']

    mean_arr = arrivals['arrival_min'].mean()
    std_arr  = arrivals['arrival_min'].std()
    mean_dep = departures['departure_min'].mean()
    std_dep  = departures['departure_min'].std()
    avg_workday = mean_dep - mean_arr

    # Piecewise Poisson rates (arrivals per minute) 
    #   06:30–07:15  (clock  0 – 75)   early 
    #   07:15–09:15  (clock 75 – 195)  peak 
    #   09:15–18:30  (clock 195 – 720) late
    SIM_START = 6 * 60 + 30   # 06:30
    windows = [
        (SIM_START,          SIM_START + 75,   "early"),
        (SIM_START + 75,     SIM_START + 195,  "peak"),
        (SIM_START + 195,    SIM_START + 720,  "tail"),
    ]

    arrival_rates = []
    for (w_start, w_end, label) in windows:
        count = ((arrivals['arrival_min'] >= w_start) & (arrivals['arrival_min'] <  w_end)).sum()
        duration_min = w_end - w_start
        rate = count / duration_min if duration_min > 0 else 0.001

        arrival_rates.append({
            'window':    label,
            'start_min': w_start,
            'end_min':   w_end,
            'rate':      rate,        # arrivals per minute
        })

    if verbose:
        print("=" * 50)
        print(f"Total Arrival Trips (to Work):      {len(arrivals)}")
        print(f"Mean Arrival Time:                  {mean_arr:.1f} min ({int(mean_arr/60)}:{int(mean_arr%60):02d})")
        print(f"Arrival std dev:                    {std_arr:.1f} min")

        print("-" * 50)
        print(f"Total Departure Trips (from Work):  {len(departures)}")
        print(f"Mean Departure Time:                {mean_dep:.1f} min ({int(mean_dep/60)}:{int(mean_dep%60):02d})")
        print(f"Departure std dev:                  {std_dep:.1f} min")

        print("-" * 50)
        print("Piecewise arrival rates (arrivals/min):")
        for r in arrival_rates:
            print(f"  {r['window']:6s}  {int(r['start_min']/60):02d}:{int(r['start_min']%60):02d}"
                  f" – {int(r['end_min']/60):02d}:{int(r['end_min']%60):02d}"
                  f"   rate = {r['rate']:.5f}")
        print("=" * 50)

    return {
        'arrival_rates': arrival_rates,
        'work_duration': {
            'mean_min': avg_workday,
            'std_min':  (std_arr**2 + std_dep**2)**0.5,
        },
    }

if __name__ == "__main__":
    load_and_fit(verbose=True)