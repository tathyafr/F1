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

            n = min(len(result["time_history"]), len(result["power_history"]),
                len(result["soc_history"]), len(result["pos_history"]),
                len(result["speed_history"]))

            tel_df = pd.DataFrame({
                "time":     result["time_history"][:n],
                "power":    result["power_history"][:n],
                "soc":      result["soc_history"][:n],
                "distance": result["pos_history"][:n],
                "speed":    result["speed_history"][:n],
                "segment_name": result["seg_name_history"][:n],
                "segment_type": result["seg_type_history"][:n],
            })
            tel_df["cumulative_energy_deployed_j"] = tel_df["power"].cumsum() * 0.2
            fname = f"results/telemetry_{strategy}_soc{int(soc*10)}.csv"
            tel_df.to_csv(fname, index=False)

            print(f"{strategy:15s}  SOC={soc:.1f}  lap={result['lap_time_s']:.2f}s  "
                f"deployed={deployed/1e6:.2f}MJ  soc_end={result['soc_end']:.3f}")

    df = pd.DataFrame(results)
    df.to_csv("results/strategy_results.csv", index=False)
    print("\nSaved to results/strategy_results.csv")

    # Multi-lap test (conservative, SOC=0.6)
    print("\n--- Multi-lap test (conservative, SOC=0.6) ---")
    battery_ml = Battery(BATTERY_CAPACITY_J, soc=0.6)
    sim_ml = SimulationRunner(track, vehicle, battery_ml, ConservativeController())
    lap_results = sim_ml.run_laps(n_laps=3)
    for r in lap_results:
        print(f"Lap {r['lap_number']}: {r['lap_time_s']:.2f}s  soc_end={r['soc_end']:.3f}")


if __name__ == "__main__":
    run()