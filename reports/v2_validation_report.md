# Market Risk Model Validation Report

## 1. Executive Summary

This report validates MR-001, the Gaussian Parametric VaR / ES model for a hypothetical SPY/QQQ/TLT/GLD portfolio. The validation covers conceptual soundness, independent implementation verification, challenger benchmarking, outcomes and regime analysis, sensitivity, data quality, formal findings, remediation, and ongoing monitoring.

Final validation decision: **RESTRICTED_USE**. MR-001 is correctly implemented and useful as a transparent baseline, but it is not supported as a standalone 99% far-tail risk measure. MV-001 and MV-002 remain open.

## 2. Model Identification

- Model ID: MR-001
- Version: 0.1.0
- Methodology: rolling Gaussian one-day VaR / ES
- Owner role: Model Owner / Developer
- Validator role: Independent Validation
- Materiality: High within the project framework
- Portfolio: SPY / QQQ / TLT / GLD
- Horizon: one trading day
- Confidence levels: 95% and 99%

## 3. Purpose and Intended Use

Original intended use was daily internal market-risk monitoring, portfolio loss-threshold awareness, model comparison, and project risk reporting. Final supported use is narrower: transparent baseline monitoring and comparison, with restricted 99% interpretation and required challenger/monitoring context.

## 4. Validation Scope

Phases 2 through 7.1 covered conceptual diagnostics, independent implementation verification, challenger benchmarking, outcomes and stability analysis, data-quality impact, findings/remediation tracking, and monitoring framework hardening.

## 5. Data Assessment

The validation uses frozen public adjusted-close ETF data. Core hashes are recorded in generated summaries. Phase 6 injected five deterministic data-quality failures; all five were detected and blocked. Data limitations remain: public ETF proxies, daily data, finite history, and vendor-revision risk if data are refreshed.

## 6. Conceptual Soundness

The return distribution has excess kurtosis of 7.5525. The empirical 99% loss quantile is 2.0391%, compared with a fitted Gaussian 99% loss quantile of 1.7460%. This supports a far-tail conceptual concern, especially in high-volatility regimes.

## 7. Implementation Verification

Independent verification matched 464/464 comparisons, with match fraction 1.0 and maximum absolute difference 0.0. The observed weakness is not explained by a known implementation defect.

## 8. Challenger Benchmarking

At 99%, MR-001 recorded 41/1804 exceptions. MR-002, MR-003, and MR-004 recorded exception rates of 1.50%, 2.00%, and 1.33%. Empirical and filtered challengers improve some unconditional tail coverage dimensions, but no challenger is established as universally superior or approved.

## 9. Outcomes Analysis

MR-001 95% exception frequency is 4.82%, close to the nominal rate, with Kupiec p-value 0.7281. Conditional coverage p-value is 0.0346, and max project cluster length is 9.

MR-001 99% exception frequency is 2.27%, versus a 1% nominal tail rate. Realized loss to ES on 99% exception dates is 1.2936.

## 10. Regime Analysis

Retrospective Phase 2/5 regimes show MR-001 99% HIGH_VOL exception rate of 3.43% and high-vol concentration ratio 1.51. These are descriptive validation regimes, not live monitoring thresholds.

## 11. Sensitivity and Stability

Sensitivity covered 125/250/500-day windows, 95%/97.5%/99% confidence levels, EWMA lambdas 0.94/0.97/0.99, and fixed portfolio variants. Results were not used for post-hoc model selection. Tail-sample warnings remain important for high confidence levels and shorter empirical windows.

## 12. Stress Testing

V1 deterministic stress testing remains relevant scenario context. The largest deterministic baseline loss is equity_selloff at -3.75%. This is static project stress evidence, not regulatory stress capital.

## 13. Data Quality Impact

Phase 6 detected 5/5 and blocked 5/5 deterministic corruptions, with 0 false negatives. Material bad-data examples would have distorted VaR materially if allowed downstream, including QQQ x100 bad print and synthetic adjustment discontinuity. No DQ finding was opened because controls blocked the scenarios.

## 14. Formal Findings

| finding_id | severity | status | title | recommendation |
| --- | --- | --- | --- | --- |
| MV-001 | High | OPEN | Gaussian 99% VaR understates far-tail loss frequency and severity | Do not rely on standalone MR-001 99% Gaussian VaR as the sole far-tail risk measure; require challenger comparison, high-volatility escalation, and methodology enhancement evaluation before broader intended use. |
| MV-002 | Moderate | OPEN | VaR exceptions cluster despite acceptable 95% unconditional coverage | Add rolling exception-rate and clustering monitoring, define escalation for clustered exceptions, and review challenger behavior during clustered or high-volatility periods. |

Phase 8 closure assessment:

| finding_id | severity | root_cause_resolved | compensating_control_implemented | closure_criteria_satisfied | recommended_finding_status |
| --- | --- | --- | --- | --- | --- |
| MV-001 | High | False | True | False | OPEN |
| MV-002 | Moderate | False | True | False | OPEN |

## 15. Ongoing Monitoring

Phase 7 v1.0 was deliberately conservative and produced alert saturation. Phase 7.1 preserved all numeric thresholds and introduced v1.1 semantics that separate hard performance signals, temporal dependence, challenger disagreement, volatility context, and data-quality failures.

