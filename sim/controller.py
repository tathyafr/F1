# sim/controller.py
from abc import ABC, abstractmethod
from typing import Dict, List, Optional
from sim.config import MGUK_POWER_LIMIT_W, ENERGY_TO_TIME_COEFF
from sim.vehicle import Vehicle
from sim.track import Segment
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
