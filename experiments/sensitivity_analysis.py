# experiments/sensitivity_analysis.py
"""
One-at-a-time (OAT) sensitivity analysis of ERS simulator parameters.

Sweeps three parameters independently (holding others at baseline):
  - regen_efficiency:   0.40 → 0.80
  - battery_capacity_j: 3 MJ → 7 MJ
  - mguk_power_limit_w: 80 kW → 160 kW

Also generates a 2D grid sweep of regen_efficiency × battery_capacity.

Outputs:
  results/sensitivity_oat.csv    — OAT sweep results
  results/sensitivity_2d.csv     — 2D grid results
"""

import os
import sys
import pandas as pd

# Allow running as a script from the repo root
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from experiments.tracks import build_monza
from sim.vehicle import Vehicle
from sim.battery import Battery
from sim.controller import ConservativeController, AggressiveController, LookaheadController
from sim.sim_runner import SimulationRunner
from sim.config import VEHICLE_MASS_KG, BATTERY_CAPACITY_J, DEFAULT_REGEN_EFFICIENCY

os.makedirs("results", exist_ok=True)

# ── Baseline parameters ────────────────────────────────────────────────────────
BASELINE_REGEN = DEFAULT_REGEN_EFFICIENCY   # 0.6
BASELINE_CAPACITY = BATTERY_CAPACITY_J      # 5 MJ
BASELINE_POWER = 120_000                    # 120 kW (FIA limit)
INITIAL_SOC = 0.6

STRATEGIES = {
    "conservative": lambda: ConservativeController(),
    "aggressive":   lambda: AggressiveController(energy_budget_j=4e6),
    "lookahead":    lambda: LookaheadController(Vehicle(VEHICLE_MASS_KG)),
}


def run_single(regen: float, capacity_j: float, strategy_name: str) -> dict:
    track = build_monza()
    vehicle = Vehicle(VEHICLE_MASS_KG)
    battery = Battery(capacity_j, soc=INITIAL_SOC)
    ctrl = STRATEGIES[strategy_name]()
    sim = SimulationRunner(track, vehicle, battery, ctrl, regen_efficiency=regen)
    r = sim.run_lap()
    return {
        "strategy": strategy_name,
        "lap_time_s": r["lap_time_s"],
        "improvement_s": r["lap_time_improvement_s"],
        "deployed_j": r["deployed_j"],
        "harvested_j": r["harvested_j"],
        "soc_end": r["soc_end"],
    }


# ── OAT sweep ─────────────────────────────────────────────────────────────────
print("Running OAT sensitivity sweep...")
rows_oat = []

regen_values    = [0.40, 0.50, 0.60, 0.70, 0.80]
capacity_values = [3e6, 4e6, 5e6, 6e6, 7e6]
power_values    = [80_000, 100_000, 120_000, 140_000, 160_000]

# Sweep regen_efficiency (hold capacity + power at baseline)
for regen in regen_values:
    for strat in STRATEGIES:
        r = run_single(regen, BASELINE_CAPACITY, strat)
        rows_oat.append({
            "sweep_param": "regen_efficiency",
            "param_value": regen,
            **r,
        })

# Sweep battery_capacity (hold regen + power at baseline)
for cap in capacity_values:
    for strat in STRATEGIES:
        r = run_single(BASELINE_REGEN, cap, strat)
        rows_oat.append({
            "sweep_param": "battery_capacity_mj",
            "param_value": cap / 1e6,  # store in MJ for readability
            **r,
        })

# Sweep MGU-K power limit by temporarily patching the config import
# We patch at the controller level via energy budget for aggressive
# and rebuild controllers. For conservative/lookahead, power limit affects decide_power cap.
from sim import config as _cfg
original_power = _cfg.MGUK_POWER_LIMIT_W
for pw in power_values:
    _cfg.MGUK_POWER_LIMIT_W = pw  # patch module-level constant
    track = build_monza()
    for strat_name, ctrl_factory in STRATEGIES.items():
        vehicle = Vehicle(VEHICLE_MASS_KG)
        battery = Battery(BASELINE_CAPACITY, soc=INITIAL_SOC)
        ctrl = ctrl_factory()
        if strat_name == "aggressive":
            ctrl = AggressiveController(energy_budget_j=4e6)
        sim = SimulationRunner(track, vehicle, battery, ctrl, regen_efficiency=BASELINE_REGEN)
        r = sim.run_lap()
        rows_oat.append({
            "sweep_param": "mguk_power_kw",
            "param_value": pw / 1000,
            "strategy": strat_name,
            "lap_time_s": r["lap_time_s"],
            "improvement_s": r["lap_time_improvement_s"],
            "deployed_j": r["deployed_j"],
            "harvested_j": r["harvested_j"],
            "soc_end": r["soc_end"],
        })
_cfg.MGUK_POWER_LIMIT_W = original_power  # restore

df_oat = pd.DataFrame(rows_oat)
df_oat.to_csv("results/sensitivity_oat.csv", index=False)
print(f"  Saved {len(df_oat)} rows → results/sensitivity_oat.csv")

# ── 2D grid: regen × capacity ─────────────────────────────────────────────────
print("Running 2D grid sweep (regen × capacity)...")
rows_2d = []
for regen in regen_values:
    for cap in capacity_values:
        for strat in STRATEGIES:
            r = run_single(regen, cap, strat)
            rows_2d.append({
                "regen_efficiency": regen,
                "battery_capacity_mj": cap / 1e6,
                **r,
            })

df_2d = pd.DataFrame(rows_2d)
df_2d.to_csv("results/sensitivity_2d.csv", index=False)
print(f"  Saved {len(df_2d)} rows → results/sensitivity_2d.csv")

# ── Quick summary printout ─────────────────────────────────────────────────────
print("\n── OAT impact range by parameter ──")
for param in df_oat["sweep_param"].unique():
    sub = df_oat[df_oat["sweep_param"] == param]
    rng = sub.groupby("strategy")["improvement_s"].agg(lambda x: x.max() - x.min())
    print(f"  {param}:")
    for strat, val in rng.items():
        print(f"    {strat}: {val:.4f}s range")

print("\nDone.")
