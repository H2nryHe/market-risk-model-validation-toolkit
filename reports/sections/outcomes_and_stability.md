# Outcomes, Regime, and Stability Analysis

## 1. Objective

Phase 5 tests when, how often, and how severely the model forecasts fail. A
single unconditional exception count can hide clustering, volatility-regime
concentration, ES shortfall behavior, and sensitivity to predeclared modeling
choices.

## 2. Exception Diagnostics

Common Phase 4 sample reused for Phase 5: 2019-01-02 to
2026-03-06, 1804 observations, four models.
Input returns SHA-256: `76116af57c526231c62fe83ae2e26e8be41bc5a28a418bbdef5be79fd8b1b08e`. Challenger forecast
artifact SHA-256: `181bc00ad0eccecef6f47a0f757f3986ad11cc4950e4dd1f6d818efceb139567`.

| model_id | confidence_level | exception_count | exception_rate | max_cluster_length | number_of_clusters | median_days_between_exceptions | average_exception_severity | maximum_exception_severity |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| MR-001 | 0.9500 | 87 | 0.0482 | 9 | 53 | 8.5000 | 1.6537 | 6.3593 |
| MR-002 | 0.9500 | 86 | 0.0477 | 8 | 61 | 11.0000 | 1.7748 | 7.7157 |
| MR-003 | 0.9500 | 86 | 0.0477 | 5 | 61 | 12.0000 | 1.4988 | 2.9638 |
| MR-004 | 0.9500 | 90 | 0.0499 | 5 | 63 | 11.0000 | 1.5297 | 3.7997 |
| MR-001 | 0.9900 | 41 | 0.0227 | 5 | 27 | 10.0000 | 1.5330 | 4.3968 |
| MR-002 | 0.9900 | 27 | 0.0150 | 5 | 16 | 16.0000 | 1.5221 | 2.8660 |
| MR-003 | 0.9900 | 36 | 0.0200 | 3 | 30 | 38.0000 | 1.3638 | 2.0955 |
| MR-004 | 0.9900 | 24 | 0.0133 | 3 | 21 | 58.0000 | 1.3337 | 2.1445 |

Cluster definition: adjacent exceptions separated by <=5 trading observations
are assigned to the same project diagnostic cluster. This is not a regulatory
threshold. Rolling exception rates use trailing 125- and 250-observation windows
only.

## 3. Exceedance Severity

Top exception severity observations:

| date | model_id | confidence_level | realized_loss | var | exceedance_amount | severity_ratio | volatility_regime |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 2020-03-12 | MR-002 | 0.9500 | 0.0553 | 0.0072 | 0.0481 | 7.7157 | HIGH_VOL |
| 2020-03-12 | MR-001 | 0.9500 | 0.0553 | 0.0087 | 0.0466 | 6.3593 | HIGH_VOL |
| 2020-03-16 | MR-002 | 0.9500 | 0.0440 | 0.0074 | 0.0366 | 5.9519 | HIGH_VOL |
| 2020-03-18 | MR-002 | 0.9500 | 0.0393 | 0.0075 | 0.0319 | 5.2625 | HIGH_VOL |
| 2020-03-11 | MR-002 | 0.9500 | 0.0332 | 0.0070 | 0.0262 | 4.7710 | HIGH_VOL |

## 4. Regime Analysis

Regimes reuse the Phase 2 LOW_VOL / NORMAL_VOL / HIGH_VOL labels. They are
retrospective/descriptive because Phase 2 thresholds used full-sample volatility
quantiles; these labels are not live monitoring thresholds.

