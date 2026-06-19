"""
Run this. See README.md for information on how to correctly set up the files
so that the simulation runs.
Outputs:
    - A comparison between the baseline and startup scenario
    - Additional plots that can be found in the data/ folder 
"""
import random
import math

from station import Station
from simulation import Simulation
from arrivals import load_and_fit
from extract_energy_distr import EnergyDistribution
from solar_profile import SolarProfile
import results

# TOGGLES:
CONFIG = {
    'num_grid_spots':           4,          # existing grid-only chargers
    'num_solar_spots':          4,          # solar-assisted chargers added by the start-up
    'num_solar_panels':         210,        # panels feeding the solar spots
    'season':                   'summer',   # time of the year
    'panel_peak_kw':            0.4,        # peak output per panel
    'charger_power_rate':       11,         # kW per active charger
    'phev_max_charge_kw':       5.7,        # PHEV onboard-charger cap
    'phev_fraction':            0.38,       # share of arrivals that are PHEV
    'arrival_scale':            0.115,      # scales Noord-Brabant counts to this lot
    'battery_capacity_kwh':     1000.0,     # kWh of battery storage

    # configuration of test:
    # "Baseline"    = uses grid-only spots
    # "Start-up"    = uses grid-only + solar spots
    # "Solar-only"  = uses solar spots only
    'COMPARISON':               ("Baseline", "Solar-only"),

    'sim_start_min':            390,        # simulation start = 06:30
    'arrival_cutoff_min':       1110,       # arrival cutoff = 18:30
    'monitor_interval_min':     10,         # snapshots step
    'monitor_end_min':          1320,       # end of the monitoring window = 22:00

    'num_replications':         100,
    'random_seed':              42,
}

class WorkDurationDist:
    def __init__(self, mean, std, min_minutes=60.0):
        self.mean = mean
        self.std = std
        self.min_minutes = min_minutes
    def sample(self):
        while True:
            val = random.normalvariate(self.mean, self.std)
            if 60.0 <= val <= 720.0:
                return val

class ExponentialDist:
    def __init__(self, rates, scale=1.0):
        self.rates = rates
        self.scale = scale
    def sample(self, clock):
        rate_info = self.rates[-1]
        for r in self.rates:
            if clock < r['end_min']:
                rate_info = r
                break
        return random.expovariate(rate_info['rate'] * self.scale)


def build_stations(scenario, config):
    """
    Baseline:   X grid-only spots
    Start-up:   Y solar spots (filled first) + X grid spots as overflow
    Solar-only: Y solar spots only
    """
    op_start, op_end = config['sim_start_min'], config['monitor_end_min']
    stations = []

    if scenario in ("Start-up", "Solar-only"):
        solar_profile = SolarProfile(season=config["season"], num_panels=config["num_solar_panels"])
        stations.append(Station(
            "Solar_Station", station_type="solar",
            capacity=config['num_solar_spots'], panels=config['num_solar_panels'],
            panel_peak_kw=config['panel_peak_kw'], charger_power_rate=config['charger_power_rate'],
            op_start=op_start, op_end=op_end, solar_profile=solar_profile,
            battery_capacity_kwh=config['battery_capacity_kwh']
        ))

    if scenario in ("Start-up", "Baseline"):
        stations.append(Station(
            "Grid_Station", station_type="grid",
            capacity=config['num_grid_spots'], panels=0,
            charger_power_rate=config['charger_power_rate'],
            op_start=op_start, op_end=op_end
        ))

    return stations


def confidence_interval(values):
    """
    # Return: (mean, half-width) for a 95% CI
    """
    n = len(values)
    mean = sum(values) / n
    if n < 2:
        return mean, 0.0
    var = sum((v - mean) ** 2 for v in values) / (n - 1)
    half = 1.96 * math.sqrt(var) / math.sqrt(n)
    return mean, half


def run_experiment(scenario, config, num_repl):
    """
    Runs multiple replications of a scenario and calculate CIs
    """
    arrival_fit = load_and_fit()
    energy_dist = EnergyDistribution()

    per_repl = []
    sample_history = None
    sample_stations = None
    for i in range(num_repl):
        random.seed(config['random_seed'] + i)

        stations = build_stations(scenario, config)
        arrival_dist = ExponentialDist(arrival_fit['arrival_rates'], config['arrival_scale'])
        work_dist = WorkDurationDist(arrival_fit['work_duration']['mean_min'],
                                     arrival_fit['work_duration']['std_min'])

        sim = Simulation(stations, arrival_dist, energy_dist, work_dist, config)
        sim.run()
        per_repl.append(sim.compute_metrics())
        if i == 0:
            sample_history = sim.history
            sample_stations = sim.stations

    aggregated = {}
    for key in per_repl[0]:
        aggregated[key] = confidence_interval([r[key] for r in per_repl])
    return aggregated, sample_history, sample_stations


if __name__ == "__main__":
    n = CONFIG['num_replications']
    scenario_a, scenario_b = CONFIG['COMPARISON']
    result_a, hist_a, stns_a = run_experiment(scenario_a, CONFIG, num_repl=n)
    result_b, hist_b, stns_b = run_experiment(scenario_b, CONFIG, num_repl=n)

    results.print_comparison(result_a, result_b, CONFIG)
    results.plot_all(hist_b, stns_b, hist_a, result_a, result_b, scenario_b)