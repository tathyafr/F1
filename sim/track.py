# sim/track.py
from dataclasses import dataclass
from typing import List


@dataclass
class Segment:
    """
    A track segment.
      - name: descriptive
      - seg_type: 'straight', 'brake', 'corner' etc. (used for analysis)
      - length_m: segment length in meters
      - v_entry: entry speed (m/s)
      - v_exit: exit speed (m/s)
    Notes:
      Speeds are expected in m/s (use utils.kmh_to_mps if starting from km/h).
    """
    name: str
    seg_type: str
    length_m: float
    v_entry: float
    v_exit: float


class Track:
    def __init__(self, segments: List[Segment]):
        if not segments:
            raise ValueError("Track must contain at least one Segment.")
        self.segments = list(segments)

    def total_length(self) -> float:
        return sum(s.length_m for s in self.segments)

    def num_segments(self) -> int:
        return len(self.segments)

    def lap_base_time(self) -> float:
        """Return rough baseline lap time computed as sum(length / avg_speed)."""
        total = 0.0
        for s in self.segments:
            avg_v = max(0.1, 0.5 * (s.v_entry + s.v_exit))
            total += s.length_m / avg_v
        return total
