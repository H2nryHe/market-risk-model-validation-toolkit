# Data Quality Impact and Validation Findings

## 1. Objective

Phase 6 has two goals: quantify how deterministic market-data failures propagate
into portfolio returns and VaR/ES estimates, and convert supported Phase 2-6
validation evidence into formal findings. Detection, blocking, and downstream
impact are evaluated separately.

## 2. Data Quality Scenario Design

Scenario dates use this predeclared rule: deterministic fixed-position rule on frozen price sample: DQ-01 begins at 40%, DQ-02 begins at 50%, DQ-03 occurs at 60%, DQ-04 begins at 70%, DQ-05 occurs at 80%; dates are not selected based on impact.

| scenario_id | scenario_name | asset | start_date | end_date | injection_type | expected_control |
| --- | --- | --- | --- | --- | --- | --- |
| DQ-01 | Missing observation block | SPY | 2021-04-09 | 2021-04-15 | set_price_missing | missingness |
| DQ-02 | Stale price sequence | TLT | 2022-01-31 | 2022-02-04 | forward_fill_stale_price | staleness |
| DQ-03 | Extreme bad print | QQQ | 2022-11-23 | 2022-11-23 | multiply_single_price | extreme_return |
| DQ-04 | Cross-asset date misalignment | GLD | 2023-09-20 | 2023-09-20 | shift_asset_plus_one_observation | date_alignment |
| DQ-05 | Corporate-action-like discontinuity | SPY | 2024-07-17 | 2024-07-17 | multiply_price_from_date_forward | extreme_return |

## 3. Control Framework

Controls cover missingness, staleness, extreme returns/outliers, date alignment,
and price validity. The staleness threshold of 3
unchanged daily prices and the 15% suspicious-return
threshold are project QA choices, not regulatory thresholds. Project policy
allows PASS, FLAG, or BLOCK; Phase 6 uses BLOCK for missing required prices,
severe staleness, extreme bad prints/discontinuities, date misalignment, and
non-finite/non-positive prices.

## 4. Data Quality Risk Impact

| scenario_id | detected | blocked | risk_pipeline_allowed | largest_abs_relative_var_change | material_var_impact |
| --- | --- | --- | --- | --- | --- |
| DQ-01 | True | True | False | 0.0205 | False |
| DQ-02 | True | True | False | 0.0062 | False |
| DQ-03 | True | True | False | 160.2357 | True |
| DQ-04 | True | True | False | 0.0888 | False |
| DQ-05 | True | True | False | 0.6641 | True |

Largest MR-001 VaR impacts if corrupted data were allowed downstream:

| scenario_id | model_id | confidence_level | affected_forecast_count | relative_var_change | max_relative_var_change | material_var_impact | risk_pipeline_allowed |
| --- | --- | --- | --- | --- | --- | --- | --- |
| DQ-01 | MR-001 | 0.9500 | 250 | 0.0072 | 0.0673 | False | False |
| DQ-02 | MR-001 | 0.9900 | 255 | 0.0012 | 0.0029 | False | False |
| DQ-03 | MR-001 | 0.9900 | 251 | 160.2357 | 220.8098 | True | False |
| DQ-04 | MR-001 | 0.9500 | 1803 | -0.0514 | 0.1458 | False | False |
| DQ-05 | MR-001 | 0.9500 | 250 | 0.6641 | 0.8232 | True | False |

Largest challenger VaR impacts if corrupted data were allowed downstream:

| scenario_id | model_id | confidence_level | affected_forecast_count | relative_var_change | max_relative_var_change | material_var_impact | risk_pipeline_allowed |
| --- | --- | --- | --- | --- | --- | --- | --- |
| DQ-01 | MR-002 | 0.9500 | 250 | 0.0205 | 0.2132 | False | False |
| DQ-02 | MR-004 | 0.9500 | 255 | -0.0062 | 0.0198 | False | False |
| DQ-03 | MR-004 | 0.9900 | 251 | 116.8015 | 466.7399 | True | False |
| DQ-04 | MR-004 | 0.9900 | 1803 | -0.0888 | 0.6860 | False | False |
| DQ-05 | MR-004 | 0.9900 | 250 | 0.3260 | 4.5895 | True | False |

