import pytest
from sim.battery import Battery
from sim.track import Segment, Track
from sim.vehicle import Vehicle
from sim.controller import (
    BaselineController,
    ConservativeController,
    AggressiveController,
    LookaheadController,
    OptimalController,
)
from sim.sim_runner import SimulationRunner
from sim.config import BATTERY_CAPACITY_J, ENERGY_PER_LAP_J, VEHICLE_MASS_KG
from utils.units import kmh_to_mps


# ── Battery ──────────────────────────────────────────────────────────────────

def test_soc_bounds_add():
    b = Battery(5_000_000, soc=0.5)
    b.add_energy(10_000_000)
    assert b.soc <= 1.0

def test_soc_bounds_deploy():
    b = Battery(5_000_000, soc=0.5)
    b.deploy_energy(10_000_000)
    assert b.soc >= 0.1

def test_wasted_energy_tracked():
    b = Battery(5_000_000, soc=0.95)
    b.add_energy(1_000_000)
    assert b.total_wasted > 0

def test_energy_accounting():
    b = Battery(5_000_000, soc=0.5)
    b.add_energy(1_000_000)
    b.deploy_energy(500_000)
    assert b.get_energy_j() <= b.capacity_j

def test_reset_history():
    b = Battery(5_000_000, soc=0.5)
    b.add_energy(100_000)
    b.reset_history()
    assert b.soc_history == []
    assert b.harvested_history == []


# ── Vehicle ──────────────────────────────────────────────────────────────────

def test_braking_energy_positive():
    v = Vehicle(798.0)
    e = v.braking_energy_j(kmh_to_mps(300), kmh_to_mps(100))
    assert e > 0

def test_braking_energy_zero_when_accelerating():
    v = Vehicle(798.0)
    assert v.braking_energy_j(kmh_to_mps(100), kmh_to_mps(200)) == 0.0

def test_time_saved_positive():
    v = Vehicle(798.0)
    # Use 2 MJ at 50 m/s over 500 m; drag consumes ~536 kJ so net energy is positive
    saved = v.estimate_time_saved_by_energy(2_000_000, 50.0, 500.0)
    assert saved > 0

def test_time_saved_zero_no_energy():
    v = Vehicle(798.0)
    assert v.estimate_time_saved_by_energy(0, 50.0, 500.0) == 0.0


# ── Controllers ──────────────────────────────────────────────────────────────

def test_conservative_deploys_above_threshold():
    c = ConservativeController(soc_threshold=0.5)
    power = c.decide_power({"soc": 0.7}, dt=0.2)
    assert power > 0

def test_conservative_no_deploy_below_threshold():
    c = ConservativeController(soc_threshold=0.5)
    assert c.decide_power({"soc": 0.3}, dt=0.2) == 0.0

def test_aggressive_depletes_budget():
    c = AggressiveController(energy_budget_j=1000)
    c.start_lap()
    total = 0
    for _ in range(1000):
        total += c.decide_power({"soc": 0.8}, dt=0.2) * 0.2
    assert abs(total - 1000) < 1e-6

def test_aggressive_resets_on_start_lap():
    c = AggressiveController(energy_budget_j=10_000)
    c.start_lap()
    c.decide_power({"soc": 0.8}, dt=0.2)
    c.start_lap()
    assert c._remaining == 10_000

def test_lookahead_no_upcoming_returns_zero():
    v = Vehicle(798.0)
    c = LookaheadController(v)
    assert c.decide_power({"soc": 0.8, "v": 50}, dt=0.2, upcoming=[]) == 0.0


# ── SimulationRunner ─────────────────────────────────────────────────────────

@pytest.fixture
def simple_track():
    return Track([
        Segment("S1", "straight", 500, kmh_to_mps(200), kmh_to_mps(200)),
        Segment("B1", "brake",    150, kmh_to_mps(200), kmh_to_mps(80)),
        Segment("C1", "corner",   100, kmh_to_mps(80),  kmh_to_mps(100)),
    ])

