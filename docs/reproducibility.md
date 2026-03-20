# Reproducibility Guide

This document describes how to reproduce every result, figure, and claim in this project from scratch.

---

## Environment setup

```bash
# Python 3.9+ required
pip install -r requirements.txt
```

**Dependencies** (see `requirements.txt`):

| Package | Purpose |
|---------|---------|
| `numpy` | Array operations in OptimalController |
| `scipy` | SLSQP optimizer (`scipy.optimize.minimize`) |
| `pandas` | CSV output in experiment scripts |
| `matplotlib` | All figures |
| `jupyter` | Notebook analysis |
| `pytest` | Test suite |

---

## Step 1 — Run unit + integration tests

```bash
pytest tests/ -v
```

Expected: **29 tests pass** in < 5 seconds.

Key invariants verified by the test suite:
- SOC never leaves `[SOC_MIN, SOC_MAX]` during any simulation
- Baseline (ERS-OFF) always produces zero improvement
- Optimal never violates the FIA 4 MJ/lap cap
- Optimal is always equal or faster than Aggressive

---

## Step 2 — Run the sanity check

```bash
python -m experiments.sanity_check
```

This programmatically verifies across all 3 tracks × 5 strategies × 3 SOC levels (45 runs):
1. SOC bounds hold at every timestep
2. FIA 4 MJ/lap cap is not exceeded
3. Baseline is always the slowest strategy
4. Optimal always beats or ties Aggressive
5. Monza ERS benefit ≥ Monaco (power circuit vs. street circuit)

Expected output: `All sanity checks passed.` and exit code 0.

---

## Step 3 — Regenerate all experiment CSVs

```bash
python -m experiments.run_experiment
```

Outputs to `results/`:

| File | Contents |
|------|---------|
| `strategy_results.csv` | 45 rows: 5 strategies × 3 tracks × 3 SOCs |
| `stint_results.csv` | 20 rows: 4 strategies × 5 laps (Monza, SOC=0.8) |
| `telemetry_{strategy}_soc{N}.csv` | Per-step telemetry for Monza strategies |

Runtime: ~2–4 minutes (OptimalController runs SLSQP once per track/SOC).

---

## Step 4 — Run sensitivity analysis

```bash
python -m experiments.sensitivity_analysis
```

Outputs:
- `results/sensitivity_oat.csv` — one-at-a-time sweeps (regen efficiency, battery capacity, MGU-K power)
- `results/sensitivity_2d.csv` — 2D grid (regen × capacity)

---

## Step 5 — Regenerate all figures

Open and run `analysis/F1_analysis.ipynb` from top to bottom.

Each cell is self-contained. The notebook:
1. Calls `run_experiment.run()` to regenerate CSVs (Steps 3)
2. Produces 5 publication-quality figures saved to `results/`:

| Figure | File | Description |
|--------|------|-------------|
| A | `fig_a_improvement_by_track.png` | ERS improvement by strategy × circuit at SOC=0.6 |
| B | `fig_b_energy_vs_improvement.png` | Energy deployed vs. lap time improvement (scatter) |
| C | `fig_c_tornado.png` | OAT sensitivity tornado chart |
| D | `fig_d_pareto.png` | Pareto frontier: improvement vs. SOC remaining |
| E | `fig_e_stint.png` | 5-lap stint: SOC depletion + lap time degradation |

---

## Model parameters

All constants are defined in `sim/config.py`. Changing any value here propagates to all simulations automatically.

| Parameter | Value | Source |
|-----------|-------|--------|
| Vehicle mass | 798 kg | FIA minimum (car + driver) |
| MGU-K power limit | 120 kW | FIA Technical Regulations Art. 5.2.3 |
| Battery capacity | 5 MJ | Representative F1 ERS store |
| SOC minimum | 0.10 | Conservative buffer above depleted |
| SOC maximum | 1.00 | Full charge |
| Regen efficiency | 0.60 | Literature range 55–65% |
| Energy-to-time coefficient | 1e-7 s/J | Calibrated: 0.4s / 4MJ at Monza (published data) |
| FIA deployment cap | 4 MJ/lap | FIA Technical Regulations Art. 5.2.3 |
| Timestep | 0.2 s | Convergence tested at 0.1 s (< 0.01% difference) |

---

## Track baselines vs. real lap times

| Track | Simulated baseline | Real race pace | Error |
|-------|--------------------|----------------|-------|
| Monza | 81.72 s | 80.3 s (2023) | 1.8% |
| Spa | 108.60 s | 106.8 s (2023) | 1.7% |
| Monaco | 76.64 s | 75.9 s (2023) | 1.0% |

Errors arise from the trapezoidal velocity profile approximation (no traction circle, no fuel mass reduction, no tire degradation). All errors are within ±2% and are conservative (model slightly slower than reality).

---

## Known limitations

- **Linear ERS time model**: assumes every joule deployed on a straight saves exactly 1e-7 s. In reality, diminishing returns apply at high deployment rates.
- **Corner deployment**: corners receive zero time benefit from ERS (grip-limited). This is physically correct for slow corners but slightly pessimistic for medium-speed arcs where power is partially beneficial.
- **Single lap**: no tire degradation, fuel mass, or traffic modeled. Stint results show the battery effect only.
- **LookaheadController**: the greedy heuristic uses a simplified time-benefit estimate (`vehicle.estimate_time_saved_by_energy`), not the calibrated linear model. Results are directionally correct but not optimal.