| framework_version | confidence_level | green_count | amber_count | red_count | insufficient_data_count | observation_count | red_fraction | longest_continuous_red_streak | red_episode_count |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 1.0000 | 0.9500 | 99 | 290 | 1331 | 84 | 1804 | 0.7378 | 574 | 28 |
| 1.1000 | 0.9500 | 99 | 912 | 709 | 84 | 1804 | 0.3930 | 231 | 11 |
| 1.0000 | 0.9900 | 0 | 151 | 1527 | 126 | 1804 | 0.8465 | 527 | 17 |
| 1.1000 | 0.9900 | 0 | 518 | 1160 | 126 | 1804 | 0.6430 | 406 | 6 |

The latest monitoring snapshot is frozen historical evidence as of 2026-03-06, not live/current monitoring.

## 16. Remediation Assessment

| remediation_id | finding_id | action | owner_role | status | target_date | completion_date | evidence |
| --- | --- | --- | --- | --- | --- | --- | --- |
| RM-001 | MV-001 | Implement 99% far-tail monitoring, challenger-divergence monitoring, high-volatility escalation context, and restrict standalone interpretation of MR-001 99% risk where monitoring identifies material disagreement. | Model Owner / Developer | COMPLETED | 2026-08-28 | 2026-08-14 | data/artifacts/monitoring_history.csv;data/artifacts/monitoring_breaches.csv;data/artifacts/monitoring_snapshot.csv;data/artifacts/monitoring_framework_comparison.csv;configs/monitoring/thresholds.yaml;configs/monitoring/thresholds_v1_0.yaml;data/artifacts/monitoring_v1_0/monitoring_summary.json;reports/monitoring_report.md |
| RM-002 | MV-002 | Implement rolling exception-rate monitoring, recent cluster monitoring, conditional-coverage monitoring, and escalation for clustered exceptions. | Independent Validation | COMPLETED | 2026-08-28 | 2026-08-14 | data/artifacts/monitoring_history.csv;data/artifacts/monitoring_breaches.csv;data/artifacts/monitoring_snapshot.csv;data/artifacts/monitoring_framework_comparison.csv;configs/monitoring/thresholds.yaml;configs/monitoring/thresholds_v1_0.yaml;data/artifacts/monitoring_v1_0/monitoring_summary.json;reports/monitoring_report.md |

RM-001 and RM-002 are completed as monitoring/control implementation actions. Completion does not mean the underlying Gaussian tail or temporal dependence root causes are eliminated.

## 17. Residual Model Risk

Residual risks remain: Gaussian far-tail calibration weakness, exception clustering, finite empirical tails, challenger limitations, proxy data, and lack of live institutional monitoring/escalation.

## 18. Final Validation Decision

Decision: **RESTRICTED_USE**.

Decision comparison:

- VALIDATED: Rejected: material unresolved High and Moderate findings remain.
- VALIDATED_WITH_CONDITIONS: Rejected: evidence does not support the full stated intended use with conditions alone, especially standalone 99% far-tail interpretation.
- RESTRICTED_USE: Selected: the model remains useful for transparent baseline and limited internal monitoring roles, but 99% use must be narrowed and controlled.
- NOT_VALIDATED: Rejected: implementation is correct and 95% unconditional coverage plus monitoring/challenger controls support meaningful restricted use.

## 19. Required Controls / Restrictions

- MR-001 99% Gaussian VaR must not be used as a standalone far-tail risk measure.
- 99% outputs require challenger context, far-tail monitoring, and high-volatility escalation.
- High-volatility periods require heightened review before relying on MR-001 tail estimates.
- Not for regulatory capital, real trading limits, live institutional systems, or automated decisions.
- Monitoring framework v1.1 with far-tail, dependence, challenger-review, volatility-context, and DQ gates.
- Challenger comparison for 99% MR-001 interpretation.
- High-volatility escalation when far-tail performance watch is AMBER or RED.
- Phase 6 data-quality controls must block material corruptions before risk outputs are used.
- Open findings MV-001/MV-002 must remain visible until root cause or governance closure is justified.

## 20. Revalidation Triggers

- Material methodology change.
- Material change to intended use.
- Material change to portfolio scope.
- Sustained RED far-tail performance.
- Repeated dependence or clustering escalation.
- Persistent challenger divergence.
- Material data-quality control failure.
- Significant input-data or source change.

## 21. Limitations

- Educational portfolio project, not a real bank validation.
- Public ETF proxies and daily adjusted-close data.
- One-day horizon and fixed frozen historical dataset.
- Project-specific thresholds and no institutional escalation process.
- No regulatory capital or live institutional-system claim.
- No real organizational independence.
- Finite empirical tails.
- No regulatory capital claim.

## 22. Artifact Index

- `data/artifacts/final_validation_decision.json`
- `data/artifacts/finding_closure_assessment.csv`
- `data/artifacts/release_metrics.json`
- `data/artifacts/model_comparison.csv`
- `data/artifacts/implementation_verification_summary.json`
- `data/artifacts/data_quality_summary.json`
- `data/artifacts/monitoring_summary.json`
- `reports/executive_summary.md`
- `reports/monitoring_report.md`
