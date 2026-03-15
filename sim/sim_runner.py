from typing import Dict, List
from sim.track import Track
from sim.vehicle import Vehicle
from sim.battery import Battery
from sim.controller import Controller
from sim.config import DEFAULT_DT, DEFAULT_REGEN_EFFICIENCY, MGUK_POWER_LIMIT_W
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

        total_time = 0.0

        power_history: List[float] = []
        time_history: List[float] = []
        pos_history: List[float] = []
        soc_history: List[float] = []
        speed_history: List[float] = []

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

            for step in range(n_steps):

                frac = (step + 0.5) / n_steps

                current_v = max(
                    0.1,
                    (1 - frac) * seg.v_entry + frac * seg.v_exit
                )

                state = {
                    "soc": self.battery.soc,
                    "v": current_v
                }

                power = self.controller.decide_power(state, step_dt)

                power = max(0.0, min(power, MGUK_POWER_LIMIT_W))

                energy_request = power * step_dt

                self.battery.deploy_energy(energy_request)

                # telemetry
                time_history.append(total_time + step * step_dt)
                power_history.append(power)
                pos_history.append(position_m + frac * seg.length_m)
                soc_history.append(self.battery.soc)
                speed_history.append(current_v)

            total_time += seg_time
            position_m += seg.length_m

        results = {

            "lap_time_s": total_time,

            "soc_end": self.battery.soc,

            "harvested_j": self.battery.total_harvested,
            "deployed_j": self.battery.total_deployed,
            "wasted_j": self.battery.total_wasted,

            "soc_history": soc_history,
            "power_history": power_history,
            "time_history": time_history,
            "pos_history": pos_history,
            "speed_history": speed_history,
        }

        return results
