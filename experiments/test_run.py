# experiments/test_run.py

from sim.track import Segment, Track
from sim.vehicle import Vehicle
from sim.battery import Battery
from sim.controller import ConservativeController
from sim.sim_runner import SimulationRunner
from sim.config import VEHICLE_MASS_KG, BATTERY_CAPACITY_J
from utils.units import kmh_to_mps


def build_test_track():

    segments = [
        Segment("Straight", "straight", 800, kmh_to_mps(280), kmh_to_mps(280)),
        Segment("Brake", "brake", 200, kmh_to_mps(280), kmh_to_mps(120)),
        Segment("Corner", "corner", 150, kmh_to_mps(120), kmh_to_mps(120)),
        Segment("Straight2", "straight", 600, kmh_to_mps(120), kmh_to_mps(260)),
    ]

    return Track(segments)


def main():

    track = build_test_track()

    vehicle = Vehicle(VEHICLE_MASS_KG)

    battery = Battery(BATTERY_CAPACITY_J, soc=0.5)

    controller = ConservativeController()

    sim = SimulationRunner(track, vehicle, battery, controller)

    results = sim.run_lap()

    print("Lap time:", results["lap_time_s"])
    print("Energy harvested:", results["harvested_j"])
    print("Energy deployed:", results["deployed_j"])
    print("Energy wasted:", results["wasted_j"])


if __name__ == "__main__":
    main()