| model_id | confidence_level | high_vol_exception_rate | low_vol_exception_rate | normal_vol_exception_rate | fraction_all_exceptions_in_high_vol | high_vol_exception_concentration_ratio | high_vol_severity |
| --- | --- | --- | --- | --- | --- | --- | --- |
| MR-001 | 0.9500 | 0.0768 | 0.0171 | 0.0467 | 0.4368 | 1.5918 | 1.7646 |
| MR-001 | 0.9900 | 0.0343 | 0.0098 | 0.0222 | 0.4146 | 1.5111 | 1.7701 |
| MR-002 | 0.9500 | 0.0727 | 0.0171 | 0.0478 | 0.4186 | 1.5256 | 2.0012 |
| MR-002 | 0.9900 | 0.0242 | 0.0098 | 0.0122 | 0.4444 | 1.6198 | 1.6085 |
| MR-003 | 0.9500 | 0.0444 | 0.0390 | 0.0534 | 0.2558 | 0.9323 | 1.4974 |
| MR-003 | 0.9900 | 0.0202 | 0.0195 | 0.0200 | 0.2778 | 1.0123 | 1.3096 |
| MR-004 | 0.9500 | 0.0384 | 0.0439 | 0.0590 | 0.2111 | 0.7694 | 1.4469 |
| MR-004 | 0.9900 | 0.0081 | 0.0220 | 0.0122 | 0.1667 | 0.6074 | 1.1851 |

## 5. Expected Shortfall Diagnostics

These ES diagnostics are descriptive outcomes conditional on VaR exceptions,
not a definitive regulatory ES backtest.

| model_id | confidence_level | mean_forecast_es_on_exception_dates | mean_realized_loss_on_exception_dates | realized_loss_to_es_ratio | fraction_exceptions_exceeding_es |
| --- | --- | --- | --- | --- | --- |
| MR-001 | 0.9500 | 0.0145 | 0.0181 | 1.2500 | 0.5977 |
| MR-002 | 0.9500 | 0.0172 | 0.0183 | 1.0648 | 0.4535 |
| MR-003 | 0.9500 | 0.0145 | 0.0172 | 1.1840 | 0.6047 |
| MR-004 | 0.9500 | 0.0164 | 0.0165 | 1.0078 | 0.4556 |
| MR-001 | 0.9900 | 0.0172 | 0.0223 | 1.2936 | 0.5854 |
| MR-002 | 0.9900 | 0.0213 | 0.0251 | 1.1769 | 0.5926 |
| MR-003 | 0.9900 | 0.0178 | 0.0212 | 1.1878 | 0.7778 |
| MR-004 | 0.9900 | 0.0183 | 0.0200 | 1.0947 | 0.6250 |

## 6. Lookback Sensitivity

The lookback grid retained every predeclared 125/250/500-day window and every
95%/97.5%/99% confidence level. Native samples are each window's own available
forecast sample. Common sensitivity samples use the date intersection across
the compared windows.

