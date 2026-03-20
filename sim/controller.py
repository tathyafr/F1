# sim/controller.py
from abc import ABC, abstractmethod
from typing import Dict, List, Optional
from sim.config import MGUK_POWER_LIMIT_W, ENERGY_TO_TIME_COEFF
from sim.vehicle import Vehicle
from sim.track import Segment
from sim.battery import Battery
import math


class Controller(ABC):
    """
    Abstract controller class.

    decide_power(state, dt, upcoming_segments) -> power_in_watts (float)
    'state' is a dictionary with keys: 'soc' (float), 'v' (float) etc.
    """

    @abstractmethod
    def decide_power(self, state: Dict, dt: float, upcoming: Optional[List[Segment]] = None) -> float:
        raise NotImplementedError


class BaselineController(Controller):
    """
    ERS-OFF baseline: deploys zero power at all times.
    Used as the reference point for all strategy comparisons.
    Without this, improvements are relative to an undefined baseline.
    """

    def decide_power(self, state: Dict, dt: float, upcoming: Optional[List[Segment]] = None) -> float:
        return 0.0


class ConservativeController(Controller):
    """
    Deploy up to MGUK_POWER_LIMIT only if SOC is above a threshold.
    """

    def __init__(self, soc_threshold: float = 0.6, deploy_fraction: float = 1.0):
        self.soc_threshold = soc_threshold
        self.deploy_fraction = max(0.0, min(1.0, deploy_fraction))

    def decide_power(self, state: Dict, dt: float, upcoming: Optional[List[Segment]] = None) -> float:
        soc = float(state.get("soc", 0.5))
        if soc > self.soc_threshold:
            return MGUK_POWER_LIMIT_W * self.deploy_fraction
        return 0.0


class AggressiveController(Controller):
    """
    Spend a fixed energy budget per lap (E_budget_j). Deploy continuously up to MGUK limit until
    budget exhausted. The controller keeps state for remaining budget (per-run).
    """

    def __init__(self, energy_budget_j: float):
        self.energy_budget_j = float(energy_budget_j)
        self._remaining = float(energy_budget_j)

    def start_lap(self):
        self._remaining = float(self.energy_budget_j)

    def decide_power(self, state: Dict, dt: float, upcoming: Optional[List[Segment]] = None) -> float:
        if self._remaining <= 0:
            return 0.0
        max_possible = MGUK_POWER_LIMIT_W
        requested = max_possible
        energy_requested = requested * dt
        energy_used = min(self._remaining, energy_requested)
        # actual power is energy_used / dt
        power = energy_used / max(dt, 1e-9)
        self._remaining -= energy_used
        return power


class LookaheadController(Controller):
    """
    Simple greedy lookahead: approximate the marginal time benefit of deploying energy in
    upcoming segments, and decide to deploy if expected benefit > threshold.
    This is a simple, deterministic heuristic — not an optimal DP.
    """

    def __init__(self, vehicle: Vehicle, power_limit_w: float = MGUK_POWER_LIMIT_W, energy_to_time_coeff: float = ENERGY_TO_TIME_COEFF):
        self.vehicle = vehicle
        self.power_limit_w = power_limit_w
        self.energy_to_time_coeff = energy_to_time_coeff

    def decide_power(self, state: Dict, dt: float, upcoming: Optional[List[Segment]] = None) -> float:
        # default: no upcoming segments => conservative
        if upcoming is None or len(upcoming) == 0:
            return 0.0

        soc = float(state.get("soc", 0.5))
        v = float(state.get("v", 10.0))

        # Very simple heuristic:
        # compute approximate energy that could be deployed during next segment
        first_seg = upcoming[0]
        seg_time = max(1e-6, first_seg.length_m / max(0.1, 0.5 * (first_seg.v_entry + first_seg.v_exit)))
        max_energy_deployable = self.power_limit_w * seg_time

        # Estimate time saved if we used that energy on the segment using vehicle estimate
        estimated_time_saved = self.vehicle.estimate_time_saved_by_energy(max_energy_deployable, v, first_seg.length_m)

        # Convert to a simple score (time saved per J)
        score = estimated_time_saved / max(1e-9, max_energy_deployable)

        # Decide: if score is above a tiny threshold, deploy at power limit
        threshold = self.energy_to_time_coeff  # tunable
        if score > threshold and soc > 0.12:
            return self.power_limit_w
        return 0.0


