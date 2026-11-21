# experiments/corner_benefit_sensitivity.py
"""
Stress-tests the model's biggest assumption.

The main model assumes energy deployed in a corner gives ZERO lap-time benefit
(corners are grip-limited, not power-limited). That assumption makes the
headline result partly true by construction, so here it is relaxed: energy
used in a corner is worth some fraction f of what it would be worth on a
straight. If the strategy ranking still holds as f grows, the conclusion
"timing matters more than total energy" is not just an artefact of f = 0.

Sweep: f = 0.0, 0.1, 0.25, 0.5, 0.75, 1.0 across all three tracks, SOC = 0.6.

Output: results/corner_benefit_sensitivity.csv
Run:    python -m experiments.corner_benefit_sensitivity
"""

import os
import pandas as pd

from experiments.tracks import TRACK_REGISTRY, build_track
from sim.vehicle import Vehicle
from sim.battery import Battery
from sim.controller import (
    BaselineController,
    ConservativeController,
    AggressiveController,
    LookaheadController,
    OptimalController,
)
from sim.sim_runner import SimulationRunner
from sim.config import VEHICLE_MASS_KG, BATTERY_CAPACITY_J, ENERGY_PER_LAP_J

FRACTIONS = [0.0, 0.1, 0.25, 0.5, 0.75, 1.0]
INITIAL_SOC = 0.6


def run():
    os.makedirs("results", exist_ok=True)
    rows = []
    for track_name in TRACK_REGISTRY:
        track = build_track(track_name)
        vehicle = Vehicle(VEHICLE_MASS_KG)
        for f in FRACTIONS:
            controllers = {
                "baseline": BaselineController(),
                "conservative": ConservativeController(),
                "aggressive": AggressiveController(energy_budget_j=ENERGY_PER_LAP_J),
                "lookahead": LookaheadController(vehicle),
                # The optimizer is told the same corner value the simulator uses,
                # so it re-plans for each f rather than keeping its f = 0 plan.
                "optimal": OptimalController(
                    vehicle, track, Battery(BATTERY_CAPACITY_J, soc=INITIAL_SOC),
                    corner_benefit_fraction=f,
                ),
            }
            for name, ctrl in controllers.items():
                battery = Battery(BATTERY_CAPACITY_J, soc=INITIAL_SOC)
                sim = SimulationRunner(track, vehicle, battery, ctrl,
                                       corner_benefit_fraction=f)
                r = sim.run_lap()
                rows.append({
                    "track": track_name,
                    "corner_benefit_fraction": f,
                    "strategy": name,
                    "improvement_s": round(r["lap_time_improvement_s"], 4),
                    "deployed_mj": round(r["deployed_j"] / 1e6, 3),
                })
            print(f"{track_name:7s} f={f:<4} done")

    df = pd.DataFrame(rows)
    df.to_csv("results/corner_benefit_sensitivity.csv", index=False)
    print("\nWrote results/corner_benefit_sensitivity.csv")
    print(df.pivot_table(index=["track", "corner_benefit_fraction"],
                         columns="strategy", values="improvement_s").round(3))


if __name__ == "__main__":
    run()
