# sim/vehicle.py
from typing import Optional


class Vehicle:
    """
    Simple vehicle physics helper. Focuses on kinetic-energy bookkeeping and a
    first-order time/benefit estimate for deployed energy.
    """

    def __init__(self, mass_kg: float):
        self.mass = float(mass_kg)
        # Add to __init__
        self.drag_coeff = 0.7      # CdA (m^2), typical F1
        self.air_density = 1.225   # kg/m^3

        # Replace estimate_time_saved_by_energy with:
        def estimate_time_saved_by_energy(self, energy_j: float, v_ref: float, distance_m: float) -> float:
            if energy_j <= 0 or v_ref <= 0 or distance_m <= 0:
                return 0.0
            import math
            drag_power = 0.5 * self.air_density * self.drag_coeff * (v_ref ** 3)
            net_energy = max(0.0, energy_j - drag_power * (distance_m / max(v_ref, 0.1)))
            ke_new = 0.5 * self.mass * (v_ref ** 2) + net_energy
            v_new = math.sqrt(max(0.0, 2.0 * ke_new / self.mass))
            if v_new <= 0:
                return 0.0
            return max(0.0, distance_m / v_ref - distance_m / v_new)

    def braking_energy_j(self, v_entry: float, v_exit: float) -> float:
        """
        Kinetic energy available from v_entry -> v_exit (in joules).
        v in m/s.
        If v_exit >= v_entry returns 0.
        """
        if v_entry <= v_exit:
            return 0.0
        return 0.5 * self.mass * (v_entry ** 2 - v_exit ** 2)

    def estimate_time_saved_by_energy(self, energy_j: float, v_ref: float, distance_m: float) -> float:
        """
        Rough, first-order estimate of time saved by spending `energy_j` (J)
        to increase kinetic energy while the car traverses `distance_m` at
        reference speed `v_ref` (m/s).

        Approach:
          - treat energy_j as an addition to kinetic energy: KE_new = 0.5*m*v^2 + energy_j
          - compute implied v_new = sqrt(v^2 + 2*energy_j/m)
          - estimate time saved = distance/v_ref - distance/v_new

        This is an approximation — assumes energy can be applied efficiently
        and instantaneously to increase cruising speed. Use sensitivity analysis.
        """
        if energy_j <= 0 or v_ref <= 0 or distance_m <= 0:
            return 0.0
        import math

        ke_initial = 0.5 * self.mass * (v_ref ** 2)
        ke_new = ke_initial + energy_j
        v_new = math.sqrt(max(0.0, 2.0 * ke_new / self.mass))
        if v_new <= 0.0:
            return 0.0

        t_before = distance_m / v_ref
        t_after = distance_m / v_new
        saved = max(0.0, t_before - t_after)
        return saved
