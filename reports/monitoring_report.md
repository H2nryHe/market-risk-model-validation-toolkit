# Ongoing Model Monitoring Report

## 1. Purpose

Phase 7 implements a historical replay of an ongoing monitoring framework for
MR-001. Monitoring is a lifecycle control and a compensating control. It does
not erase the underlying Gaussian tail limitation or close validation findings.

## 2. Findings in Scope

- MV-001: MR-001 99% Gaussian far-tail calibration weakness, High, OPEN.
- MV-002: MR-001 95% exception clustering despite acceptable unconditional coverage, Moderate, OPEN.

## 3. Monitoring Framework

The framework monitors exception frequency, rolling Kupiec p-values, rolling
conditional-coverage p-values where data are meaningful, recent clustering,
challenger VaR divergence, causal volatility regime context, and Phase 6
data-quality gating.

## 4. Threshold Framework

Threshold version: 1.1, effective date:
2026-08-14. All thresholds are project controls, not regulatory
numerical requirements. The 15%/25% challenger-divergence thresholds originate
in Phase 1. The 0.05 statistical significance convention originates in Phase 1.
The 0.10 p-value AMBER band and recent-cluster thresholds are Phase 7
early-warning monitoring choices.

## 4A. Monitoring Framework Version Review

Phase 7 v1.0 was deliberately conservative. Historical replay revealed alert saturation,
including long RED periods driven by challenger divergence. The
primary design issue was not the numerical challenger thresholds. The issue was
aggregation semantics: methodological disagreement was being promoted directly
into hard model failure.

Version 1.1 preserves all numeric thresholds and distinguishes model-performance
evidence, temporal-dependence evidence, methodological disagreement, volatility
context, and data-quality hard failures. Challenger divergence remains measured
with the same 15%/25% thresholds and remains prominent as review context, but a
challenger difference alone is not treated as proof that MR-001 has failed.
Version 1.0 remains preserved for auditability under
`data/artifacts/monitoring_v1_0/` and
`configs/monitoring/thresholds_v1_0.yaml`.

Version 1.1 is not a post-hoc attempt to make MR-001 pass. Actual RED
model-performance evidence remains RED.

| framework_version | confidence_level | green_count | amber_count | red_count | insufficient_data_count | observation_count | red_fraction | longest_continuous_red_streak | red_episode_count |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 1.0 | 0.9500 | 99 | 290 | 1331 | 84 | 1804 | 0.7378 | 574 | 28 |
| 1.1 | 0.9500 | 99 | 912 | 709 | 84 | 1804 | 0.3930 | 231 | 11 |
| 1.0 | 0.9900 | 0 | 151 | 1527 | 126 | 1804 | 0.8465 | 527 | 17 |
| 1.1 | 0.9900 | 0 | 518 | 1160 | 126 | 1804 | 0.6430 | 406 | 6 |

## 5. Causal Volatility Regime

Trailing volatility window: 60. Calibration uses
the first 500 valid rolling-volatility
observations, from 2018-03-29 to
2020-03-24. Fixed boundaries are LOW <=
0.003910 and HIGH >=
0.006290. This is not the retrospective Phase 2/5
full-sample regime framework.

## 6. Historical Monitoring Results

| overall_status | 0.95 | 0.99 |
| --- | --- | --- |
| AMBER | 912 | 518 |
| RED | 709 | 1160 |
| GREEN | 99 | 0 |
| INSUFFICIENT_DATA | 84 | 126 |

## 7. Major Breaches

