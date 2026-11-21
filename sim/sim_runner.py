# sim/sim_runner.py
from typing import Dict, List
from sim.track import Track
from sim.vehicle import Vehicle
from sim.battery import Battery
from sim.controller import Controller
from sim.config import DEFAULT_DT, DEFAULT_REGEN_EFFICIENCY, MGUK_POWER_LIMIT_W, ENERGY_TO_TIME_COEFF, ENERGY_PER_LAP_J as _DEFAULT_ENERGY_CAP_J
import math


class SimulationRunner:

    def __init__(
        self,
        track: Track,
        vehicle: Vehicle,
        battery: Battery,
        controller: Controller,
        dt: float = DEFAULT_DT,
        regen_efficiency: float = DEFAULT_REGEN_EFFICIENCY,
        energy_cap_j: float = _DEFAULT_ENERGY_CAP_J,
        corner_benefit_fraction: float = 0.0,
    ):
        self.track = track
        self.vehicle = vehicle
        self.battery = battery
        self.controller = controller
        self.dt = dt
        self.regen_efficiency = regen_efficiency
        self.energy_cap_j = energy_cap_j
        # Fraction of the straight-line time benefit that energy deployed in a
        # corner is assumed to give. 0.0 = the main model's assumption (corners
        # are grip-limited, so extra power is useless). Swept in
        # experiments/corner_benefit_sensitivity.py to test that assumption.
        self.corner_benefit_fraction = corner_benefit_fraction

    def run_lap(self) -> Dict:

        self.battery.reset_history()

        # Reset per-lap controller state (e.g. the Aggressive budget)
        if hasattr(self.controller, "start_lap"):
            self.controller.start_lap()

        baseline_time = self.track.lap_base_time()
        total_time = 0.0
        lap_deployed_j = 0.0  # FIA Article 5.2.3 hard cap: <= ENERGY_PER_LAP_J per lap

        power_history: List[float] = []
        time_history: List[float] = []
        pos_history: List[float] = []
        soc_history: List[float] = []
        speed_history: List[float] = []
        seg_name_history: List[str] = []
        seg_type_history: List[str] = []

        position_m = 0.0

        for seg_idx, seg in enumerate(self.track.segments):

            avg_v = max(0.1, 0.5 * (seg.v_entry + seg.v_exit))
            seg_time = seg.length_m / avg_v

            n_steps = max(1, int(math.ceil(seg_time / self.dt)))
            step_dt = seg_time / n_steps

            # braking energy recovery
            if seg.v_entry > seg.v_exit:
                e_brake = self.vehicle.braking_energy_j(seg.v_entry, seg.v_exit)
                e_rec = self.regen_efficiency * e_brake
                self.battery.add_energy(e_rec)

            # Upcoming segments are passed so the Lookahead controller can plan ahead
            upcoming = self.track.segments[seg_idx + 1:]

            seg_deployed_j = 0.0

            for step in range(n_steps):

                frac = (step + 0.5) / n_steps

                current_v = max(
                    0.1,
                    (1 - frac) * seg.v_entry + frac * seg.v_exit,
                )

                state = {
                    "soc": self.battery.soc,
                    "v": current_v,
                    "seg_type": seg.seg_type,
                    "seg_name": seg.name,
                }

                power = self.controller.decide_power(state, step_dt, upcoming)

                power = max(0.0, min(power, MGUK_POWER_LIMIT_W))

                energy_request = power * step_dt
                # FIA Article 5.2.3: hard cap on total MGU-K deployment per lap
                fia_headroom = max(0.0, self.energy_cap_j - lap_deployed_j)
                energy_request = min(energy_request, fia_headroom)
                actual_deployed = self.battery.deploy_energy(energy_request)
                seg_deployed_j += actual_deployed
                lap_deployed_j += actual_deployed

                time_history.append(total_time + step * step_dt)
                power_history.append(power)
                pos_history.append(position_m + frac * seg.length_m)
                soc_history.append(self.battery.soc)
                speed_history.append(current_v)
                seg_name_history.append(seg.name)
                seg_type_history.append(seg.seg_type)

            # Convert deployed energy to lap time savings.
            # Uses a calibrated linear coefficient (ENERGY_TO_TIME_COEFF = 1e-7 s/J),
            # equivalent to ~0.1 s per MJ, matching real F1 ERS benefit at Monza (~0.4s / 4 MJ).
            # Applied only on straights: corners are lateral-grip-limited, not power-limited.
            if seg.seg_type == "straight":
                time_saved = seg_deployed_j * ENERGY_TO_TIME_COEFF
            elif seg.seg_type == "corner":
                time_saved = seg_deployed_j * ENERGY_TO_TIME_COEFF * self.corner_benefit_fraction
            else:  # braking zones: deploying while braking gives no benefit
                time_saved = 0.0
            effective_seg_time = max(seg_time - time_saved, seg.length_m / 100.0)  # 100 m/s ~360 km/h physical cap
            total_time += effective_seg_time
            position_m += seg.length_m

        results = {
            "lap_time_s": total_time,
            "lap_time_improvement_s": baseline_time - total_time,
            "soc_end": self.battery.soc,
            "harvested_j": self.battery.total_harvested,
            "deployed_j": self.battery.total_deployed,
            "wasted_j": self.battery.total_wasted,
            "soc_history": soc_history,
            "power_history": power_history,
            "time_history": time_history,
            "pos_history": pos_history,
            "speed_history": speed_history,
            "seg_name_history": seg_name_history,
            "seg_type_history": seg_type_history,
        }

        return results

    def run_laps(self, n_laps: int = 3) -> list:
        """Run multiple laps, carrying battery state across laps."""
        all_results = []
        for lap in range(n_laps):
            result = self.run_lap()
            result["lap_number"] = lap + 1
            all_results.append(result)
        return all_results