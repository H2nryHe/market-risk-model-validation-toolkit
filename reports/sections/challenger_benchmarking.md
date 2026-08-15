# Challenger Benchmarking - MR-001

## 1. Objective

Phase 4 tests whether reasonable alternative methodologies produce materially
different VaR / ES estimates or lightweight backtesting evidence from MR-001.
It does not select a model winner or replace MR-001.

## 2. Models

- MR-001: Gaussian Parametric VaR / ES, the primary model under validation.
- MR-002: Historical Simulation VaR / ES, the existing V1 benchmark/challenger.
- MR-003: EWMA Gaussian VaR / ES, an implemented Phase 4 challenger.
- MR-004: Filtered Historical Simulation VaR / ES, an implemented Phase 4 challenger.

## 3. Challenger Methodologies

MR-003 uses a 250-day estimation window, lambda 0.94, a 20-day sample-variance
seed, and a zero-mean one-day forecasting assumption. The zero-mean assumption
is a challenger-model choice, not a universal claim about returns.

MR-004 uses the same EWMA volatility filter. Seed observations initialize
variance and are not standardized into the residual pool. Each residual uses a
volatility estimate based only on prior returns. The forecast volatility uses
returns through t-1. At 99%, about 230 residuals provide only a small far-tail
sample, so FHS 99% ES should not be treated as highly precise.

## 4. Sample Alignment

Native forecast counts by model: {'MR-001': 1804, 'MR-002': 1804, 'MR-003': 1804, 'MR-004': 1804}.
The common comparison sample runs from 2019-01-02 to
2026-03-06 with 1804 observations. All four
models share the same forecast dates: True.

## 5. VaR / ES And Backtesting Comparison

Average exceedance severity is defined as realized loss divided by VaR for
exception observations only.

| Model | CL | Mean VaR | Mean ES | Exceptions | Exception Rate | Kupiec p | Indep. p | CC p | Avg Severity |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| MR-001 | 0.95 | 1.2099% | 1.5302% | 87 | 4.82% | 0.7281 | 0.0101 | 0.0346 | 1.654 |
| MR-002 | 0.95 | 1.1570% | 1.7155% | 86 | 4.77% | 0.6476 | 0.6516 | 0.8135 | 1.775 |
| MR-003 | 0.95 | 1.2000% | 1.5048% | 86 | 4.77% | 0.6476 | 0.5501 | 0.7535 | 1.499 |
| MR-004 | 0.95 | 1.2279% | 1.7849% | 90 | 4.99% | 0.9828 | 0.4328 | 0.7350 | 1.530 |
| MR-001 | 0.99 | 1.7323% | 1.9921% | 41 | 2.27% | 0.0000 | 0.0785 | 0.0000 | 1.533 |
| MR-002 | 0.99 | 2.0797% | 2.4996% | 27 | 1.50% | 0.0483 | 0.0067 | 0.0036 | 1.522 |
| MR-003 | 0.99 | 1.6972% | 1.9444% | 36 | 2.00% | 0.0002 | 0.0378 | 0.0001 | 1.364 |
| MR-004 | 0.99 | 2.1134% | 2.4586% | 24 | 1.33% | 0.1795 | 0.0399 | 0.0492 | 1.334 |

## 6. Divergence From MR-001

Phase 1 amber/red thresholds are project methodology-divergence indicators, not
regulatory limits or automatic failure rules.

| Challenger | CL | Mean Abs. Rel. Div. | Median Abs. Rel. Div. | Above 15% | Above 25% |
| --- | ---: | ---: | ---: | ---: | ---: |
| MR-002 | 0.95 | 8.03% | 5.46% | 15.91% | 6.15% |
| MR-003 | 0.95 | 23.77% | 17.25% | 55.71% | 35.81% |
| MR-004 | 0.95 | 29.06% | 22.83% | 65.02% | 46.40% |
| MR-002 | 0.99 | 19.66% | 12.70% | 42.41% | 27.83% |
| MR-003 | 0.99 | 23.96% | 17.97% | 56.82% | 35.98% |
| MR-004 | 0.99 | 37.36% | 26.94% | 68.57% | 52.61% |

## 7. Interpretation

Challenger evidence should be read as methodology evidence, not model selection.
Volatility-responsive models can change estimates materially when recent
volatility differs from the rolling sample average. FHS can reveal empirical
residual-tail behavior, but the finite residual pool makes 99% tail estimates
sample-limited.

## 8. Limitations

- Public ETF proxy portfolio.
- Fixed 250-day window.
- Lambda 0.94 is predeclared and not tuned.
- Zero-mean EWMA/FHS assumption.
- Finite FHS residual tail, especially at 99%.
- Same historical sample is used across methodologies.
- Phase 4 does not perform full regime, sensitivity, or stability analysis.

## 9. Phase 4 Conclusion

Challenger evidence indicates material methodology divergence. No final validation decision is assigned.
