# experiments/tracks.py
"""
Shared track definitions used by all experiment scripts.
Add new tracks here and import them wherever needed.
"""
from sim.track import Segment, Track
from utils.units import kmh_to_mps


def build_monza() -> Track:
    """
    Simplified Monza circuit (12 segments).
    Speeds converted from km/h to m/s.
    """
    segments = [
        Segment("Main Straight",  "straight", 900,  kmh_to_mps(200), kmh_to_mps(340)),
        Segment("T1 Brake",       "brake",    150,  kmh_to_mps(340), kmh_to_mps(90)),
        Segment("T1 Corner",      "corner",   120,  kmh_to_mps(90),  kmh_to_mps(110)),
        Segment("Curva Grande",   "corner",   700,  kmh_to_mps(280), kmh_to_mps(300)),
        Segment("Roggia Brake",   "brake",    150,  kmh_to_mps(330), kmh_to_mps(100)),
        Segment("Roggia Corner",  "corner",   150,  kmh_to_mps(100), kmh_to_mps(140)),
        Segment("Lesmo 1",        "corner",   200,  kmh_to_mps(150), kmh_to_mps(180)),
        Segment("Lesmo 2",        "corner",   250,  kmh_to_mps(160), kmh_to_mps(200)),
        Segment("Serraglio",      "straight", 800,  kmh_to_mps(200), kmh_to_mps(330)),
        Segment("Ascari",         "corner",   350,  kmh_to_mps(150), kmh_to_mps(220)),
        Segment("Back Straight",  "straight", 900,  kmh_to_mps(220), kmh_to_mps(340)),
        Segment("Parabolica",     "corner",   500,  kmh_to_mps(180), kmh_to_mps(240)),
    ]
    return Track(segments)