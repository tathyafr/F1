# experiments/sanity_check.py
"""
Programmatic sanity checks for the ERS simulator.

Answers the key defensibility questions:
  1. Does SOC always stay within FIA-allowed bounds [SOC_MIN, SOC_MAX]?
  2. Does every ERS-ON strategy respect the 4 MJ/lap deployment cap?
  3. Is the baseline (ERS-OFF) always the slowest strategy?
  4. Do different tracks produce meaningfully different ERS benefits?
  5. Does Optimal always beat or match Aggressive?

Run with: python -m experiments.sanity_check
Exit code 0 = all checks pass. Any failure prints the offending row and exits 1.
"""

import sys
import textwrap

from experiments.tracks import TRACK_REGISTRY, build_track
from sim.battery import Battery
from sim.config import BATTERY_CAPACITY_J, ENERGY_PER_LAP_J, SOC_MIN, SOC_MAX, VEHICLE_MASS_KG
from sim.controller import (
    AggressiveController,
    BaselineController,
    ConservativeController,
    LookaheadController,
    OptimalController,
)
from sim.sim_runner import SimulationRunner
from sim.vehicle import Vehicle

INITIAL_SOCS = [0.4, 0.6, 0.8]
TOLERANCE = 1e-6  # float rounding guard


def _make_controllers(vehicle, track, soc):
    bat_opt = Battery(BATTERY_CAPACITY_J, soc=soc)
    opt = OptimalController(vehicle, track, bat_opt)
    return {
        "baseline":     BaselineController(),
        "conservative": ConservativeController(),
        "aggressive":   AggressiveController(energy_budget_j=4e6),
        "lookahead":    LookaheadController(vehicle),
        "optimal":      opt,
    }


def run_all_sims():
    """Return list of result dicts across all tracks × strategies × SOCs."""
    rows = []
    for track_name in TRACK_REGISTRY:
        track = build_track(track_name)
        vehicle = Vehicle(VEHICLE_MASS_KG)
        for soc in INITIAL_SOCS:
            controllers = _make_controllers(vehicle, track, soc)
            for strategy, ctrl in controllers.items():
                battery = Battery(BATTERY_CAPACITY_J, soc=soc)
                sim = SimulationRunner(track, vehicle, battery, ctrl)
                result = sim.run_lap()
                rows.append({
                    "track": track_name,
                    "strategy": strategy,
                    "initial_soc": soc,
                    "lap_time_s": result["lap_time_s"],
                    "improvement_s": result["lap_time_improvement_s"],
                    "soc_end": result["soc_end"],
                    "deployed_j": result["deployed_j"],
                    "soc_history": result["soc_history"],
                })
    return rows


def check_soc_bounds(rows):
    """SOC must stay within [SOC_MIN, SOC_MAX] at every timestep."""
    failures = []
    for r in rows:
        for i, soc in enumerate(r["soc_history"]):
            if soc < SOC_MIN - TOLERANCE or soc > SOC_MAX + TOLERANCE:
                failures.append(
                    f"  {r['track']}/{r['strategy']}/soc0={r['initial_soc']}: "
                    f"timestep {i} SOC={soc:.4f} out of [{SOC_MIN}, {SOC_MAX}]"
                )
    return failures


def check_fia_energy_cap(rows):
    """Every strategy must deploy <= 4 MJ per lap (FIA Article 5.2.3)."""
    failures = []
    for r in rows:
        if r["deployed_j"] > ENERGY_PER_LAP_J + TOLERANCE:
            failures.append(
                f"  {r['track']}/{r['strategy']}/soc0={r['initial_soc']}: "
                f"deployed {r['deployed_j']/1e6:.3f} MJ > {ENERGY_PER_LAP_J/1e6:.1f} MJ cap"
            )
    return failures


def check_baseline_is_slowest(rows):
    """Baseline (ERS-OFF) must produce the highest (worst) lap time for each track/SOC."""
    failures = []
    from collections import defaultdict
    groups = defaultdict(dict)
    for r in rows:
        groups[(r["track"], r["initial_soc"])][r["strategy"]] = r["lap_time_s"]

    for (track, soc), times in groups.items():
        baseline_t = times.get("baseline")
        if baseline_t is None:
            continue
        for strategy, t in times.items():
            if strategy == "baseline":
                continue
            # A strategy that never deploys (e.g. conservative at very low SOC)
            # is allowed to tie baseline; it just cannot be slower.
            if t > baseline_t + TOLERANCE:
                failures.append(
                    f"  {track}/soc0={soc}: {strategy} ({t:.4f}s) > baseline ({baseline_t:.4f}s)"
                )
    return failures


def check_optimal_beats_aggressive(rows):
    """Optimal should always equal or beat Aggressive (it has strictly more freedom)."""
    failures = []
    from collections import defaultdict
    groups = defaultdict(dict)
    for r in rows:
        groups[(r["track"], r["initial_soc"])][r["strategy"]] = r["lap_time_s"]

    for (track, soc), times in groups.items():
        opt = times.get("optimal")
        agg = times.get("aggressive")
        if opt is None or agg is None:
            continue
        if opt > agg + TOLERANCE:
            failures.append(
                f"  {track}/soc0={soc}: optimal ({opt:.4f}s) > aggressive ({agg:.4f}s)"
            )
    return failures


def check_track_differentiation(rows):
    """
    ERS benefit should differ meaningfully across tracks.
    Specifically: Monza (power circuit) benefit >= Monaco (street) benefit
    for the Optimal strategy at SOC=0.6.
    """
    lookup = {(r["track"], r["strategy"], r["initial_soc"]): r["improvement_s"] for r in rows}
    monza_opt = lookup.get(("monza", "optimal", 0.6), None)
    monaco_opt = lookup.get(("monaco", "optimal", 0.6), None)
    if monza_opt is None or monaco_opt is None:
        return ["  Could not find monza/monaco optimal at SOC=0.6"]
    if monza_opt < monaco_opt - TOLERANCE:
        return [
            f"  Expected Monza ERS benefit ({monza_opt:.4f}s) >= Monaco ({monaco_opt:.4f}s)"
        ]
    return []


def main():
    print("Running ERS simulator sanity checks...")
    print(f"  Tracks: {list(TRACK_REGISTRY.keys())}")
    print(f"  SOCs:   {INITIAL_SOCS}")
    print(f"  Strategies: baseline, conservative, aggressive, lookahead, optimal\n")

    rows = run_all_sims()
    print(f"  Simulated {len(rows)} runs\n")

    all_passed = True

    checks = [
        ("SOC bounds [SOC_MIN, SOC_MAX] at every timestep",  check_soc_bounds),
        ("FIA 4 MJ/lap deployment cap (Article 5.2.3)",      check_fia_energy_cap),
        ("Baseline (ERS-OFF) is always slowest",              check_baseline_is_slowest),
        ("Optimal always beats or ties Aggressive",           check_optimal_beats_aggressive),
        ("Monza ERS benefit >= Monaco (power vs street circuit)", check_track_differentiation),
    ]

    for name, fn in checks:
        failures = fn(rows)
        if failures:
            print(f"FAIL: {name}")
            for f in failures:
                print(f)
            all_passed = False
        else:
            print(f"PASS: {name}")

    print()
    if all_passed:
        print("All sanity checks passed.")
        sys.exit(0)
    else:
        print("One or more sanity checks FAILED. See above for details.")
        sys.exit(1)


if __name__ == "__main__":
    main()
