import pytest
from sim.battery import Battery
from sim.track import Segment, Track
from sim.vehicle import Vehicle
from sim.controller import ConservativeController, AggressiveController, LookaheadController
from sim.sim_runner import SimulationRunner
from sim.config import BATTERY_CAPACITY_J, VEHICLE_MASS_KG
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
    saved = v.estimate_time_saved_by_energy(500_000, 50.0, 500.0)
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