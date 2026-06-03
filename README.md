# EV Charging Simulation
Discrete-event simulation of daytime solar-powered EV charging stations at the High Tech Campus Eindhoven. Models a baseline scenario (grid-only chargers) against a start-up scenario (solar-assisted chargers + grid overflow), and compares them across a set of performance metrics.

## Project Structure
EV-Charging-Simulation/
├── data/                          # datasets and output plots
│   ├── odin_2022.csv              # ODIN 2022 mobility survey (see below)
│   ├── ODiN2022_Codeboek_v1.0.ods # ODIN codebook
│   ├── 202410DatasetEVOfficeParking_v0.csv  # EV office parking dataset (see below)
│   ├── energy_distribution.py     # fits and compares distributions to the charging data
│   └── plot_arrivals.py           # visualises arrival/departure distributions
└── src/                           # simulation source code
├── main.py                    # entry point — run this
├── simulation.py              # discrete-event simulation engine
├── station.py                 # charging station model
├── customer.py                # EV/PHEV customer model
├── event.py                   # event types and priority queue
├── arrivals.py                # fits arrival rates from ODIN data
└── extract_energy_distr.py    # fits energy distribution from parking dataset

## Datasets
Two datasets are required and are not included in this repository.

**ODIN 2022 (Dutch National Travel Survey)**
Used to fit arrival times and work durations.
- Place as: `data/odin_2022.csv`
- Available at: [TODO: add download link]

**EV Office Parking Dataset**
Used to fit the distribution of energy needed per charging session.
- Place as: `data/202410DatasetEVOfficeParking_v0.csv`
- Available at: [TODO: add download link]

## How to Run

**Main simulation** (baseline vs start-up comparison):
```bash
cd src
python main.py
```
Output: a comparison table in the terminal and three plots saved to `data/`.

**Arrival distribution plot:**
```bash
cd data
python plot_arrivals.py
```

**Energy distribution analysis:**
```bash
cd data
python energy_distribution.py
```

## Configuration
All simulation parameters are in the `CONFIG` dict at the top of `src/main.py`:

| Parameter | Default | Description |
|---|---|---|
| `num_grid_spots` | 5 | Existing grid-only chargers (placeholder) |
| `num_solar_spots` | 2 | Solar chargers added by the start-up |
| `num_solar_panels` | 14 | Panels feeding the solar spots |
| `panel_peak_kw` | 0.4 | Peak output per panel (kW) |
| `charger_power_rate` | 11.0 | Power per active charger (kW) |
| `phev_max_charge_kw` | 3.7 | PHEV onboard charger cap (kW) |
| `phev_fraction` | 0.5 | Share of arrivals that are PHEV |
| `arrival_scale` | 0.1 | Scales ODIN survey counts to this lot's size |
| `num_replications` | 100 | Number of simulation replications |
