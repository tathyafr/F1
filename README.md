# F1 ERS Deployment Strategy Simulator

**Question:** In Formula 1, does *when* you deploy hybrid (ERS) energy matter more than *how much* you deploy?

I built a lap simulator to find out. It models the MGU-K (the electric motor that harvests energy under braking and gives it back on acceleration), runs five deployment strategies on three circuits, and enforces the FIA energy limits throughout.

**Short answer:** Yes, timing matters, but how much depends on an assumption I had to test. With the same 4 MJ of energy at Monza, an optimized strategy gains **0.40 s** per lap and a "deploy it all immediately" strategy gains **0.14 s** (2.8×). That gap assumes energy used in corners is worthless. When I relaxed that assumption, the optimized strategy was still the best every time, but its lead shrank to about 1.2× if corners are worth as much as straights.

---

## Key findings

| Finding | Evidence |
|---------|---------|
| Timing beats quantity | Optimal 0.40 s vs. Aggressive 0.14 s at Monza, same 4 MJ |
| …but the size of the effect depends on the corner assumption | Lead shrinks from 2.8× to ~2.1× (corners worth 25%) and ~1.2× (corners worth 100%) |
| Threshold-based control can waste energy | Conservative deploys 3.83 MJ at Monza and gains 0.0 s, because it fires in corners |
| Track layout sets the ceiling | Monaco (14% straights) tops out at 0.21 s; Monza (53%) at 0.40 s |
| Budget-based strategies are more consistent over a stint | Aggressive holds 81.574 s every lap for 5 laps; Conservative slows by 0.075 s |

Full write-up: [docs/report.md](docs/report.md)

---

## Scope: why the 2014–2025 rules?

The model uses the hybrid-era rules that applied from 2014 to 2025: a 120 kW MGU-K and a 4 MJ per-lap deployment limit. The 2026 rules change the power unit a lot (350 kW MGU-K, no MGU-H, roughly double the energy per lap). I stuck with the earlier rules because they were stable for over a decade and have complete data, while the 2026 season was still running. Re-running with 2026 numbers is the next step.

---

## How it works

Each circuit is split into segments (straights, braking zones, corners), each with entry and exit speeds. The simulator steps through every segment in 0.2 s increments:

1. harvests energy in braking zones (60% of the kinetic energy lost),
2. asks the strategy how much power to deploy,
3. clips that to the 120 kW power limit, the 4 MJ per-lap cap and the battery charge,
4. converts deployed energy on straights into time saved (0.1 s per MJ).

| Strategy | What it does |
|----------|-------|
| Baseline | ERS off. The reference point. |
| Conservative | Deploys full power whenever battery charge is above 60% |
| Aggressive | Spends the 4 MJ budget at full power as soon as the lap starts |
| Lookahead | Deploys if the next segment looks worth it (simple heuristic) |
| Optimal | Plans the whole lap in advance with a constrained optimizer (SciPy SLSQP), like a team's pre-race deployment map |

### Circuits

| Circuit | Segments | Length | Straight % | Simulated lap | 2023 reference | Error |
|---------|----------|--------|-----------|----------|-----------|-------|
| Monza | 12 | 5.87 km | 53% | 81.72 s | 80.3 s | 1.8% |
| Spa | 19 | 6.20 km | 43% | 108.60 s | 106.8 s | 1.7% |
| Monaco | 16 | 3.22 km | 14% | 76.64 s | 75.9 s | 1.0% |

Segment speeds were entered by hand, so this match is a calibration check rather than proof that the model is right.

---

## Limitations (the honest part)

- **The 0.40 s ceiling is an input, not a discovery.** 4 MJ × 0.1 s/MJ = 0.40 s. What the optimizer *finds* is how to get all 4 MJ onto straights.
- **Corners are assumed worthless in the main model.** This is the assumption that matters most, so `experiments/corner_benefit_sensitivity.py` tests it directly.
- **Linear time model.** Real ERS gains depend on speed and drag. `sim/vehicle.py` has a drag-based model that could replace it.
- No tyre wear, fuel burn, traffic or DRS, and no separate MGU-K harvest limit.

---

## Project structure

```
sim/              Simulation engine
  config.py       Constants (mass, power limit, battery, time coefficient)
  controller.py   The 5 strategies
  sim_runner.py   Main loop with FIA cap enforcement
  battery.py      State-of-charge model
  track.py        Segment model
  vehicle.py      Braking energy and drag-based physics

experiments/
  tracks.py                       Monza, Spa, Monaco definitions
  run_experiment.py               45 runs (5 strategies × 3 tracks × 3 starting charges)
  sensitivity_analysis.py         Parameter sweeps (regen, battery size, power)
  corner_benefit_sensitivity.py   Tests the "corners are worthless" assumption
  sanity_check.py                 5 automated invariant checks

tests/
  test_energy_balance.py   35 unit + integration tests

analysis/
  F1_analysis.ipynb   Figures A–F
  validation.md       Calibration and assumptions

docs/
  report.md           Full write-up
  reproducibility.md  How to reproduce every result
```

---

## Run it

```bash
pip install -r requirements.txt
pytest tests/ -v                                   # 35 passed
python -m experiments.sanity_check                 # All sanity checks passed.
python -m experiments.run_experiment               # main results -> results/
python -m experiments.corner_benefit_sensitivity   # assumption stress test
# Figures: open analysis/F1_analysis.ipynb and run all cells
```