| model_id | portfolio_id | window | lambda | confidence_level | sample_type | exception_rate | kupiec_p_value | conditional_coverage_p_value | tail_sample_warning |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| MR-001 | equal_weight | 125 | 0.9400 | 0.9500 | common_sensitivity_sample | 0.0573 | 0.1982 | 0.3787 |  |
| MR-002 | equal_weight | 125 | 0.9400 | 0.9500 | common_sensitivity_sample | 0.0631 | 0.0229 | 0.0750 |  |
| MR-003 | equal_weight | 125 | 0.9400 | 0.9500 | common_sensitivity_sample | 0.0508 | 0.8800 | 0.8460 |  |
| MR-004 | equal_weight | 125 | 0.9400 | 0.9500 | common_sensitivity_sample | 0.0579 | 0.1621 | 0.3168 |  |
| MR-001 | equal_weight | 125 | 0.9400 | 0.9750 | common_sensitivity_sample | 0.0393 | 0.0009 | 0.0037 |  |
| MR-002 | equal_weight | 125 | 0.9400 | 0.9750 | common_sensitivity_sample | 0.0360 | 0.0089 | 0.0260 | TAIL_SAMPLE_LIMITED |
| MR-003 | equal_weight | 125 | 0.9400 | 0.9750 | common_sensitivity_sample | 0.0386 | 0.0014 | 0.0056 |  |
| MR-004 | equal_weight | 125 | 0.9400 | 0.9750 | common_sensitivity_sample | 0.0347 | 0.0200 | 0.0490 | TAIL_SAMPLE_LIMITED |
| MR-001 | equal_weight | 125 | 0.9400 | 0.9900 | common_sensitivity_sample | 0.0277 | 0.0000 | 0.0000 |  |
| MR-002 | equal_weight | 125 | 0.9400 | 0.9900 | common_sensitivity_sample | 0.0225 | 0.0000 | 0.0000 | TAIL_SAMPLE_LIMITED |
| MR-003 | equal_weight | 125 | 0.9400 | 0.9900 | common_sensitivity_sample | 0.0219 | 0.0000 | 0.0000 |  |
| MR-004 | equal_weight | 125 | 0.9400 | 0.9900 | common_sensitivity_sample | 0.0193 | 0.0011 | 0.0042 | TAIL_SAMPLE_LIMITED |
| MR-001 | equal_weight | 250 | 0.9400 | 0.9500 | common_sensitivity_sample | 0.0547 | 0.4023 | 0.0483 |  |
| MR-002 | equal_weight | 250 | 0.9400 | 0.9500 | common_sensitivity_sample | 0.0541 | 0.4689 | 0.7504 |  |
| MR-003 | equal_weight | 250 | 0.9400 | 0.9500 | common_sensitivity_sample | 0.0508 | 0.8800 | 0.8460 |  |
| MR-004 | equal_weight | 250 | 0.9400 | 0.9500 | common_sensitivity_sample | 0.0521 | 0.7028 | 0.7479 |  |
| MR-001 | equal_weight | 250 | 0.9400 | 0.9750 | common_sensitivity_sample | 0.0360 | 0.0089 | 0.0260 |  |
| MR-002 | equal_weight | 250 | 0.9400 | 0.9750 | common_sensitivity_sample | 0.0296 | 0.2587 | 0.2393 |  |
| MR-003 | equal_weight | 250 | 0.9400 | 0.9750 | common_sensitivity_sample | 0.0386 | 0.0014 | 0.0056 |  |
| MR-004 | equal_weight | 250 | 0.9400 | 0.9750 | common_sensitivity_sample | 0.0277 | 0.5073 | 0.2827 |  |
| MR-001 | equal_weight | 250 | 0.9400 | 0.9900 | common_sensitivity_sample | 0.0264 | 0.0000 | 0.0000 |  |
| MR-002 | equal_weight | 250 | 0.9400 | 0.9900 | common_sensitivity_sample | 0.0174 | 0.0082 | 0.0011 | TAIL_SAMPLE_LIMITED |
| MR-003 | equal_weight | 250 | 0.9400 | 0.9900 | common_sensitivity_sample | 0.0219 | 0.0000 | 0.0000 |  |
| MR-004 | equal_weight | 250 | 0.9400 | 0.9900 | common_sensitivity_sample | 0.0135 | 0.1864 | 0.0404 | TAIL_SAMPLE_LIMITED |
| MR-001 | equal_weight | 500 | 0.9400 | 0.9500 | common_sensitivity_sample | 0.0534 | 0.5416 | 0.0422 |  |
| MR-002 | equal_weight | 500 | 0.9400 | 0.9500 | common_sensitivity_sample | 0.0579 | 0.1621 | 0.0505 |  |
| MR-003 | equal_weight | 500 | 0.9400 | 0.9500 | common_sensitivity_sample | 0.0508 | 0.8800 | 0.8460 |  |
| MR-004 | equal_weight | 500 | 0.9400 | 0.9500 | common_sensitivity_sample | 0.0502 | 0.9722 | 0.8788 |  |
| MR-001 | equal_weight | 500 | 0.9400 | 0.9750 | common_sensitivity_sample | 0.0360 | 0.0089 | 0.0058 |  |
| MR-002 | equal_weight | 500 | 0.9400 | 0.9750 | common_sensitivity_sample | 0.0302 | 0.1996 | 0.0795 |  |
| MR-003 | equal_weight | 500 | 0.9400 | 0.9750 | common_sensitivity_sample | 0.0386 | 0.0014 | 0.0056 |  |
| MR-004 | equal_weight | 500 | 0.9400 | 0.9750 | common_sensitivity_sample | 0.0270 | 0.6134 | 0.2823 |  |
| MR-001 | equal_weight | 500 | 0.9400 | 0.9900 | common_sensitivity_sample | 0.0206 | 0.0002 | 0.0001 |  |
| MR-002 | equal_weight | 500 | 0.9400 | 0.9900 | common_sensitivity_sample | 0.0135 | 0.1864 | 0.0037 |  |
| MR-003 | equal_weight | 500 | 0.9400 | 0.9900 | common_sensitivity_sample | 0.0219 | 0.0000 | 0.0000 |  |
| MR-004 | equal_weight | 500 | 0.9400 | 0.9900 | common_sensitivity_sample | 0.0135 | 0.1864 | 0.0404 | TAIL_SAMPLE_LIMITED |

