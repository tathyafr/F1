# experiments/monza_run.py

import pandas as pd

from sim.track import Segment, Track
from sim.vehicle import Vehicle
from sim.battery import Battery
from sim.controller import ConservativeController
from sim.sim_runner import SimulationRunner
from sim.config import VEHICLE_MASS_KG, BATTERY_CAPACITY_J
from utils.units import kmh_to_mps


def build_monza():

    segments = [

        # start / pit straight
        Segment("Main Straight", "straight", 900, kmh_to_mps(200), kmh_to_mps(340)),

        # T1 braking
        Segment("T1 Brake", "brake", 150, kmh_to_mps(340), kmh_to_mps(90)),

        Segment("T1 Corner", "corner", 120, kmh_to_mps(90), kmh_to_mps(110)),

        # Curva Grande
        Segment("Curva Grande", "corner", 700, kmh_to_mps(280), kmh_to_mps(300)),

        # T4 braking
        Segment("Roggia Brake", "brake", 150, kmh_to_mps(330), kmh_to_mps(100)),

        Segment("Roggia Corner", "corner", 150, kmh_to_mps(100), kmh_to_mps(140)),

        # Lesmo 1
        Segment("Lesmo 1", "corner", 200, kmh_to_mps(150), kmh_to_mps(180)),

        # Lesmo 2
        Segment("Lesmo 2", "corner", 250, kmh_to_mps(160), kmh_to_mps(200)),

        # Serraglio straight
        Segment("Serraglio", "straight", 800, kmh_to_mps(200), kmh_to_mps(330)),

        # Ascari
        Segment("Ascari", "corner", 350, kmh_to_mps(150), kmh_to_mps(220)),

        # Back straight
        Segment("Back Straight", "straight", 900, kmh_to_mps(220), kmh_to_mps(340)),

        # Parabolica
        Segment("Parabolica", "corner", 500, kmh_to_mps(180), kmh_to_mps(240)),
    ]

    return Track(segments)


def run():

    track = build_monza()

    vehicle = Vehicle(VEHICLE_MASS_KG)

    battery = Battery(BATTERY_CAPACITY_J, soc=0.6)

    controller = ConservativeController()

    sim = SimulationRunner(track, vehicle, battery, controller)

    results = sim.run_lap()

    df = pd.DataFrame({
        "time": results["time_history"],
        "power": results["power_history"],
        "soc": results["soc_history"][:len(results["time_history"])],
        "distance": results["pos_history"]
    })

    df.to_csv("results/monza_telemetry.csv", index=False)

    print("Lap time:", results["lap_time_s"])


if __name__ == "__main__":
    run()
