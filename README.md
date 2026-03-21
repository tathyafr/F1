# F1 ERS Deployment Strategy Simulator

> **Research question:** Is the timing of ERS deployment more important than total energy deployed when maximizing lap time benefit under FIA constraints?

**Answer from simulation:** Yes — an offline-optimized strategy extracts **0.40 s** from 4 MJ at Monza while an indiscriminate strategy extracts **0.14 s** from the same energy budget. That is a **2.8× improvement from timing alone**.

---

## What this project is

A physics-based, discrete-time lap simulator for Formula 1 Energy Recovery Systems (ERS). It models the MGU-K motor-generator unit across three circuits, compares five deployment strategies, and enforces FIA regulatory constraints throughout.

**Not a demo.** The simulator is validated against 2023 F1 race pace data (lap time error < 2% on all three circuits), and all results are verifiable via a programmatic sanity check suite.

---

## Key findings

| Finding | Evidence |
|---------|---------|
| Timing > quantity | Optimal (0.40 s) vs. Aggressive (0.14 s) — same 4 MJ, 2.8× better result |
| Conservative paradox | Conservative deploys 3.83 MJ at Monza but gains **0.0 s** — energy wasted in corners |
| Track architecture matters | Monaco (14% straights): 0.21 s max. Monza (53% straights): 0.40 s max |
| Optimal is SOC-invariant | Optimizer achieves 0.40 s regardless of initial SOC (0.4–0.8) via regen replenishment |
| Consistent > degrading | Aggressive holds 81.574 s every lap over a 5-lap stint; Conservative degrades +0.075 s |

---

## Circuits

| Circuit | Segments | Length | Straight % | Baseline | Real pace | Error |
|---------|----------|--------|-----------|----------|-----------|-------|
| Monza | 12 | 5.87 km | 53% | 81.72 s | 80.3 s | 1.8% |
| Spa | 19 | 6.20 km | 43% | 108.60 s | 106.8 s | 1.7% |
| Monaco | 16 | 3.22 km | 14% | 76.64 s | 75.9 s | 1.0% |

---

## Strategies

| Strategy | Logic |
|----------|-------|
| Baseline | ERS-OFF. Ground truth reference. |
| Conservative | Deploy at full power when SOC > 0.6 |
| Aggressive | Fixed 4 MJ budget, deploy immediately at full power |
| Lookahead | Greedy heuristic — deploy if upcoming segment has time benefit |
| Optimal | SLSQP offline optimization: minimizes lap time subject to FIA cap + SOC constraints |

---

## Project structure

```
sim/              Core simulation engine
  config.py       All constants (mass, power limits, SOC bounds, time coefficient)
  controller.py   All 5 strategies
  sim_runner.py   Main loop with FIA cap enforcement
  battery.py      SOC model
  track.py        Segment model
  vehicle.py      Physics (braking energy, time savings)

experiments/
  tracks.py           Monza, Spa, Monaco circuit definitions
  run_experiment.py   45 simulations (5 strategies × 3 tracks × 3 SOCs)
  sensitivity_analysis.py  OAT sweeps + 2D grid
  sanity_check.py     5 programmatic invariant checks

tests/
  test_energy_balance.py   29 unit + integration tests

analysis/
  F1_analysis.ipynb   Publication-quality figures (A–E)
  validation.md       Lap time accuracy and model assumptions

docs/
  report.md           Full research paper (9 sections, all claims cited to data)
  reproducibility.md  Step-by-step guide to reproduce every result
  report_outline.md   Paper skeleton
```

---

## Quickstart

```bash
# 1. Install dependencies
pip install -r requirements.txt

# 2. Run tests
pytest tests/ -v
# Expected: 29 passed

# 3. Verify model invariants
python -m experiments.sanity_check
# Expected: All sanity checks passed.

# 4. Run all experiments (generates results/ CSVs)
python -m experiments.run_experiment

# 5. Regenerate figures
# Open analysis/F1_analysis.ipynb and run all cells
```

---

## Full research paper

See [docs/report.md](docs/report.md) — includes research question, hypotheses, methods, results tables, discussion, conclusions, and limitations.

Reproducibility guide: [docs/reproducibility.md](docs/reproducibility.md)