The predeclared materiality threshold is a 10% absolute relative VaR change
from `configs/validation/validation_plan.yaml`. It is a project governance
indicator, not a Fed/OCC/FDIC requirement.

## 5. Control Effectiveness

All five intentionally injected scenarios were detected by their expected
controls and blocked by the project policy. Any material VaR distortion therefore
demonstrates downstream sensitivity to bad data if controls were bypassed; it is
not evidence that the model methodology failed because bad data made VaR wrong.

## 6. Integrated Model Evidence

Phase 2 showed excess kurtosis and a heavier empirical 99% loss tail than the
fitted Gaussian tail. Phase 3 verified 464/464 implementation comparisons, so
the weakness is not explained by a formula implementation defect. Phase 4 showed
MR-001 99% exception frequency materially above the nominal 1% tail and
meaningful challenger divergence. Phase 5 showed MR-001 99% weakness
concentrated in HIGH_VOL periods and MR-001 95% exception clustering despite
acceptable unconditional frequency.

## 7. Formal Validation Findings

| finding_id | model_id | category | title | description | evidence_artifact | severity | status | recommendation | owner_role | target_date | closure_criteria | opened_date | closed_date |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| MV-001 | MR-001 | Model Performance / Tail Calibration | Gaussian 99% VaR understates far-tail loss frequency and severity | Phase 2 conceptual diagnostics show heavy tails relative to a fitted Gaussian distribution; Phase 3 rules out an implementation mismatch; Phase 4 and Phase 5 show MR-001 99% exception frequency, regime concentration, challenger divergence, and ES shortfall evidence that are material for the project intended use. | data/artifacts/conceptual_soundness_summary.json;data/artifacts/implementation_verification_summary.json;data/artifacts/model_comparison.csv;data/artifacts/challenger_divergence.csv;data/artifacts/regime_backtest.csv;data/artifacts/es_diagnostics.csv | High | OPEN | Do not rely on standalone MR-001 99% Gaussian VaR as the sole far-tail risk measure; require challenger comparison, high-volatility escalation, and methodology enhancement evaluation before broader intended use. | Model Owner / Developer | 2026-12-12 | Implement approved project monitoring controls for MR-001 99% tail weakness; document challenger divergence thresholds; show frozen-sample monitoring/report generation; and explicitly restrict standalone interpretation of MR-001 99% where applicable. | 2026-08-14 |  |
| MV-002 | MR-001 | Outcomes Analysis / Temporal Dependence | VaR exceptions cluster despite acceptable 95% unconditional coverage | MR-001 95% unconditional coverage is close to nominal, but Phase 4 independence and conditional-coverage tests reject at the 5% project level and Phase 5 cluster diagnostics show extended exception grouping. | data/artifacts/model_comparison.csv;data/artifacts/exception_cluster_summary.csv;data/artifacts/regime_backtest.csv | Moderate | OPEN | Add rolling exception-rate and clustering monitoring, define escalation for clustered exceptions, and review challenger behavior during clustered or high-volatility periods. | Independent Validation | 2026-12-12 | Implement rolling exception and clustering monitoring; document escalation triggers; and include clustered-exception evidence in the ongoing monitoring report. | 2026-08-14 |  |

## 8. Data Quality Finding Decision

No formal data-quality control finding was opened. The deterministic injected
failures were detected and blocked by the Phase 6 project controls. The
scenarios still support the importance of upstream controls because several
would materially distort VaR if allowed downstream.

## 9. Phase 6 Conclusion

Formal findings opened: MV-001, MV-002. MV-001
captures material MR-001 99% far-tail calibration weakness. MV-002 captures
exception dependence/clustering at 95% despite acceptable unconditional
coverage. Phase 7 should link these OPEN findings to monitoring, escalation, and
remediation tracking. No final Phase 8 validation decision is assigned.

## 10. Limitations

- Synthetic DQ scenarios are deterministic control tests, not a statistical sample.
- Public ETF proxy data are used.
- Control thresholds are project-specific.
- Corrupted-data impact is measured hypothetically even when controls block the scenario.
- Phase 6 recommends remediation but does not execute remediation or monitoring.
