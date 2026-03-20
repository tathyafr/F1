# experiments/tracks.py
"""
Shared track definitions used across experiment scripts.
Add new tracks here as the project grows.
"""

from sim.track import Segment, Track
from utils.units import kmh_to_mps


def build_monza() -> Track:
    """
    Simplified Monza (Circuit di Monza) track model.
    12 segments covering the main circuit features.
    All speeds in m/s (converted from km/h).
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


def build_spa() -> Track:
    """
    Simplified Spa-Francorchamps track model.
    19 segments capturing the key ERS-relevant features.
    Kemmel Straight and Raidillon give high ERS deployment value.
    All speeds in m/s (converted from km/h).
    """
    segments = [
        Segment("Pit Straight",        "straight", 700,  kmh_to_mps(175), kmh_to_mps(295)),
        Segment("La Source Brake",     "brake",    150,  kmh_to_mps(295), kmh_to_mps(75)),
        Segment("La Source Corner",    "corner",   120,  kmh_to_mps(75),  kmh_to_mps(110)),
        Segment("Eau Rouge",           "corner",   400,  kmh_to_mps(200), kmh_to_mps(280)),
        Segment("Raidillon",           "corner",   400,  kmh_to_mps(280), kmh_to_mps(300)),
        Segment("Kemmel Straight",     "straight", 750,  kmh_to_mps(300), kmh_to_mps(330)),
        Segment("Les Combes Brake",    "brake",    180,  kmh_to_mps(330), kmh_to_mps(90)),
        Segment("Les Combes Corner",   "corner",   200,  kmh_to_mps(90),  kmh_to_mps(130)),
        Segment("Malmedy",             "corner",   350,  kmh_to_mps(200), kmh_to_mps(260)),
        Segment("Rivage Brake",        "brake",    120,  kmh_to_mps(280), kmh_to_mps(80)),
        Segment("Rivage Corner",       "corner",   180,  kmh_to_mps(80),  kmh_to_mps(115)),
        Segment("Fagnes Straight",     "straight", 600,  kmh_to_mps(220), kmh_to_mps(290)),
        Segment("Stavelot Brake",      "brake",    150,  kmh_to_mps(290), kmh_to_mps(100)),
        Segment("Stavelot Corner",     "corner",   250,  kmh_to_mps(100), kmh_to_mps(170)),
        Segment("Blanchimont",         "straight", 600,  kmh_to_mps(270), kmh_to_mps(315)),
        Segment("Bus Stop Brake",      "brake",    150,  kmh_to_mps(315), kmh_to_mps(80)),
        Segment("Bus Stop Chicane",    "corner",   200,  kmh_to_mps(80),  kmh_to_mps(135)),
        Segment("Pouhon",              "corner",   400,  kmh_to_mps(205), kmh_to_mps(240)),
        Segment("Campus Corner",       "corner",   300,  kmh_to_mps(180), kmh_to_mps(220)),
    ]
    return Track(segments)


def build_monaco() -> Track:
    """
    Simplified Monaco street circuit track model.
    16 segments. Low average speed (~155 km/h), heavy braking events,
    short tunnel straight. High regen opportunity but limited deployment windows.
    Segment speeds calibrated to match race-pace baseline of ~76.5 s
    (real 2023 race pace ~75–77 s; model error <2%).
    All speeds in m/s (converted from km/h).
    """
    segments = [
        Segment("Pit Straight",        "straight", 600,  kmh_to_mps(160), kmh_to_mps(275)),
        Segment("Sainte Devote Brake", "brake",    100,  kmh_to_mps(275), kmh_to_mps(80)),
        Segment("Sainte Devote",       "corner",   100,  kmh_to_mps(80),  kmh_to_mps(110)),
        Segment("Beau Rivage",         "corner",   300,  kmh_to_mps(145), kmh_to_mps(190)),
        Segment("Massenet Brake",      "brake",    80,   kmh_to_mps(220), kmh_to_mps(75)),
        Segment("Casino Square",       "corner",   150,  kmh_to_mps(80),  kmh_to_mps(115)),
        Segment("Mirabeau Brake",      "brake",    80,   kmh_to_mps(200), kmh_to_mps(65)),
        Segment("Mirabeau Corner",     "corner",   120,  kmh_to_mps(65),  kmh_to_mps(100)),
        Segment("Portier",             "corner",   150,  kmh_to_mps(130), kmh_to_mps(160)),
        Segment("Tunnel Straight",     "straight", 500,  kmh_to_mps(200), kmh_to_mps(275)),
        Segment("Nouvelle Chicane",    "brake",    100,  kmh_to_mps(275), kmh_to_mps(65)),
        Segment("Tabac",               "corner",   200,  kmh_to_mps(135), kmh_to_mps(165)),
        Segment("Swimming Pool",       "corner",   300,  kmh_to_mps(140), kmh_to_mps(170)),
        Segment("Rascasse Brake",      "brake",    80,   kmh_to_mps(200), kmh_to_mps(55)),
        Segment("Rascasse Corner",     "corner",   200,  kmh_to_mps(70),  kmh_to_mps(120)),
        Segment("Anthony Noghes",      "corner",   160,  kmh_to_mps(100), kmh_to_mps(155)),
    ]
    return Track(segments)


TRACK_REGISTRY = {
    "monza": build_monza,
    "spa": build_spa,
    "monaco": build_monaco,
}


def build_track(name: str) -> Track:
    """Build a track by name. Available tracks: monza, spa, monaco."""
    if name not in TRACK_REGISTRY:
        raise ValueError(f"Unknown track '{name}'. Available: {list(TRACK_REGISTRY.keys())}")
    return TRACK_REGISTRY[name]()