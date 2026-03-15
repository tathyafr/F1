# experiments/run_experiment.py
import pandas as pd

from experiments.tracks import build_monza
from sim.vehicle import Vehicle
from sim.battery import Battery
from sim.controller import (
    ConservativeController,
    AggressiveController,
    LookaheadController,
)
from sim.sim_runner import SimulationRunner
from sim.config import VEHICLE_MASS_KG, BATTERY_CAPACITY_J


def run():

    track = build_monza()
    vehicle = Vehicle(VEHICLE_MASS_KG)

    controllers = {
        "conservative": ConservativeController(),
        "aggressive":   AggressiveController(energy_budget_j=4e6),
        "lookahead":    LookaheadController(vehicle),
    }

    initial_socs = [0.4, 0.6, 0.8]

    results = []

    for strategy, controller in controllers.items():
        for soc in initial_socs:

            battery = Battery(BATTERY_CAPACITY_J, soc=soc)
            sim = SimulationRunner(track, vehicle, battery, controller)
            result = sim.run_lap()

            deployed = result["deployed_j"]
            harvested = result["harvested_j"]
            wasted = result["wasted_j"]

            # deployment efficiency: how much harvested energy was actually used
            total_available = deployed + wasted
            efficiency = deployed / total_available if total_available > 0 else 0.0

            results.append({
                "strategy":             strategy,
                "initial_soc":          soc,
                "lap_time":             result["lap_time_s"],
                "soc_end":              result["soc_end"],
                "energy_deployed_j":    deployed,
                "energy_harvested_j":   harvested,
                "energy_wasted_j":      wasted,
                "net_energy_change_j":  deployed - harvested,
                "deployment_efficiency": efficiency,
            })

            print(f"{strategy:15s}  SOC={soc:.1f}  lap={result['lap_time_s']:.2f}s  "
                  f"deployed={deployed/1e6:.2f}MJ  soc_end={result['soc_end']:.3f}")

    df = pd.DataFrame(results)
    df.to_csv("results/strategy_results.csv", index=False)
    print("\nSaved to results/strategy_results.csv")


if __name__ == "__main__":
    run()