def test_run_lap_returns_keys(simple_track):
    sim = SimulationRunner(simple_track, Vehicle(VEHICLE_MASS_KG),
                           Battery(BATTERY_CAPACITY_J, soc=0.6),
                           ConservativeController())
    r = sim.run_lap()
    for key in ["lap_time_s", "soc_end", "harvested_j", "deployed_j",
                "wasted_j", "soc_history", "power_history"]:
        assert key in r

def test_lap_time_positive(simple_track):
    sim = SimulationRunner(simple_track, Vehicle(VEHICLE_MASS_KG),
                           Battery(BATTERY_CAPACITY_J, soc=0.6),
                           ConservativeController())
    assert sim.run_lap()["lap_time_s"] > 0

def test_soc_end_in_bounds(simple_track):
    sim = SimulationRunner(simple_track, Vehicle(VEHICLE_MASS_KG),
                           Battery(BATTERY_CAPACITY_J, soc=0.6),
                           ConservativeController())
    r = sim.run_lap()
    assert 0.1 <= r["soc_end"] <= 1.0

def test_multi_lap(simple_track):
    sim = SimulationRunner(simple_track, Vehicle(VEHICLE_MASS_KG),
                           Battery(BATTERY_CAPACITY_J, soc=0.8),
                           ConservativeController())
    laps = sim.run_laps(3)
    assert len(laps) == 3
    assert all("lap_number" in r for r in laps)

def test_regen_harvests_energy(simple_track):
    sim = SimulationRunner(simple_track, Vehicle(VEHICLE_MASS_KG),
                           Battery(BATTERY_CAPACITY_J, soc=0.2),
                           ConservativeController())
    r = sim.run_lap()
    assert r["harvested_j"] > 0


# ── Lap Time Integration ──────────────────────────────────────────────────────

def test_lap_time_improvement_key_present(simple_track):
    sim = SimulationRunner(simple_track, Vehicle(VEHICLE_MASS_KG),
                           Battery(BATTERY_CAPACITY_J, soc=0.6),
                           AggressiveController(energy_budget_j=4e6))
    r = sim.run_lap()
    assert "lap_time_improvement_s" in r

def test_strategies_produce_different_lap_times():
    from experiments.tracks import build_monza
    track = build_monza()
    # Conservative with threshold=0.99 effectively deploys nothing (SOC never reaches 0.99 on a lap);
    # aggressive deploys 2 MJ unconditionally — aggressive must produce a faster lap
    conservative = SimulationRunner(
        track, Vehicle(VEHICLE_MASS_KG),
        Battery(BATTERY_CAPACITY_J, soc=0.6),
        ConservativeController(soc_threshold=0.99),
    )
    aggressive = SimulationRunner(
        track, Vehicle(VEHICLE_MASS_KG),
        Battery(BATTERY_CAPACITY_J, soc=0.6),
        AggressiveController(energy_budget_j=2e6),
    )
    t_cons = conservative.run_lap()["lap_time_s"]
    t_agg = aggressive.run_lap()["lap_time_s"]
    assert t_agg < t_cons, "Aggressive deploys 2 MJ while conservative deploys nothing — must be faster"

def test_more_energy_means_faster_lap():
    from experiments.tracks import build_monza
    track = build_monza()
    low_bat = SimulationRunner(
        track, Vehicle(VEHICLE_MASS_KG),
        Battery(BATTERY_CAPACITY_J, soc=0.2),
        AggressiveController(energy_budget_j=4e6),
    )
    high_bat = SimulationRunner(
        track, Vehicle(VEHICLE_MASS_KG),
        Battery(BATTERY_CAPACITY_J, soc=0.9),
        AggressiveController(energy_budget_j=4e6),
    )
    t_low = low_bat.run_lap()["lap_time_s"]
    t_high = high_bat.run_lap()["lap_time_s"]
    assert t_high <= t_low, "Higher SOC gives more deployable energy, so equal or faster lap"


# ── BaselineController ────────────────────────────────────────────────────────

def test_baseline_deploys_nothing(simple_track):
    sim = SimulationRunner(simple_track, Vehicle(VEHICLE_MASS_KG),
                           Battery(BATTERY_CAPACITY_J, soc=0.8),
                           BaselineController())
    r = sim.run_lap()
    assert r["deployed_j"] == 0.0, "Baseline must never deploy energy"

