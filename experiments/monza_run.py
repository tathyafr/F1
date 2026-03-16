# experiments/monza_run.py
import pandas as pd

from experiments.tracks import build_monza
from sim.vehicle import Vehicle
from sim.battery import Battery
from sim.controller import ConservativeController
from sim.sim_runner import SimulationRunner
from sim.config import VEHICLE_MASS_KG, BATTERY_CAPACITY_J


def run():

    track = build_monza()
    vehicle = Vehicle(VEHICLE_MASS_KG)
    battery = Battery(BATTERY_CAPACITY_J, soc=0.6)
    controller = ConservativeController()

    sim = SimulationRunner(track, vehicle, battery, controller)
    results = sim.run_lap()

    n = min(
        len(results["time_history"]),
        len(results["power_history"]),
        len(results["soc_history"]),
        len(results["pos_history"]),
        len(results["speed_history"]),
    )

    df = pd.DataFrame({
    "time":         results["time_history"][:n],
    "power":        results["power_history"][:n],
    "soc":          results["soc_history"][:n],
    "distance":     results["pos_history"][:n],
    "speed":        results["speed_history"][:n],
    "segment_name": results["seg_name_history"][:n],
    "segment_type": results["seg_type_history"][:n],
    })
    df["cumulative_energy_deployed_j"] = df["power"].cumsum() * 0.2  # dt=0.2s
    df.to_csv("results/monza_telemetry.csv", index=False)
    print("Lap time:", results["lap_time_s"])


if __name__ == "__main__":
    run()