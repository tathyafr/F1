# ERS Deployment Strategy in Formula 1: Does Timing Matter More Than Total Energy?

**Author:** [Your Name]
**Date:** 2026
**Repository:** github.com/[username]/F1

---

## Research Question

> **Is the timing of ERS deployment more important than the total energy deployed when maximizing lap time benefit under FIA constraints?**

---

## Hypotheses

1. **H1 (Timing hypothesis):** An optimal deployment schedule will produce a greater lap time improvement than a strategy deploying the same total energy indiscriminately, even when both are capped at the FIA 4 MJ limit.

2. **H2 (Conservative paradox):** A threshold-based conservative strategy will deploy significant energy but yield near-zero lap time improvement, because energy deployed in corners provides no time benefit.

3. **H3 (Track dependence):** ERS deployment benefit will be greater on high-speed power circuits (Monza, Spa) than on tight street circuits (Monaco), due to differences in the proportion of lap distance spent on straights.

---

## Abstract

Formula 1's Energy Recovery System (ERS) allows teams to harvest kinetic energy under braking and redeploy it via the MGU-K motor-generator unit, subject to a 4 MJ per lap FIA regulatory cap. This paper investigates whether the *timing* of deployment is more important than the *total energy* deployed, using a discrete-time lap simulation across three circuits (Monza, Spa-Francorchamps, Monaco) and five deployment strategies (ERS-OFF baseline, Conservative, Aggressive, Lookahead, and Optimal). The simulator enforces FIA energy constraints at the hardware level and is validated against published 2023 race pace data (lap time error < 2% for all three circuits). Results show that an offline-optimized strategy (SLSQP) consistently achieves 0.40 s improvement at Monza by concentrating all 4 MJ on three straights, while a conservative threshold-based strategy deploys 3.83 MJ with zero improvement by directing energy exclusively to corners. This confirms H1 and H2: deployment timing dominates total energy as a determinant of lap time benefit. Track architecture moderates the effect (Monaco: 0.21 s vs. Monza: 0.40 s), confirming H3.

---

## 1. Introduction

### 1.1 Background

Formula 1 cars have used hybrid energy recovery systems since 2014. The Motor Generator Unit – Kinetic (MGU-K) recovers energy under braking and can deploy up to 120 kW during acceleration phases. The FIA Technical Regulations impose a hard cap: no more than 4 MJ of MGU-K energy may be deployed per lap (Article 5.2.3). Teams operate within this constraint and must decide *when* during a lap to deploy their available energy.

In practice, teams compute offline-optimized deployment maps before each race, accounting for circuit geometry, battery state, and tire behavior. These maps are uploaded to the car's ERS control unit and executed deterministically during the race. The core engineering question — whether concentrating energy on straights outperforms uniform distribution — has received limited treatment in accessible literature.

### 1.2 Motivation

This project asks a sharper version of that question: given the same 4 MJ budget, does a strategy that deploys energy only on straights outperform one that deploys it indiscriminately? The answer has practical implications for how ERS algorithms are designed and evaluated.

### 1.3 Scope

This study uses a physics-informed, segment-based discrete-time simulation. The model captures energy harvesting, battery state-of-charge dynamics, and FIA regulatory constraints. It does not model tire degradation, fuel mass reduction, or car-following effects. Results are therefore valid for strategy *comparison* on a single lap, not for absolute race simulation.

---

## 2. Methods

### 2.1 Simulation Architecture

The simulator discretizes each circuit into segments (straights, braking zones, corners). Each segment is modeled with an entry speed, exit speed, and length. Within each segment, a fixed timestep (Δt = 0.2 s) loop:

1. Applies braking energy recovery if entry speed > exit speed
2. Queries the deployment controller for a power request
3. Enforces the FIA 4 MJ/lap cap as a hard hardware limit
4. Updates battery state-of-charge (SOC)
5. Accumulates segment-level deployed energy

After each segment, lap time savings are computed using a calibrated linear model applied to straights only (see Section 2.4).

### 2.2 Model Parameters

All parameters are defined in `sim/config.py`. Every modeling choice is documented with its source.

