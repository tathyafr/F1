# experiments/run_experiment.py
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
from sim.config import VEHICLE_MASS_KG, BATTERY_CAPACITY_J

os.makedirs("results", exist_ok=True)


def run():

    initial_socs = [0.4, 0.6, 0.8]
    results = []

    for track_name in TRACK_REGISTRY:
        track = build_track(track_name)
        vehicle = Vehicle(VEHICLE_MASS_KG)

        # Build OptimalController once per track/SOC combo (optimization is per-track)
        def make_controllers(soc):
            bat_opt = Battery(BATTERY_CAPACITY_J, soc=soc)
            opt = OptimalController(vehicle, track, bat_opt)
            return {
                "baseline":     BaselineController(),
                "conservative": ConservativeController(),
                "aggressive":   AggressiveController(energy_budget_j=4e6),
                "lookahead":    LookaheadController(vehicle),
                "optimal":      opt,
            }

        print(f"\n=== {track_name.upper()} ===")

        for soc in initial_socs:
            controllers = make_controllers(soc)

            for strategy, controller in controllers.items():
                battery = Battery(BATTERY_CAPACITY_J, soc=soc)
                sim = SimulationRunner(track, vehicle, battery, controller)
                result = sim.run_lap()

                deployed  = result["deployed_j"]
                harvested = result["harvested_j"]
                wasted    = result["wasted_j"]
                total_avail = deployed + wasted
                efficiency = deployed / total_avail if total_avail > 0 else 0.0

                results.append({
                    "track":                track_name,
                    "strategy":             strategy,
                    "initial_soc":          soc,
                    "lap_time_s":           result["lap_time_s"],
                    "lap_time_improvement_s": result["lap_time_improvement_s"],
                    "soc_end":              result["soc_end"],
                    "energy_deployed_j":    deployed,
                    "energy_harvested_j":   harvested,
                    "energy_wasted_j":      wasted,
                    "net_energy_change_j":  deployed - harvested,
                    "deployment_efficiency": efficiency,
                })

                # Save per-strategy telemetry (Monza only to keep file count manageable)
                if track_name == "monza":
                    n = min(len(result["time_history"]), len(result["power_history"]),
                            len(result["soc_history"]), len(result["pos_history"]),
                            len(result["speed_history"]))
                    tel_df = pd.DataFrame({
                        "time":         result["time_history"][:n],
                        "power":        result["power_history"][:n],
                        "soc":          result["soc_history"][:n],
                        "distance":     result["pos_history"][:n],
                        "speed":        result["speed_history"][:n],
                        "segment_name": result["seg_name_history"][:n],
                        "segment_type": result["seg_type_history"][:n],
                    })
                    tel_df["cumulative_energy_deployed_j"] = tel_df["power"].cumsum() * 0.2
                    fname = f"results/telemetry_{strategy}_soc{int(soc*10)}.csv"
                    tel_df.to_csv(fname, index=False)

                print(f"  {strategy:12s}  SOC={soc:.1f}  lap={result['lap_time_s']:.3f}s  "
                      f"+{result['lap_time_improvement_s']:.4f}s  "
                      f"deployed={deployed/1e6:.2f}MJ  soc_end={result['soc_end']:.3f}")

    df = pd.DataFrame(results)
    df.to_csv("results/strategy_results.csv", index=False)
    print(f"\nSaved {len(df)} rows → results/strategy_results.csv")

    # Multi-lap stint analysis (all 4 strategies, Monza, SOC=0.8, 5 laps)
    print("\n--- Multi-lap stint (Monza, SOC=0.8, 5 laps) ---")
    monza = build_track("monza")
    vehicle = Vehicle(VEHICLE_MASS_KG)
    stint_rows = []
    for strat_name, ctrl in [
        ("baseline",     BaselineController()),
        ("conservative", ConservativeController()),
        ("aggressive",   AggressiveController(energy_budget_j=4e6)),
        ("lookahead",    LookaheadController(vehicle)),
    ]:
        battery = Battery(BATTERY_CAPACITY_J, soc=0.8)
        sim = SimulationRunner(monza, vehicle, battery, ctrl)
        laps = sim.run_laps(n_laps=5)
        for r in laps:
            stint_rows.append({
                "strategy": strat_name,
                "lap": r["lap_number"],
                "lap_time_s": r["lap_time_s"],
                "improvement_s": r["lap_time_improvement_s"],
                "soc_end": r["soc_end"],
                "deployed_j": r["deployed_j"],
            })
            print(f"  {strat_name:12s}  lap {r['lap_number']}:  {r['lap_time_s']:.3f}s  "
                  f"soc_end={r['soc_end']:.3f}")

    pd.DataFrame(stint_rows).to_csv("results/stint_results.csv", index=False)
    print("Saved → results/stint_results.csv")


if __name__ == "__main__":
    run()