## 7. EWMA Lambda Sensitivity

Lambda sensitivity keeps the canonical default at 0.94 and also runs 0.97 and
0.99 for MR-003 and MR-004. No parameter is permanently changed based on these
results.

| model_id | portfolio_id | window | lambda | confidence_level | sample_type | exception_rate | kupiec_p_value | conditional_coverage_p_value | tail_sample_warning |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| MR-003 | equal_weight | 250 | 0.9400 | 0.9500 | native_sample | 0.0477 | 0.6476 | 0.7535 |  |
| MR-004 | equal_weight | 250 | 0.9400 | 0.9500 | native_sample | 0.0499 | 0.9828 | 0.7350 |  |
| MR-003 | equal_weight | 250 | 0.9400 | 0.9750 | native_sample | 0.0344 | 0.0158 | 0.0458 |  |
| MR-004 | equal_weight | 250 | 0.9400 | 0.9750 | native_sample | 0.0266 | 0.6651 | 0.3690 |  |
| MR-003 | equal_weight | 250 | 0.9400 | 0.9900 | native_sample | 0.0200 | 0.0002 | 0.0001 |  |
| MR-004 | equal_weight | 250 | 0.9400 | 0.9900 | native_sample | 0.0133 | 0.1795 | 0.0492 | TAIL_SAMPLE_LIMITED |
| MR-003 | equal_weight | 250 | 0.9700 | 0.9500 | native_sample | 0.0466 | 0.4982 | 0.7005 |  |
| MR-004 | equal_weight | 250 | 0.9700 | 0.9500 | native_sample | 0.0499 | 0.9828 | 0.7350 |  |
| MR-003 | equal_weight | 250 | 0.9700 | 0.9750 | native_sample | 0.0338 | 0.0228 | 0.0611 |  |
| MR-004 | equal_weight | 250 | 0.9700 | 0.9750 | native_sample | 0.0249 | 0.9880 | 0.3156 |  |
| MR-003 | equal_weight | 250 | 0.9700 | 0.9900 | native_sample | 0.0194 | 0.0004 | 0.0002 |  |
| MR-004 | equal_weight | 250 | 0.9700 | 0.9900 | native_sample | 0.0161 | 0.0172 | 0.0135 | TAIL_SAMPLE_LIMITED |
| MR-003 | equal_weight | 250 | 0.9900 | 0.9500 | native_sample | 0.0405 | 0.0550 | 0.1322 |  |
| MR-004 | equal_weight | 250 | 0.9900 | 0.9500 | native_sample | 0.0477 | 0.6476 | 0.8995 |  |
| MR-003 | equal_weight | 250 | 0.9900 | 0.9750 | native_sample | 0.0294 | 0.2462 | 0.2901 |  |
| MR-004 | equal_weight | 250 | 0.9900 | 0.9750 | native_sample | 0.0249 | 0.9880 | 0.3156 |  |
| MR-003 | equal_weight | 250 | 0.9900 | 0.9900 | native_sample | 0.0161 | 0.0172 | 0.0022 |  |
| MR-004 | equal_weight | 250 | 0.9900 | 0.9900 | native_sample | 0.0139 | 0.1197 | 0.0048 | TAIL_SAMPLE_LIMITED |

## 8. Portfolio Sensitivity

