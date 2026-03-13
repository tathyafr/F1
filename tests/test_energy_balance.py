# tests/test_energy_balance.py

from sim.battery import Battery


def test_soc_bounds():

    battery = Battery(capacity_j=5_000_000, soc=0.5)

    battery.add_energy(10_000_000)

    assert battery.soc <= 1.0

    battery.deploy_energy(10_000_000)

    assert battery.soc >= 0.1


def test_energy_accounting():

    battery = Battery(capacity_j=5_000_000, soc=0.5)

    initial_energy = battery.get_energy_j()

    battery.add_energy(1_000_000)
    battery.deploy_energy(500_000)

    final_energy = battery.get_energy_j()

    assert final_energy <= battery.capacity_j
