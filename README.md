# F1 Hybrid Energy Management Simulator

Physics-based simulation of Formula 1 MGU-K hybrid energy management at Monza (Circuit di Monza).

## Run

Open and execute the analysis notebook:
- `analysis/F1_analysis.ipynb`

Or run experiments directly:
- `python -m experiments.monza_run` — single lap, conservative strategy, saves telemetry
- `python -m experiments.run_experiment` — all strategies × SOC values, saves comparison CSV

## Current implementation status
- Segmented Monza track model (12 segments: straights, braking zones, corners)
- Physics-based discrete-time lap simulation
- Three ERS deployment strategies: Conservative, Aggressive, Lookahead
- FIA deployment constraints (120 kW MGU-K limit) enforced
- Battery SOC tracking with regen efficiency model
- Telemetry output: time, distance, speed, power, SOC
- Strategy comparison experiment runner