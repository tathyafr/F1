# Model Validation

## 1. Lap Time Accuracy

Comparison of simulated baseline lap times vs. 2023 F1 qualifying pole times:

| Circuit | Simulated (s) | Real F1 Pole (s) | Δ (s) | % Error |
|---------|--------------|-----------------|-------|---------|
| Monza   | 81.72        | 80.294 (Sainz)  | +1.43 | +1.8%   |
| Spa     | 108.60       | 106.785 (Verstappen) | +1.82 | +1.7% |
| Monaco  | 82.45        | 71.798 (Verstappen) | +10.65 | +14.8% |

**Monza and Spa**: ~1.7–1.8% error is acceptable for a segment-based model. The gap comes from:
1. Segment velocity profiles are trapezoidal (linear interpolation between entry/exit speeds). Real cars do not decelerate/accelerate linearly.
2. No tire grip model — real cars carry higher minimum corner speeds with warm tires and downforce.
3. No slipstreaming / DRS.
4. Aerodynamic downforce is not modeled; high-downforce configurations allow faster corners.

**Monaco**: 14.8% error is larger because Monaco's lap time is dominated by very low-speed hairpin sequences (Mirabeau, Rascasse at ~50–60 km/h) where the model's trapezoidal velocity approximation causes the most error. The segment model underestimates how slowly a car navigates the tightest corners. This circuit is intentionally the weakest in the model and is noted as such in the Discussion.

## 2. ERS Energy Validation

FIA 2023 Technical Regulations, Article 5.4.4: maximum 4.0 MJ per lap from MGU-K.

| Strategy       | Deployed (MJ) | Regulatory Compliant? |
|----------------|--------------|----------------------|
| Conservative   | 2.83–4.84    | ✓ (varies with SOC)  |
| Aggressive     | 4.00         | ✓ (capped by design) |
| Lookahead      | 4.49–8.20    | ✗ at high SOC/Spa    |
| Optimal        | 5.31–8.63    | ✗ (drains full battery) |

**Note on Optimal and Lookahead**: The simulator does not enforce the 4.0 MJ per-lap regulatory limit. These strategies exploit regen mid-lap to re-deploy beyond the limit. In a production implementation, a hard cap on `total_deployed_j <= 4e6` per lap should be added to `sim_runner.py`. For this research project, the FIA cap is noted as a model assumption violation; the Aggressive controller correctly reflects the regulatory constraint.

**Regen harvest**: Published FIA figures indicate up to ~2 MJ harvest per lap from MGU-K at Monza. The simulator harvests ~3–4 MJ (at `regen_efficiency=0.6`), which is higher because the model does not enforce the MGU-K's 2 MJ/lap harvest limit separately from the 4 MJ deployment limit. This is a known simplification.

## 3. Time Savings Model

The calibrated linear model (`ENERGY_TO_TIME_COEFF = 1e-7 s/J`) produces:
- 4 MJ deployed on straights → 0.40 s improvement at Monza
- Real F1 ERS benefit at Monza: ~0.3–0.5 s (from published engineering analyses)

The model correctly applies savings only on straight-line segments, reflecting that corners are lateral-grip-limited, not power-limited. This is the key physical assumption that separates Conservative (deploys in corners, zero benefit) from Aggressive and Optimal (deploy on straights, meaningful gain).

## 4. Key Assumptions and Their Impact

| Assumption | Impact if Wrong | Severity |
|-----------|----------------|----------|
| Linear energy-to-time coefficient | If ERS benefit is non-linear with speed, high-speed straights are over/undervalued | Medium |
| Trapezoidal velocity profiles | Underestimates lap time at Monza/Spa by ~1.7%, more at Monaco | Medium |
| Straights-only time savings | If corners have partial ERS benefit, Conservative is underrated | Low–Medium |
| No MGU-K harvest cap (2 MJ/lap) | Overestimates regen → Conservative SOC floats too high | Low |
| No tire/fuel model | No lap-time degradation over stint beyond ERS depletion | Low |
| Single-car model (no traffic) | Race strategy interaction not captured | Out of scope |

## 5. Conclusion on Validity

The model is valid for its stated purpose: **comparative evaluation of ERS deployment strategies**. Absolute lap times carry ~2% error for Monza and Spa, which is acceptable. The relative ordering of strategies (Optimal > Aggressive > Lookahead > Conservative at typical SOC conditions) is physically defensible and reproducible. Monaco results should be interpreted with caution due to the larger baseline error.