| Parameter | Value | Justification |
|-----------|-------|---------------|
| Vehicle mass | 798 kg | FIA minimum (car + driver, 2023 regulations) |
| MGU-K power limit | 120 kW | FIA Technical Regulations Art. 5.2.3 |
| Battery capacity | 5 MJ | Representative of FIA-compliant ERS store |
| SOC minimum | 0.10 | Conservative operational floor (10% reserve) |
| SOC maximum | 1.00 | Full charge |
| Regen efficiency | 0.60 | Mid-range of published literature (55–65%) |
| Energy-to-time coefficient | 1×10⁻⁷ s/J | Calibrated to real F1 data: ~0.4 s per 4 MJ at Monza |
| FIA deployment cap | 4 MJ/lap | FIA Technical Regulations Art. 5.2.3 |
| Simulation timestep | 0.2 s | Convergence tested: Δt = 0.1 s changes results by < 0.01% |

### 2.3 Track Models

Three circuits were modelled with distinct architectural characteristics:

| Circuit | Segments | Length | Straights | Baseline | Real pace | Error |
|---------|----------|--------|-----------|----------|-----------|-------|
| Monza | 12 | 5.87 km | 3 (53% of lap) | 81.72 s | 80.3 s | 1.8% |
| Spa-Francorchamps | 19 | 6.20 km | 4 (43% of lap) | 108.60 s | 106.8 s | 1.7% |
| Monaco | 16 | 3.22 km | 2 (14% of lap) | 76.64 s | 75.9 s | 1.0% |

Straight percentage was computed as (total straight length) / (total track length). Monza has the highest straight fraction; Monaco the lowest. This architectural difference is the primary driver of H3.

Baseline lap times were validated against 2023 F1 season race pace data. All errors are within ±2% and are conservative (simulated car slightly slower than real pace due to simplified velocity profiles).

### 2.4 Lap Time Model

ERS deployment reduces lap time only on straights. The justification: corners are lateral-grip-limited — additional longitudinal power does not improve corner exit speed because traction is saturated. On straights, the car is power-limited at high speed, so additional MGU-K power directly increases velocity.

The time saving on a straight is modelled as:

```
Δt = E_deployed × k
```

where `k = 1×10⁻⁷ s/J` (0.1 s per MJ). This coefficient was calibrated against published F1 data: at Monza, full ERS deployment (~4 MJ) yields approximately 0.4 s per lap. The linear model is validated to within the precision of available reference data.

A physical minimum segment time is enforced (segment length / 100 m/s ≈ 360 km/h) to prevent unphysical results at extreme energy inputs.

### 2.5 Battery Model

Battery SOC is tracked continuously. Energy recovery (regen) is applied at the start of each braking segment:

```
E_recovered = η_regen × 0.5 × m × (v_entry² − v_exit²)
```

Energy above SOC_MAX is discarded (wasted). Energy below SOC_MIN cannot be deployed. The FIA 4 MJ/lap deployment cap is enforced as a running total reset at the start of each lap — identical to the physical ERS control unit behavior.

### 2.6 Deployment Controllers

Five strategies were tested, representing a spectrum from no deployment to offline-optimized:

| Strategy | Logic | Key parameter |
|----------|-------|---------------|
| Baseline | Deploy 0 W at all times | — |
| Conservative | Deploy at full power when SOC > threshold | SOC threshold = 0.6 |
| Aggressive | Deploy at full power until 4 MJ budget exhausted | Budget = 4 MJ |
| Lookahead | Deploy if estimated time benefit of upcoming segment > threshold | Greedy heuristic |
| Optimal | SLSQP offline optimization: minimize lap time subject to SOC and FIA constraints | Scipy minimize, maxiter=300 |

The Optimal controller solves a constrained nonlinear program before the lap begins and executes the resulting deployment schedule deterministically — directly analogous to real-world pre-race ERS mapping.

### 2.7 Experimental Design

**Controlled variables:** circuit, vehicle mass, battery capacity, regen efficiency, FIA cap, timestep.
**Independent variable:** deployment strategy (5 levels).
**Dependent variable:** lap time improvement relative to ERS-OFF baseline (seconds).

All 45 combinations (5 strategies × 3 circuits × 3 initial SOC values: 0.4, 0.6, 0.8) were simulated. Initial SOC was varied to test strategy robustness to battery state at lap start.

---

## 3. Results

### 3.1 Primary Result: Strategy Comparison at SOC = 0.6

The table below shows the key finding. All values are lap time improvement over the ERS-OFF baseline.

| Strategy | Monza | Spa | Monaco | Deployed (Monza) |
|----------|-------|-----|--------|------------------|
| Baseline | 0.000 s | 0.000 s | 0.000 s | 0.00 MJ |
| Conservative | **0.000 s** | 0.000 s | 0.000 s | **3.83 MJ** |
| Aggressive | 0.144 s | 0.177 s | 0.119 s | 4.00 MJ |
| Lookahead | 0.083 s | 0.072 s | 0.081 s | 4.00 MJ |
| Optimal | **0.400 s** | **0.400 s** | **0.210 s** | **4.00 MJ** |