The portfolio grid uses four fixed, predeclared weight sets:
equal_weight, equity_heavy, rates_heavy, and diversified_balanced. Weights were
not optimized after observing results.

| model_id | portfolio_id | window | lambda | confidence_level | sample_type | exception_rate | kupiec_p_value | conditional_coverage_p_value | tail_sample_warning |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| MR-001 | diversified_balanced | 250 | 0.9400 | 0.9500 | native_sample | 0.0443 | 0.2616 | 0.0191 |  |
| MR-002 | diversified_balanced | 250 | 0.9400 | 0.9500 | native_sample | 0.0493 | 0.8966 | 0.1203 |  |
| MR-003 | diversified_balanced | 250 | 0.9400 | 0.9500 | native_sample | 0.0488 | 0.8114 | 0.7654 |  |
| MR-004 | diversified_balanced | 250 | 0.9400 | 0.9500 | native_sample | 0.0521 | 0.6834 | 0.5753 |  |
| MR-001 | diversified_balanced | 250 | 0.9400 | 0.9900 | native_sample | 0.0211 | 0.0000 | 0.0000 |  |
| MR-002 | diversified_balanced | 250 | 0.9400 | 0.9900 | native_sample | 0.0144 | 0.0773 | 0.0043 | TAIL_SAMPLE_LIMITED |
| MR-003 | diversified_balanced | 250 | 0.9400 | 0.9900 | native_sample | 0.0200 | 0.0002 | 0.0001 |  |
| MR-004 | diversified_balanced | 250 | 0.9400 | 0.9900 | native_sample | 0.0133 | 0.1795 | 0.0492 | TAIL_SAMPLE_LIMITED |
| MR-001 | equal_weight | 250 | 0.9400 | 0.9500 | native_sample | 0.0482 | 0.7281 | 0.0346 |  |
| MR-002 | equal_weight | 250 | 0.9400 | 0.9500 | native_sample | 0.0477 | 0.6476 | 0.8135 |  |
| MR-003 | equal_weight | 250 | 0.9400 | 0.9500 | native_sample | 0.0477 | 0.6476 | 0.7535 |  |
| MR-004 | equal_weight | 250 | 0.9400 | 0.9500 | native_sample | 0.0499 | 0.9828 | 0.7350 |  |
| MR-001 | equal_weight | 250 | 0.9400 | 0.9900 | native_sample | 0.0227 | 0.0000 | 0.0000 |  |
| MR-002 | equal_weight | 250 | 0.9400 | 0.9900 | native_sample | 0.0150 | 0.0483 | 0.0036 | TAIL_SAMPLE_LIMITED |
| MR-003 | equal_weight | 250 | 0.9400 | 0.9900 | native_sample | 0.0200 | 0.0002 | 0.0001 |  |
| MR-004 | equal_weight | 250 | 0.9400 | 0.9900 | native_sample | 0.0133 | 0.1795 | 0.0492 | TAIL_SAMPLE_LIMITED |
| MR-001 | equity_heavy | 250 | 0.9400 | 0.9500 | native_sample | 0.0543 | 0.4057 | 0.1089 |  |
| MR-002 | equity_heavy | 250 | 0.9400 | 0.9500 | native_sample | 0.0532 | 0.5350 | 0.2083 |  |
| MR-003 | equity_heavy | 250 | 0.9400 | 0.9500 | native_sample | 0.0565 | 0.2114 | 0.3266 |  |
| MR-004 | equity_heavy | 250 | 0.9400 | 0.9500 | native_sample | 0.0549 | 0.3490 | 0.5116 |  |
| MR-001 | equity_heavy | 250 | 0.9400 | 0.9900 | native_sample | 0.0238 | 0.0000 | 0.0000 |  |
| MR-002 | equity_heavy | 250 | 0.9400 | 0.9900 | native_sample | 0.0155 | 0.0292 | 0.0029 | TAIL_SAMPLE_LIMITED |
| MR-003 | equity_heavy | 250 | 0.9400 | 0.9900 | native_sample | 0.0233 | 0.0000 | 0.0000 |  |
| MR-004 | equity_heavy | 250 | 0.9400 | 0.9900 | native_sample | 0.0150 | 0.0483 | 0.1029 | TAIL_SAMPLE_LIMITED |
| MR-001 | rates_heavy | 250 | 0.9400 | 0.9500 | native_sample | 0.0560 | 0.2519 | 0.1090 |  |
| MR-002 | rates_heavy | 250 | 0.9400 | 0.9500 | native_sample | 0.0554 | 0.2977 | 0.1105 |  |
| MR-003 | rates_heavy | 250 | 0.9400 | 0.9500 | native_sample | 0.0549 | 0.3490 | 0.5108 |  |
| MR-004 | rates_heavy | 250 | 0.9400 | 0.9500 | native_sample | 0.0538 | 0.4678 | 0.5634 |  |
| MR-001 | rates_heavy | 250 | 0.9400 | 0.9900 | native_sample | 0.0172 | 0.0054 | 0.0001 |  |
| MR-002 | rates_heavy | 250 | 0.9400 | 0.9900 | native_sample | 0.0144 | 0.0773 | 0.0004 | TAIL_SAMPLE_LIMITED |
| MR-003 | rates_heavy | 250 | 0.9400 | 0.9900 | native_sample | 0.0161 | 0.0172 | 0.0460 |  |
| MR-004 | rates_heavy | 250 | 0.9400 | 0.9900 | native_sample | 0.0133 | 0.1795 | 0.2512 | TAIL_SAMPLE_LIMITED |

