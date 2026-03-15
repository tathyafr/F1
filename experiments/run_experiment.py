import pandas as pd

from sim.track import Segment, Track
from sim.vehicle import Vehicle
from sim.battery import Battery
from sim.controller import (
    ConservativeController,
    AggressiveController,
    LookaheadController
)
from sim.sim_runner import SimulationRunner
from sim.config import VEHICLE_MASS_KG, BATTERY_CAPACITY_J
from utils.units import kmh_to_mps


def build_monza():

    segments = [

        Segment("Main Straight", "straight", 900, kmh_to_mps(200), kmh_to_mps(340)),
        Segment("T1 Brake", "brake", 150, kmh_to_mps(340), kmh_to_mps(90)),
        Segment("T1 Corner", "corner", 120, kmh_to_mps(90), kmh_to_mps(110)),

        Segment("Curva Grande", "corner", 700, kmh_to_mps(280), kmh_to_mps(300)),

        Segment("Roggia Brake", "brake", 150, kmh_to_mps(330), kmh_to_mps(100)),
        Segment("Roggia Corner", "corner", 150, kmh_to_mps(100), kmh_to_mps(140)),

        Segment("Lesmo 1", "corner", 200, kmh_to_mps(150), kmh_to_mps(180)),
        Segment("Lesmo 2", "corner", 250, kmh_to_mps(160), kmh_to_mps(200)),

        Segment("Serraglio", "straight", 800, kmh_to_mps(200), kmh_to_mps(330)),

        Segment("Ascari", "corner", 350, kmh_to_mps(150), kmh_to_mps(220)),

        Segment("Back Straight", "straight", 900, kmh_to_mps(220), kmh_to_mps(340)),

        Segment("Parabolica", "corner", 500, kmh_to_mps(180), kmh_to_mps(240)),
    ]

    return Track(segments)


def run():

    track = build_monza()

    vehicle = Vehicle(VEHICLE_MASS_KG)

    controllers = {
        "conservative": ConservativeController(),
        "aggressive": AggressiveController(energy_budget_j=4e6),
        "lookahead": LookaheadController(vehicle)
    }

    initial_socs = [0.4, 0.6, 0.8]

    results = []

    for strategy, controller in controllers.items():

        for soc in initial_socs:

            battery = Battery(BATTERY_CAPACITY_J, soc=soc)

            sim = SimulationRunner(track, vehicle, battery, controller)

            result = sim.run_lap()

            results.append({
                "strategy": strategy,
                "initial_soc": soc,
                "lap_time": result["lap_time_s"],
                "energy_deployed": result["deployed_j"],
                "energy_harvested": result["harvested_j"],
                "energy_wasted": result["wasted_j"]
            })

            print(strategy, soc, result["lap_time_s"])

    df = pd.DataFrame(results)

    df.to_csv("results/strategy_results.csv", index=False)

    print("\nSaved results to results/strategy_results.csv")


if __name__ == "__main__":
    run()
