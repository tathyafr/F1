# sim/config.py
"""
Centralized constants and default parameters (SI units).
Edit these values and document any deviations from real-world/regulatory numbers.
"""
from typing import Final

# ---------- vehicle ----------
VEHICLE_MASS_KG: Final[float] = 798.0  # kg (car + driver, example)

# ---------- MGU-K / power limits ----------
MGUK_POWER_LIMIT_W: Final[float] = 120_000.0  # 120 kW (in watts)

# ---------- battery ----------
# Example capacities expressed in joules (1 MJ = 1e6 J)
BATTERY_CAPACITY_J: Final[float] = 5.0e6  # 5 MJ ≈ FIA-ish example
SOC_MIN: Final[float] = 0.10  # minimum allowed state-of-charge (fraction)
SOC_MAX: Final[float] = 1.0   # maximum allowed SOC (fraction)

# ---------- energy assumptions ----------
DEFAULT_REGEN_EFFICIENCY: Final[float] = 0.6  # fraction of kinetic energy recovered
ENERGY_PER_LAP_J: Final[float] = 4.0e6  # placeholder: 4 MJ per lap (example)

# ---------- sim control ----------
DEFAULT_DT: Final[float] = 0.2  # seconds; time-step used inside segments by runner

# ---------- lap time model ----------
# This converts a deployed energy (J) into a first-order speed/time benefit.
# This is a tunable constant used by lookahead controller; see docs for caveats.
ENERGY_TO_TIME_COEFF: Final[float] = 1e-7  # calibrated: ~0.1 s per MJ (0.4 s / 4 MJ typical F1 Monza ERS benefit)