## 9. Stability Assessment

Robust conclusions: far-tail behavior remains sensitive across methodologies,
and empirical tail estimates are sample-limited for smaller windows and high
confidence levels. Parameter-sensitive conclusions: EWMA/FHS estimates move
materially with lambda, especially in the 99% tail. Portfolio-sensitive
conclusions: exception rates and mean VaR change under equity-heavy versus
rates-heavy weights, so Phase 6 findings should avoid overgeneralizing from a
single portfolio. Small empirical-tail samples are explicitly flagged as
TAIL_SAMPLE_LIMITED in `sensitivity_results.csv`.

## 10. Integrated Phase 5 Interpretation

- H1: SUPPORTED. MR-001 99% HIGH_VOL exception rate 3.43% versus NORMAL_VOL 2.22%; high-vol concentration ratio 1.51.
- H2: SUPPORTED. MR-001 95% exception rate 4.82%, Kupiec p 0.7281, conditional coverage p 0.0346, max project cluster 9.
- H3: SUPPORTED. MR-003 99% exception rate 2.00%, Kupiec p 0.0002; volatility responsiveness alone does not remove far-tail rejection.
- H4: SUPPORTED. MR-002/MR-004 99% rates 1.50%/1.33% versus MR-001 2.27%; conditional p-values 0.0036/0.0492.

Candidate concern A: 99% Gaussian VaR shows persistent far-tail weakness.
Evidence comes from Phase 2 fat-tail diagnostics, Phase 4 challenger comparison,
and Phase 5 regime/outcomes results. This is candidate finding evidence only;
no formal finding or severity is assigned in Phase 5.

Candidate concern B: 95% Gaussian VaR weakness appears more conditional than
unconditional. Exception frequency is close to nominal, but clustering and
conditional-coverage evidence require Phase 6 integration before any formal
finding.

## 11. Limitations

- Public ETF proxies rather than a production portfolio.
- Retrospective regime classification based on full-sample Phase 2 thresholds.
- Finite empirical tails, especially 99% with 125-day windows.
- Overlapping rolling samples create dependence in outcomes.
- ES analysis is descriptive and conditional on VaR exceptions.
- Fixed parameter grids are sensitivity diagnostics, not optimization.
- No formal finding, severity, remediation item, or final validation decision is created here.

## 12. Phase 5 Conclusion

Phase 5 establishes that model outcomes differ by volatility regime, exception
clustering matters beyond frequency, and some challenger/parameter choices
improve unconditional 99% coverage while retaining conditional-coverage or
finite-tail limitations. This evidence should proceed to Phase 6 findings and
data-quality impact analysis, but it is not a final validation decision.
