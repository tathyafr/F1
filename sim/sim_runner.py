# sim/sim_runner.py
from typing import Dict, List
from sim.track import Track
from sim.vehicle import Vehicle
from sim.battery import Battery
from sim.controller import Controller
from sim.config import DEFAULT_DT, DEFAULT_REGEN_EFFICIENCY, MGUK_POWER_LIMIT_W, ENERGY_TO_TIME_COEFF
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
    ):
        self.track = track
        self.vehicle = vehicle
        self.battery = battery
        self.controller = controller
        self.dt = dt
        self.regen_efficiency = regen_efficiency

    def run_lap(self) -> Dict:

        self.battery.reset_history()

        # Bug fix 2: reset AggressiveController budget at the start of each lap
        if hasattr(self.controller, "start_lap"):
            self.controller.start_lap()

        baseline_time = self.track.lap_base_time()
        total_time = 0.0

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

            # Bug fix 1: pass upcoming segments so LookaheadController can use them
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
                actual_deployed = self.battery.deploy_energy(energy_request)
                seg_deployed_j += actual_deployed

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
            else:
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