class OptimalController(Controller):
    """
    Offline optimal ERS deployment schedule computed via scipy.optimize (SLSQP).

    Models the real-world approach: a pre-race optimized deployment map is
    uploaded to the car's ERS control unit and executed deterministically.

    Decision variables: x[i] = fraction of MGUK_POWER_LIMIT_W to deploy on segment i.
    Objective: minimize total lap time.
    Constraint: SOC at end of lap >= SOC_MIN (do not arrive drained).

    The schedule is computed once at construction. During decide_power(), the
    controller returns the pre-computed power for the current segment index.
    """

    def __init__(
        self,
        vehicle: Vehicle,
        track,
        battery: Battery,
        regen_efficiency: float = 0.6,
        dt: float = 0.2,
    ):
        from sim.config import SOC_MIN
        self._SOC_MIN = SOC_MIN
        self._seg_index = 0
        self._current_seg_name = None
        self._schedule = self._optimize(vehicle, track, battery, regen_efficiency, dt)

    def _simulate_lap_fast(self, x, vehicle, track, battery_init_soc, battery_capacity_j,
                           regen_efficiency, dt):
        """Lightweight simulation used by the optimizer (no history tracking)."""
        import math
        from sim.config import SOC_MIN, SOC_MAX, MGUK_POWER_LIMIT_W

        soc = battery_init_soc
        total_time = 0.0
        total_deployed = 0.0

        for i, seg in enumerate(track.segments):
            avg_v = max(0.1, 0.5 * (seg.v_entry + seg.v_exit))
            seg_time = seg.length_m / avg_v
            n_steps = max(1, int(math.ceil(seg_time / dt)))

            # regen
            if seg.v_entry > seg.v_exit:
                e_brake = 0.5 * vehicle.mass * (seg.v_entry ** 2 - seg.v_exit ** 2)
                e_rec = regen_efficiency * e_brake
                available_cap = (SOC_MAX - soc) * battery_capacity_j
                accepted = min(e_rec, available_cap)
                soc += accepted / battery_capacity_j

            # deployment
            power = x[i] * MGUK_POWER_LIMIT_W
            energy_request = power * seg_time
            available_j = max(0.0, (soc - SOC_MIN) * battery_capacity_j)
            deployed = min(energy_request, available_j)
            soc -= deployed / battery_capacity_j
            soc = max(SOC_MIN, min(SOC_MAX, soc))
            total_deployed += deployed

            # time savings: calibrated linear model, straights only (mirrors sim_runner logic)
            if seg.seg_type == "straight":
                time_saved = deployed * ENERGY_TO_TIME_COEFF
            else:
                time_saved = 0.0
            effective_time = max(seg_time - time_saved, seg.length_m / 100.0)
            total_time += effective_time

        return total_time, soc, total_deployed

    def _optimize(self, vehicle, track, battery, regen_efficiency, dt):
        import numpy as np
        from scipy.optimize import minimize
        from sim.config import SOC_MIN, ENERGY_PER_LAP_J

        n = track.num_segments()
        x0 = np.ones(n) * 0.5

        def objective(x):
            t, _, _ = self._simulate_lap_fast(
                x, vehicle, track, battery.soc, battery.capacity_j, regen_efficiency, dt
            )
            return t

        def soc_constraint(x):
            # SOC at end of lap must be >= SOC_MIN
            _, soc_end, _ = self._simulate_lap_fast(
                x, vehicle, track, battery.soc, battery.capacity_j, regen_efficiency, dt
            )
            return soc_end - SOC_MIN

        def fia_energy_constraint(x):
            # FIA Article 5.2.3: total MGU-K deployment <= 4 MJ per lap
            _, _, deployed = self._simulate_lap_fast(
                x, vehicle, track, battery.soc, battery.capacity_j, regen_efficiency, dt
            )
            return ENERGY_PER_LAP_J - deployed  # >= 0 means compliant

        result = minimize(
            objective,
            x0,
            method="SLSQP",
            bounds=[(0.0, 1.0)] * n,
            constraints=[
                {"type": "ineq", "fun": soc_constraint},
                {"type": "ineq", "fun": fia_energy_constraint},
            ],
            options={"maxiter": 300, "ftol": 1e-7},
        )
        return result.x.tolist()

    def start_lap(self):
        self._seg_index = 0
        self._current_seg_name = None

    def decide_power(self, state: Dict, dt: float, upcoming: Optional[List[Segment]] = None) -> float:
        seg_name = state.get("seg_name", "")
        if seg_name != self._current_seg_name:
            if self._current_seg_name is not None:
                self._seg_index = min(self._seg_index + 1, len(self._schedule) - 1)
            self._current_seg_name = seg_name
        fraction = self._schedule[self._seg_index]
        return fraction * MGUK_POWER_LIMIT_W
