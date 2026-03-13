# experiments/run_experiment.py

import pandas as pd

from sim.track import Segment, Track
from sim.vehicle import Vehicle
from sim.battery import Battery
from sim.controller import ConservativeController, AggressiveController
from sim.sim_runner import SimulationRunner
from sim.config import VEHICLE_MASS_KG, BATTERY_CAPACITY_J
from utils.units import kmh_to_mps


def build_track():

    segments = [
        Segment("Straight1", "straight", 800, kmh_to_mps(280), kmh_to_mps(280)),
        Segment("Brake1", "brake", 200, kmh_to_mps(280), kmh_to_mps(120)),
        Segment("Corner", "corner", 150, kmh_to_mps(120), kmh_to_mps(120)),
        Segment("Straight2", "straight", 600, kmh_to_mps(120), kmh_to_mps(260)),
    ]

    return Track(segments)


def run():

    track = build_track()

    results = []

    controllers = {
        "conservative": ConservativeController(),
        "aggressive": AggressiveController(energy_budget_j=2_000_000),
    }

    initial_socs = [0.3, 0.5, 0.7, 0.9]

    for name, controller in controllers.items():

        for soc in initial_socs:

            vehicle = Vehicle(VEHICLE_MASS_KG)

            battery = Battery(BATTERY_CAPACITY_J, soc=soc)

            sim = SimulationRunner(track, vehicle, battery, controller)

            result = sim.run_lap()

            results.append({
                "controller": name,
                "initial_soc": soc,
                "lap_time": result["lap_time_s"],
                "harvested": result["harvested_j"],
                "deployed": result["deployed_j"],
                "wasted": result["wasted_j"],
            })

    df = pd.DataFrame(results)

    df.to_csv("results/experiment_results.csv", index=False)

    print(df)


if __name__ == "__main__":
    run()