**Key observation (H1 confirmed):** Optimal and Aggressive both deploy 4 MJ at Monza. Optimal achieves 0.400 s improvement; Aggressive achieves 0.144 s — the same energy budget yields **2.8× greater benefit** purely from better timing.

**Key observation (H2 confirmed):** Conservative deploys 3.83 MJ at Monza (SOC=0.6) but achieves **zero lap time improvement**. The energy is deployed in corners (where SOC rises after braking zones and the threshold is triggered), providing no time benefit. This is the Conservative paradox.

### 3.2 Effect of Initial SOC

| Strategy | Monza SOC=0.4 | Monza SOC=0.6 | Monza SOC=0.8 |
|----------|---------------|---------------|---------------|
| Baseline | 0.000 s | 0.000 s | 0.000 s |
| Conservative | 0.000 s | 0.000 s | 0.101 s |
| Aggressive | 0.144 s | 0.144 s | 0.144 s |
| Lookahead | 0.083 s | 0.083 s | 0.083 s |
| Optimal | 0.400 s | 0.400 s | 0.400 s |

**Notable:** Optimal is **invariant to initial SOC** across all three values. This occurs because the SLSQP optimizer concentrates all 4 MJ on the three Monza straights regardless of starting SOC — regen replenishes enough energy between braking zones to always reach the 4 MJ deployment cap. Aggressive and Lookahead are similarly invariant at high SOC because regen ensures the battery stays filled. Conservative shows SOC-dependence because the threshold trigger fires more frequently at higher starting SOC.

### 3.3 Track Architecture Effect (H3)

| Track | Straight % | Optimal improvement | Aggressive improvement |
|-------|-----------|---------------------|----------------------|
| Monza | 53% | 0.400 s | 0.144 s |
| Spa | 43% | 0.400 s | 0.177 s |
| Monaco | 14% | 0.210 s | 0.119 s |

H3 is **partially confirmed**: Monaco yields lower ERS benefit for Optimal (0.210 s vs. 0.400 s at Monza) due to fewer and shorter straights. However, the Optimal improvement is identical at Monza and Spa despite Spa having 10% fewer straight distance — Spa's longer individual straights (Kemmel Straight: 750 m, Blanchimont: 600 m) allow full 4 MJ deployment even without Monza's straight dominance. The result suggests that the number of high-speed straight *segments* matters less than the total deployable energy achievable on straights in a single lap.

### 3.4 Multi-Lap Stint Analysis (Monza, SOC = 0.8, 5 laps)

| Lap | Baseline | Conservative | Aggressive | Lookahead |
|-----|----------|--------------|------------|-----------|
| 1 | 81.718 s | 81.617 s | 81.574 s | 81.635 s |
| 2 | 81.718 s | 81.637 s | 81.574 s | 81.635 s |
| 3 | 81.718 s | 81.653 s | 81.574 s | 81.635 s |
| 4 | 81.718 s | 81.673 s | 81.574 s | 81.635 s |
| 5 | 81.718 s | 81.692 s | 81.574 s | 81.635 s |

**Conservative degrades across the stint** (81.617 → 81.692 s, +0.075 s over 5 laps) as battery depletes and the SOC threshold fires less often. **Aggressive is perfectly consistent** (81.574 s every lap) because the 4 MJ budget is always available from regen replenishment. **Lookahead is also consistent** but at a worse absolute time. This demonstrates that budget-based strategies are more predictable over a stint than threshold-based ones.

---

## 4. Discussion

### 4.1 Timing is the Primary Lever

The central finding is unambiguous: deployment timing dominates total energy deployed as a determinant of lap time improvement. The Conservative controller deploys 3.83 MJ at Monza (96% of the maximum 4 MJ budget) and gains zero seconds. The Optimal controller deploys 4.00 MJ and gains 0.40 s. The difference is entirely attributable to *where* in the lap energy is applied.

This result is physically grounded. ERS time savings arise only on straights, where the car is power-limited. Corners are grip-limited: additional longitudinal power cannot overcome the lateral traction constraint, so energy deployed in corners is wasted from a lap time perspective. A strategy that does not explicitly reason about segment type will therefore underperform regardless of its total energy deployment.

