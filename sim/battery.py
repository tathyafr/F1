# sim/battery.py
from typing import List, Optional
from dataclasses import dataclass, field
from sim.config import SOC_MIN, SOC_MAX


@dataclass
class Battery:
    """
    Simple battery model with SOC state and bookkeeping.

    All energies are in joules. SOC is fraction in [SOC_MIN, SOC_MAX].
    """
    capacity_j: float
    soc: float = 0.5

    # bookkeeping
    total_harvested: float = 0.0
    total_deployed: float = 0.0
    total_wasted: float = 0.0

    # histories for plotting / analysis
    soc_history: List[float] = field(default_factory=list)
    harvested_history: List[float] = field(default_factory=list)
    deployed_history: List[float] = field(default_factory=list)
    wasted_history: List[float] = field(default_factory=list)

    def _clip_soc(self) -> None:
        if self.soc > SOC_MAX:
            self.soc = SOC_MAX
        if self.soc < SOC_MIN:
            self.soc = SOC_MIN

    def add_energy(self, energy_j: float) -> float:
        """
        Add harvested energy (J). Returns actual accepted energy (J).
        If battery overflows, the overflow is counted as wasted.
        """
        if energy_j <= 0:
            return 0.0

        available_capacity_j = (SOC_MAX - self.soc) * self.capacity_j
        accepted = min(energy_j, available_capacity_j)
        wasted = max(0.0, energy_j - accepted)

        # update
        self.soc += accepted / self.capacity_j
        self.total_harvested += accepted
        self.total_wasted += wasted

        # history
        self.soc_history.append(self.soc)
        self.harvested_history.append(accepted)
        self.wasted_history.append(wasted)
        return accepted

    def deploy_energy(self, energy_j: float) -> float:
        """
        Consume energy_j (J) from battery to deploy. Returns actual energy delivered.
        Will not go below SOC_MIN; if requested energy is larger than available, only use available.
        """
        if energy_j <= 0:
            return 0.0

        available_j = (self.soc - SOC_MIN) * self.capacity_j
        used = min(energy_j, max(0.0, available_j))

        self.soc -= used / self.capacity_j
        self.total_deployed += used

        # history
        self.deployed_history.append(used)
        self.soc_history.append(self.soc)

        # keep soc in bounds
        self._clip_soc()
        return used

    def get_energy_j(self) -> float:
        return self.soc * self.capacity_j

    def reset_history(self) -> None:
        self.soc_history.clear()
        self.harvested_history.clear()
        self.deployed_history.clear()
        self.wasted_history.clear()
