# F1 Hybrid Energy Management Simulator

Notebook-first research prototype for Formula 1 MGU-K energy management at Circuit Gilles Villeneuve.

## Run
Open and execute:
- `f1_hybrid_energy_management_simulator.ipynb`

## Current implementation status
- Strategy-aware segmented track model (deployment/regen/overtake priorities).
- Track consistency validation.
- Physics-based discrete-time lap simulation (baseline ERS OFF vs ERS ON).
- FIA deployment constraints (120 kW, 4 MJ/lap) enforced in controller/simulation.
- SOC, deployment/regen power, and speed visualizations.