### 4.2 The Conservative Paradox

The Conservative controller's behavior at SOC=0.6 on Monza appears counterintuitive: it deploys more energy than the Lookahead controller (3.83 MJ vs. 4.00 MJ) but achieves zero improvement versus Lookahead's 0.083 s gain. The explanation is the SOC threshold mechanism. At SOC=0.6, the battery fills up during braking zones (regen pushes SOC above the 0.6 threshold), triggering deployment in the *subsequent corner segment* — exactly where time savings are zero. The controller deploys energy energetically but ineffectively.

This is not a bug in the simulation; it represents a real failure mode in simplistic ERS control logic. A production ERS controller that triggers purely on SOC without segment-type awareness would exhibit this behavior.

### 4.3 Optimal vs. Aggressive: Same Budget, 2.8× Better Result

At Monza (SOC=0.6), Optimal and Aggressive both deploy exactly 4 MJ. Optimal achieves 0.400 s; Aggressive 0.144 s. This 2.8× difference is the clearest quantification of the timing effect in this study. The Aggressive controller distributes energy throughout the lap (deploys immediately at full power until the budget is exhausted), hitting both straights and corners. The Optimal controller concentrates all 4 MJ on the three Monza straights — Main Straight (900 m), Serraglio (800 m), and Back Straight (900 m).

This result validates the real-world practice of pre-race ERS map optimization. Teams that invest in offline optimization can extract up to 2.8× more lap time benefit from the same regulatory energy budget as teams using simpler deployment heuristics.

### 4.4 Optimal's SOC Independence

A notable property of the Optimal solution is its invariance to initial SOC across the tested range (0.4–0.8). This arises because Monza's braking zones generate sufficient regen energy to refill the battery between straight deployments regardless of starting SOC. The optimizer discovers this and always commits to full deployment on all three straights. In a real race, this implies that the pre-optimized ERS map remains valid even if the car enters a lap with slightly different battery state than planned — a practically important robustness property.

### 4.5 Track Architecture as a Moderating Variable

Monaco's lower ERS benefit (0.210 s optimal vs. 0.400 s at Monza) is consistent with its circuit architecture: only 14% of the lap is spent on straights versus 53% at Monza. This suggests that the absolute ERS benefit ceiling is determined more by circuit geometry than by strategy sophistication. On Monaco, even a perfect optimizer cannot extract more than ~0.21 s because the deployable straight distance is fundamentally limited. Strategy selection is therefore more impactful at power circuits (Monza, Spa) than at street circuits (Monaco).

### 4.6 Regulatory Cap Sensitivity: When Do the Rules Stop Mattering?

Sweeping the FIA deployment cap from 2 MJ to 8 MJ for the Optimal controller reveals a consistent pattern across all three circuits (Figure F):

| Cap (MJ) | Monza improvement (s) | Spa improvement (s) | Monaco improvement (s) |
|----------|----------------------|---------------------|------------------------|
| 2        | 0.200                | 0.200               | 0.200                  |
| 4        | 0.400                | 0.400               | 0.210                  |
| 6        | 0.413                | 0.422               | 0.210                  |
| 8        | 0.413                | 0.422               | 0.210                  |

Three findings emerge. First, below 4 MJ the relationship is linear: each additional megajoule yields exactly 0.1 s improvement (for straights-only deployment), meaning the cap is the binding constraint. Above 4 MJ, returns diminish sharply — doubling the cap from 4 to 8 MJ yields only 0.013 s additional improvement at Monza and 0.022 s at Spa. Second, Monaco plateaus at the current 4 MJ cap: above 4 MJ, no further improvement is possible regardless of cap level, because the circuit has insufficient straight length to absorb additional deployment. The track architecture, not the regulation, becomes the binding constraint. Third, Spa has a higher ceiling than Monza (0.422 s vs. 0.413 s at 6 MJ) because it has more absolute straight length even though its straight *percentage* is lower.

These results suggest that the FIA's 4 MJ cap is well-calibrated for street circuits like Monaco, where it coincides with the physical deployment ceiling. On power circuits, a modest cap increase to 5–6 MJ would yield measurable performance gains; beyond 6 MJ, diminishing returns make further cap increases largely ineffective.

---

## 5. Conclusions

Three explicit conclusions follow from the simulation results:

**C1.** Deployment timing is the primary determinant of ERS lap time benefit. An offline-optimized strategy extracting 0.400 s from 4 MJ of deployment at Monza outperforms an indiscriminate strategy extracting 0.144 s from the same energy — a 2.8× improvement attributable solely to concentrating deployment on straights.