| date | confidence_level | metric | driver_type | observed_value | threshold | status | finding_id |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 2019-12-27 | 0.9500 | kupiec | FAR_TAIL_PERFORMANCE | 0.0001708561168588267 | AMBER p<0.10; RED p<0.05 | RED | MV-002 |
| 2019-12-27 | 0.9500 | far_tail_performance_watch | FAR_TAIL_PERFORMANCE | RED | RED if exception-rate or Kupiec status is RED; AMBER for AMBER performance evidence or challenger disagreement; challenger disagreement alone cannot create RED. | RED | MV-001 |
| 2019-12-27 | 0.9500 | overall | FAR_TAIL_PERFORMANCE | RED | v1.1 precedence: data-quality RED, far-tail-performance RED, temporal-dependence RED, then AMBER hard/contextual reviews; challenger alone cannot create RED. | RED | MV-001;MV-002 |
| 2019-12-27 | 0.9900 | kupiec | FAR_TAIL_PERFORMANCE | 0.02498150305344973 | AMBER p<0.10; RED p<0.05 | RED | MV-001 |
| 2019-12-27 | 0.9900 | far_tail_performance_watch | FAR_TAIL_PERFORMANCE | RED | RED if exception-rate or Kupiec status is RED; AMBER for AMBER performance evidence or challenger disagreement; challenger disagreement alone cannot create RED. | RED | MV-001 |
| 2019-12-27 | 0.9900 | overall | FAR_TAIL_PERFORMANCE | RED | v1.1 precedence: data-quality RED, far-tail-performance RED, temporal-dependence RED, then AMBER hard/contextual reviews; challenger alone cannot create RED. | RED | MV-001 |
| 2019-12-30 | 0.9500 | kupiec | FAR_TAIL_PERFORMANCE | 0.0001708561168588267 | AMBER p<0.10; RED p<0.05 | RED | MV-002 |
| 2019-12-30 | 0.9500 | far_tail_performance_watch | FAR_TAIL_PERFORMANCE | RED | RED if exception-rate or Kupiec status is RED; AMBER for AMBER performance evidence or challenger disagreement; challenger disagreement alone cannot create RED. | RED | MV-001 |
| 2019-12-30 | 0.9500 | overall | FAR_TAIL_PERFORMANCE | RED | v1.1 precedence: data-quality RED, far-tail-performance RED, temporal-dependence RED, then AMBER hard/contextual reviews; challenger alone cannot create RED. | RED | MV-001;MV-002 |
| 2019-12-30 | 0.9900 | kupiec | FAR_TAIL_PERFORMANCE | 0.02498150305344973 | AMBER p<0.10; RED p<0.05 | RED | MV-001 |
| 2019-12-30 | 0.9900 | far_tail_performance_watch | FAR_TAIL_PERFORMANCE | RED | RED if exception-rate or Kupiec status is RED; AMBER for AMBER performance evidence or challenger disagreement; challenger disagreement alone cannot create RED. | RED | MV-001 |
| 2019-12-30 | 0.9900 | overall | FAR_TAIL_PERFORMANCE | RED | v1.1 precedence: data-quality RED, far-tail-performance RED, temporal-dependence RED, then AMBER hard/contextual reviews; challenger alone cannot create RED. | RED | MV-001 |
| 2019-12-31 | 0.9500 | kupiec | FAR_TAIL_PERFORMANCE | 0.0001708561168588267 | AMBER p<0.10; RED p<0.05 | RED | MV-002 |
| 2019-12-31 | 0.9500 | far_tail_performance_watch | FAR_TAIL_PERFORMANCE | RED | RED if exception-rate or Kupiec status is RED; AMBER for AMBER performance evidence or challenger disagreement; challenger disagreement alone cannot create RED. | RED | MV-001 |
| 2019-12-31 | 0.9500 | overall | FAR_TAIL_PERFORMANCE | RED | v1.1 precedence: data-quality RED, far-tail-performance RED, temporal-dependence RED, then AMBER hard/contextual reviews; challenger alone cannot create RED. | RED | MV-001;MV-002 |
| 2019-12-31 | 0.9900 | kupiec | FAR_TAIL_PERFORMANCE | 0.02498150305344973 | AMBER p<0.10; RED p<0.05 | RED | MV-001 |
| 2019-12-31 | 0.9900 | far_tail_performance_watch | FAR_TAIL_PERFORMANCE | RED | RED if exception-rate or Kupiec status is RED; AMBER for AMBER performance evidence or challenger disagreement; challenger disagreement alone cannot create RED. | RED | MV-001 |
| 2019-12-31 | 0.9900 | overall | FAR_TAIL_PERFORMANCE | RED | v1.1 precedence: data-quality RED, far-tail-performance RED, temporal-dependence RED, then AMBER hard/contextual reviews; challenger alone cannot create RED. | RED | MV-001 |
| 2020-01-02 | 0.9500 | kupiec | FAR_TAIL_PERFORMANCE | 0.0001708561168588267 | AMBER p<0.10; RED p<0.05 | RED | MV-002 |
| 2020-01-02 | 0.9500 | far_tail_performance_watch | FAR_TAIL_PERFORMANCE | RED | RED if exception-rate or Kupiec status is RED; AMBER for AMBER performance evidence or challenger disagreement; challenger disagreement alone cannot create RED. | RED | MV-001 |