def test_baseline_improvement_is_zero(simple_track):
    sim = SimulationRunner(simple_track, Vehicle(VEHICLE_MASS_KG),
                           Battery(BATTERY_CAPACITY_J, soc=0.8),
                           BaselineController())
    r = sim.run_lap()
    assert r["lap_time_improvement_s"] == pytest.approx(0.0, abs=1e-9)

def test_baseline_is_slowest_on_monza():
    from experiments.tracks import build_monza
    track = build_monza()
    vehicle = Vehicle(VEHICLE_MASS_KG)
    baseline = SimulationRunner(track, vehicle,
                                Battery(BATTERY_CAPACITY_J, soc=0.6),
                                BaselineController())
    optimal = SimulationRunner(track, vehicle,
                               Battery(BATTERY_CAPACITY_J, soc=0.6),
                               OptimalController(vehicle, track,
                                                 Battery(BATTERY_CAPACITY_J, soc=0.6)))
    t_base = baseline.run_lap()["lap_time_s"]
    t_opt  = optimal.run_lap()["lap_time_s"]
    assert t_opt < t_base, "Optimal must be faster than ERS-OFF baseline"


# ── OptimalController ─────────────────────────────────────────────────────────

def test_optimal_runs_and_returns_keys():
    from experiments.tracks import build_monza
    track = build_monza()
    vehicle = Vehicle(VEHICLE_MASS_KG)
    battery = Battery(BATTERY_CAPACITY_J, soc=0.6)
    ctrl = OptimalController(vehicle, track, battery)
    sim = SimulationRunner(track, vehicle, Battery(BATTERY_CAPACITY_J, soc=0.6), ctrl)
    r = sim.run_lap()
    for key in ["lap_time_s", "lap_time_improvement_s", "deployed_j", "soc_end"]:
        assert key in r

def test_optimal_respects_fia_cap():
    """Optimal must not deploy more than the FIA 4 MJ/lap cap."""
    from experiments.tracks import build_monza
    track = build_monza()
    vehicle = Vehicle(VEHICLE_MASS_KG)
    battery = Battery(BATTERY_CAPACITY_J, soc=0.8)
    ctrl = OptimalController(vehicle, track, battery)
    sim = SimulationRunner(track, vehicle, Battery(BATTERY_CAPACITY_J, soc=0.8), ctrl)
    r = sim.run_lap()
    assert r["deployed_j"] <= ENERGY_PER_LAP_J + 1e3, (
        f"Optimal deployed {r['deployed_j']/1e6:.3f} MJ, exceeds FIA cap of {ENERGY_PER_LAP_J/1e6:.1f} MJ"
    )

def test_optimal_beats_aggressive_on_monza():
    """Optimal (unconstrained timing) should match or beat fixed-budget Aggressive."""
    from experiments.tracks import build_monza
    track = build_monza()
    vehicle = Vehicle(VEHICLE_MASS_KG)
    battery = Battery(BATTERY_CAPACITY_J, soc=0.6)
    opt_ctrl = OptimalController(vehicle, track, battery)
    agg_ctrl = AggressiveController(energy_budget_j=4e6)
    t_opt = SimulationRunner(track, vehicle, Battery(BATTERY_CAPACITY_J, soc=0.6), opt_ctrl).run_lap()["lap_time_s"]
    t_agg = SimulationRunner(track, vehicle, Battery(BATTERY_CAPACITY_J, soc=0.6), agg_ctrl).run_lap()["lap_time_s"]
    assert t_opt <= t_agg + 1e-6, f"Optimal ({t_opt:.4f}s) should not be slower than Aggressive ({t_agg:.4f}s)"

def test_optimal_soc_stays_in_bounds():
    from experiments.tracks import build_monza
    from sim.config import SOC_MIN, SOC_MAX
    track = build_monza()
    vehicle = Vehicle(VEHICLE_MASS_KG)
    battery = Battery(BATTERY_CAPACITY_J, soc=0.6)
    ctrl = OptimalController(vehicle, track, battery)
    sim = SimulationRunner(track, vehicle, Battery(BATTERY_CAPACITY_J, soc=0.6), ctrl)
    r = sim.run_lap()
    assert SOC_MIN <= r["soc_end"] <= SOC_MAX