**C2.** SOC-threshold controllers are systematically vulnerable to the Conservative paradox: they can deploy near-maximum energy budgets with zero lap time benefit if the deployment trigger fires during corner segments. Segment-type awareness is a necessary condition for effective ERS strategy.

**C3.** Circuit architecture sets the absolute ceiling on ERS benefit. Tracks with higher straight-distance fractions (Monza 53%, Spa 43%) permit greater improvement than street circuits (Monaco 14%). Strategy optimization is therefore more valuable at power circuits than at tight street circuits.

**C4.** The FIA 4 MJ/lap cap is the binding constraint at street circuits but not at power circuits. Relaxing the cap to 6 MJ would yield approximately 0.013–0.022 s additional improvement at Monza and Spa; beyond 6 MJ, diminishing returns make further increases practically ineffective. On Monaco, raising the cap above 4 MJ provides zero benefit — the track architecture is the constraint, not the regulation.

---

## 6. Limitations

The following limitations should be considered before generalizing these results:

| Limitation | Impact | Severity |
|-----------|--------|---------|
| Linear ERS time model (k = 1×10⁻⁷ s/J) | Assumes constant marginal benefit; diminishing returns at high deployment rates not captured | Medium |
| Straights-only time savings | Slightly pessimistic for medium-speed curves where power can assist (e.g., Spa's Eau Rouge) | Low |
| No tire degradation | Stint analysis reflects battery effects only; real stint performance declines faster | Medium |
| No fuel mass reduction | Car gets ~30 kg lighter over a race; lap time improves 0.03–0.04 s/lap from this alone | Low |
| Trapezoidal velocity profile | Linear speed interpolation within segments; underestimates speed at segment transitions | Low |
| LookaheadController heuristic mismatch | Uses legacy physics estimate for time benefit, not calibrated linear model | Low |
| Single-car model | No car-following, DRS, or traffic effects | Low |
| Battery capacity assumed fixed | Real battery capacity degrades with temperature and cycling | Low |

The most significant limitation is the linear time savings model. Real ERS deployment exhibits some saturation at very high deployment rates, meaning the Optimal strategy's 0.400 s figure may be slightly optimistic. However, because this model is applied *consistently* to all strategies, the relative comparisons (Optimal vs. Aggressive vs. Conservative) remain valid.

---

## References

1. FIA Formula One Technical Regulations, Article 5.2 (Energy Store and MGUK), 2023.
2. Perez, L.J. et al. "Energy management strategies for hybrid Formula 1 powertrains." *Proceedings of the Institution of Mechanical Engineers, Part D*, 2017.
3. Formula 1 official timing data, Autodromo Nazionale Monza, Italian Grand Prix 2023.
4. Formula 1 official timing data, Circuit de Spa-Francorchamps, Belgian Grand Prix 2023.
5. Formula 1 official timing data, Circuit de Monaco, Monaco Grand Prix 2023.
6. scipy.optimize.minimize documentation, SLSQP method. SciPy v1.11.

---

## Appendix A: Figure List

| Figure | File | Description |
|--------|------|-------------|
| A | `results/fig_a_improvement_by_track.png` | Bar chart: lap time improvement by strategy and circuit at SOC=0.6 |
| B | `results/fig_b_energy_vs_improvement.png` | Scatter: energy deployed vs. improvement (all tracks, all SOCs) with 0.1 s/MJ reference line |
| C | `results/fig_c_tornado.png` | Tornado chart: OAT sensitivity — parameter impact range by strategy |
| D | `results/fig_d_pareto.png` | Pareto frontier: lap time improvement vs. SOC remaining at lap end |
| E | `results/fig_e_stint.png` | Multi-lap stint: SOC depletion and lap time degradation over 5 laps (Monza, SOC=0.8) |
| F | `results/fig_f_cap_sensitivity.png` | Cap sensitivity: Optimal improvement vs. FIA deployment cap (2–8 MJ) across all 3 circuits |

---

## Appendix B: Reproducing Results

See `docs/reproducibility.md` for complete instructions. Summary:

```bash
pip install -r requirements.txt          # install dependencies
pytest tests/ -v                          # 29 tests, all pass
python -m experiments.sanity_check       # 5 invariants, all pass
python -m experiments.run_experiment     # regenerate all CSVs
# Open analysis/F1_analysis.ipynb and run all cells to regenerate figures
```
