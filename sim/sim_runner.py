# sim/sim_runner.py
from typing import Dict, List, Optional
from sim.track import Track, Segment
from sim.vehicle import Vehicle
from sim.battery import Battery
from sim.controller import Controller
from sim.config import DEFAULT_DT, DEFAULT_REGEN_EFFICIENCY, MGUK_POWER_LIMIT_W
import math


class SimulationRunner:
    """
    Runs a single-lap simulation using a segment-based track with an internal
    time-stepped loop inside each segment.

    Outputs a result dict with energy accounting and histories.
    """

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
        # reset battery histories for this run
        self.battery.reset_history()

        total_time = 0.0
        power_history: List[float] = []
        time_history: List[float] = []
        pos_history: List[float] = []
        soc_history = [self.battery.soc]

        position_m = 0.0

        for seg_idx, seg in enumerate(self.track.segments):
            # compute nominal segment duration from average speed
            avg_v = max(0.1, 0.5 * (seg.v_entry + seg.v_exit))
            seg_time = seg.length_m / avg_v
            n_steps = max(1, int(math.ceil(seg_time / self.dt)))
            step_dt = seg_time / n_steps

            # If there is braking in this segment, harvest braking energy once (lumped)
            e_brake_total = 0.0
            if seg.v_entry > seg.v_exit:
                e_brake_total = self.vehicle.braking_energy_j(seg.v_entry, seg.v_exit)
                e_rec_total = self.regen_efficiency * e_brake_total
                # add harvested energy (battery will clip/waste if full)
                self.battery.add_energy(e_rec_total)
            else:
                e_rec_total = 0.0

            # Time-step through the segment; controller can deploy energy each dt
            for step in range(n_steps):
                t = total_time + step * step_dt

                # Prepare state for controller
                # We'll use current soc and a simple speed estimate (linear interp)
                # speed interpolation between entry and exit across the segment
                frac = (step + 0.5) / n_steps
                current_v = max(0.1, (1 - frac) * seg.v_entry + frac * seg.v_exit)

                state = {"soc": self.battery.soc, "v": current_v, "segment": seg, "segment_index": seg_idx}

                # Determine upcoming segments slice (for lookahead)
                upcoming = self.track.segments[seg_idx : seg_idx + 3]  # small lookahead window

                # controller returns power in W (0..MGUK_LIMIT)
                power_w = float(self.controller.decide_power(state, step_dt, upcoming))
                power_w = max(0.0, min(power_w, MGUK_POWER_LIMIT_W))

                energy_request_j = power_w * step_dt
                energy_delivered_j = self.battery.deploy_energy(energy_request_j)

                power_history.append(power_w)
                time_history.append(t)
                pos_history.append(position_m + (step + 0.5) * (seg.length_m / n_steps))
                soc_history.append(self.battery.soc)

            total_time += seg_time
            position_m += seg.length_m

        # end of lap
        results = {
            "lap_time_s": total_time,
            "soc_end": self.battery.soc,
            "soc_start": soc_history[0] if soc_history else None,
            "harvested_j": self.battery.total_harvested,
            "deployed_j": self.battery.total_deployed,
            "wasted_j": self.battery.total_wasted,
            "soc_history": self.battery.soc_history.copy(),
            "power_history": power_history,
            "time_history": time_history,
            "pos_history": pos_history,
        }

        # energy conservation quick-check (useful in tests)
        # Δbattery = energy_in - energy_out - wasted (approximately)
        # where energy_in == harvested_j, energy_out == deployed_j
        results["delta_battery_energy_j"] = (results["soc_end"] - results["soc_start"]) * self.battery.capacity_j
        results["check_balance"] = results["harvested_j"] - results["deployed_j"] - results["wasted_j"] - results["delta_battery_energy_j"]

        return results