Individual breach resolution in the historical replay is not equivalent to closing
the linked model finding, remediation, or finding closure.

## 8. Latest Frozen Snapshot

This is a historical project snapshot as of the final date in the frozen
validation dataset, not a live/current market-risk status.

| as_of_date | confidence_level | overall_status | exception_rate_status | kupiec_status | conditional_coverage_status | cluster_status | dependence_watch_status | challenger_divergence_status | challenger_review_required | far_tail_performance_watch | volatility_regime | high_vol_tail_escalation | open_findings |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 2026-03-06 | 0.9500 | AMBER | GREEN | GREEN | RED | GREEN | AMBER | GREEN | False | GREEN | HIGH_VOL | False | MV-001;MV-002 |
| 2026-03-06 | 0.9900 | RED | RED | GREEN | AMBER | GREEN | AMBER | RED | True | RED | HIGH_VOL | True | MV-001;MV-002 |

## 9. MV-001 Remediation Evidence

RM-001 implements 99% tail-watch monitoring, challenger divergence monitoring,
and high-volatility escalation context. The Gaussian far-tail model limitation
itself has not been mathematically eliminated; the control reduces the risk of
unaware reliance on MR-001 99% output.

## 10. MV-002 Remediation Evidence

RM-002 implements rolling exception-rate monitoring, recent exception-cluster
monitoring, conditional-coverage monitoring when meaningful, and escalation for
clustered exceptions.

## 11. Data Quality Gate

Phase 6 data-quality controls are integrated as a hard gate. A blocking
data-quality failure forces overall monitoring RED and prevents risk outputs
from being treated as trusted for that date.

## 12. Remediation Status

Phase 8 assessed these monitoring actions as completed control implementation.
That completion does not close the underlying findings.

| remediation_id | finding_id | action | owner_role | status | target_date | completion_date | evidence |
| --- | --- | --- | --- | --- | --- | --- | --- |
| RM-001 | MV-001 | Implement 99% far-tail monitoring, challenger-divergence monitoring, high-volatility escalation context, and restrict standalone interpretation of MR-001 99% risk where monitoring identifies material disagreement. | Model Owner / Developer | COMPLETED | 2026-08-28 | 2026-08-14 | data/artifacts/monitoring_history.csv;data/artifacts/monitoring_breaches.csv;data/artifacts/monitoring_snapshot.csv;data/artifacts/monitoring_framework_comparison.csv;configs/monitoring/thresholds.yaml;configs/monitoring/thresholds_v1_0.yaml;data/artifacts/monitoring_v1_0/monitoring_summary.json;reports/monitoring_report.md |
| RM-002 | MV-002 | Implement rolling exception-rate monitoring, recent cluster monitoring, conditional-coverage monitoring, and escalation for clustered exceptions. | Independent Validation | COMPLETED | 2026-08-28 | 2026-08-14 | data/artifacts/monitoring_history.csv;data/artifacts/monitoring_breaches.csv;data/artifacts/monitoring_snapshot.csv;data/artifacts/monitoring_framework_comparison.csv;configs/monitoring/thresholds.yaml;configs/monitoring/thresholds_v1_0.yaml;data/artifacts/monitoring_v1_0/monitoring_summary.json;reports/monitoring_report.md |

## 13. Limitations

- Frozen historical dataset, not live monitoring.
- Project-specific thresholds and no institutional escalation process.
- Small 99% rolling samples: 250 observations imply about 2.5 expected exceptions.
- Conditional-coverage power is limited when exceptions are sparse.
- Public ETF proxies and no real-time feed.
- Findings are not closed in Phase 7.

## 14. Phase 7 / Phase 8 Release Context

The monitoring controls and remediation evidence are ready for Phase 8 closure
assessment. No VALIDATED, VALIDATED_WITH_CONDITIONS, RESTRICTED_USE, or
NOT_VALIDATED decision is assigned here.

Phase 8 subsequently assigned the final validation decision **RESTRICTED_USE**.
The monitoring report remains supporting evidence; it does not close MV-001 or
MV-002 and does not show that the Gaussian tail weakness or temporal-dependence
root causes were eliminated.
