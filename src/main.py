import random
import numpy as np

from station import Station
from simulation import Simulation

SIM_SEED = 42

class GammaDist:
    def __init__(self, alpha, beta):
        self.alpha = alpha
        self.beta = beta
    def sample(self):
        return random.gammavariate(self.alpha, self.beta)

class LognormalDist:
    def __init__(self, mu, sigma):
        self.mu = mu
        self.sigma = sigma
    def sample(self):
        return random.lognormvariate(self.mu, self.sigma) / 60.0

class ExponentialDist:
    def __init__(self, rates):
        self.rates = rates
    def sample(self, clock):
        if clock < 45:
            rate_info = self.rates[0]
        elif clock < 195:
            rate_info = self.rates[1]
        else:
            rate_info = self.rates[2]
        
        rate = rate_info['rate']
        return random.expovariate(rate)
    
def run_experiment(name, num_repl):
    """
    Run multiple replications of a scenario and calculate CIs.
    """
    # TODO


if __name__ == "__main__":
    run_experiment("Baseline", num_repl=100)
    run_experiment("Start-up", num_repl=100)