# sim/vehicle.py
import math


class Vehicle:
    def __init__(self, mass_kg: float):
        self.mass = float(mass_kg)
        self.drag_coeff = 0.7      # CdA (m^2), typical F1
        self.air_density = 1.225   # kg/m^3

    def braking_energy_j(self, v_entry: float, v_exit: float) -> float:
        if v_entry <= v_exit:
            return 0.0
        return 0.5 * self.mass * (v_entry ** 2 - v_exit ** 2)

    def estimate_time_saved_by_energy(self, energy_j: float, v_ref: float, distance_m: float) -> float:
        if energy_j <= 0 or v_ref <= 0 or distance_m <= 0:
            return 0.0
        drag_power = 0.5 * self.air_density * self.drag_coeff * (v_ref ** 3)
        net_energy = max(0.0, energy_j - drag_power * (distance_m / max(v_ref, 0.1)))
        ke_new = 0.5 * self.mass * (v_ref ** 2) + net_energy
        v_new = math.sqrt(max(0.0, 2.0 * ke_new / self.mass))
        if v_new <= 0:
            return 0.0
        return max(0.0, distance_m / v_ref - distance_m / v_new)