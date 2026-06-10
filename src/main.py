"""
Run this.
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
    'num_grid_spots':       5,      # existing grid-only chargers
    'num_solar_spots':      2,      # solar-assisted chargers added by the start-up
    'num_solar_panels':     60,     # panels feeding the solar spots
    'season':             'summer', # time of the year
    'panel_peak_kw':        0.4,    # peak output per panel
    'charger_power_rate':   13.47,  # kW per active charger
    'phev_max_charge_kw':   3.7,    # PHEV onboard-charger caP
    'phev_fraction':        0.5,    # share of arrivals that are PHEV
    'arrival_scale':        0.1,    # scales Noord-Brabant counts to this lot

    'sim_start_min':        390,    # simulation start = 06:30
    'arrival_cutoff_min':   1110,   # arrival cutoff = 18:30
    'monitor_interval_min': 10,     # snapshots step
    'monitor_end_min':      1320,   # end of the monitoring window = 22:00

    'num_replications':     100,
    'random_seed':          42,
}

class WorkDurationDist:
    def __init__(self, mean, std, min_minutes=60.0):
        self.mean = mean
        self.std = std
        self.min_minutes = min_minutes
    def sample(self):
        return max(self.min_minutes, random.normalvariate(self.mean, self.std))

class ExponentialDist:
    def __init__(self, rates, scale=1.0):
        self.rates = rates      # list of {window, start_min, end_min, rate}
        self.scale = scale      # scales survey counts down to this lot's size
    def sample(self, clock):
        rate_info = self.rates[-1]
        for r in self.rates:
            if clock < r['end_min']:
                rate_info = r
                break
        return random.expovariate(rate_info['rate'] * self.scale)


def build_stations(scenario, config):
    """
    Baseline:  X grid-only spots
    Start-up:  Y solar spots (filled first) + X grid spots as overflow
    """
    op_start, op_end = config['sim_start_min'], config['monitor_end_min']
    stations = []

    if scenario == "Start-up":
        solar_profile = SolarProfile(
            season=config["season"],
            num_panels=config["num_solar_panels"]
        )

        stations.append(Station(
            "Solar_Station", station_type="solar", capacity=config['num_solar_spots'], 
            panels=config['num_solar_panels'], panel_peak_kw=config['panel_peak_kw'], charger_power_rate=config['charger_power_rate'],
            op_start=op_start, op_end=op_end,solar_profile=solar_profile
        ))

    stations.append(Station(
        "Grid_Station",
        station_type="grid", capacity=config['num_grid_spots'], panels=0,
        charger_power_rate=config['charger_power_rate'], op_start=op_start, op_end=op_end
    ))

    return stations


def confidence_interval(values):
    """
    Return: (mean, half_width) for a 95% CI
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
            sample_history = sim.history        # one run's time series for plotting
            sample_stations = sim.stations      # one run's stations for hourly bins

    # aggregate every metric into mean +/- 95% CI half-width
    aggregated = {}
    for key in per_repl[0]:
        aggregated[key] = confidence_interval([r[key] for r in per_repl])
    return aggregated, sample_history, sample_stations


if __name__ == "__main__":
    n = CONFIG['num_replications']
    baseline, base_hist, base_stns = run_experiment("Baseline", CONFIG, num_repl=n)
    startup, start_hist, start_stns = run_experiment("Start-up", CONFIG, num_repl=n)

    results.print_comparison(baseline, startup, CONFIG)
    results.plot_all(start_hist, start_stns, base_hist, baseline, startup)