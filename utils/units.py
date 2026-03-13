# utils/units.py

def kmh_to_mps(speed_kmh: float) -> float:
    """Convert km/h to m/s"""
    return speed_kmh / 3.6


def mps_to_kmh(speed_mps: float) -> float:
    """Convert m/s to km/h"""
    return speed_mps * 3.6


def mj_to_j(mj: float) -> float:
    """Convert megajoules to joules"""
    return mj * 1_000_000


def j_to_mj(j: float) -> float:
    """Convert joules to megajoules"""
    return j / 1_000_000
