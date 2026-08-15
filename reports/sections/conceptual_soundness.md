# Conceptual Soundness Review - MR-001

## 1. Model Under Review

MR-001 is the Gaussian Parametric VaR / ES model. It is the primary model under
validation defined in the Phase 1 governance inventory.

## 2. Purpose and Intended Use

The Phase 1 governance artifacts define MR-001 for daily internal market-risk
monitoring of the project's hypothetical liquid multi-asset portfolio. The
portfolio is the existing V1 baseline equal-weight portfolio: SPY 25%, QQQ 25%,
TLT 25%, and GLD 25%. This review does not evaluate regulatory capital,
live institutional systems, or real institutional approval.

## 3. Core Model Assumptions

The relevant conceptual assumptions are that daily portfolio returns are
approximately Gaussian within the estimation framework, that mean and volatility
adequately characterize the relevant one-day distribution, that Gaussian
probabilities are a reasonable approximation for tail behavior, and that the
historical sample dynamics are sufficiently representative for rolling
estimation.

## 4. Empirical Distribution Assessment

The frozen Phase 0 return snapshot contains 2,054
portfolio-return observations from 2018-01-03 to
2026-03-06. Mean daily return is
0.000514, volatility is
0.007726, skewness is -0.050,
and excess kurtosis is 7.553.

Jarque-Bera statistic is 4855.089 with
p-value 0.000e+00. This is statistical evidence
that the return distribution is inconsistent with exact Gaussianity. It is not,
by itself, a final model validation decision.

The empirical 1% return quantile is
-2.0391% versus a fitted Gaussian
1% quantile of -1.7460%. The
empirical 5% return quantile is
-1.1843% versus a fitted Gaussian
5% quantile of -1.2194%. The QQ plot
and histogram artifacts provide visual evidence for this comparison.

## 5. Left-Tail Assessment

Loss-tail diagnostics are kept separate from rolling VaR backtesting. They use
the full fitted distribution only as a conceptual assumption check.

At the 95% loss tail, the empirical loss quantile is
1.1843% versus a Gaussian-implied threshold of
1.2194%. Observations beyond the fitted
Gaussian 95% loss threshold occur 91
times, a frequency of 4.43%.

At the 99% loss tail, the empirical loss quantile is
2.0391% versus a Gaussian-implied threshold of
1.7460%. Observations beyond the fitted
Gaussian 99% loss threshold occur 35
times, a frequency of 1.70%.

Observed excess kurtosis and heavier empirical left-tail behavior provide a
plausible mechanism for Gaussian VaR / ES to underestimate extreme losses,
particularly at high confidence levels.

## 6. Time Variation and Regime Stability

Rolling diagnostics use a trailing 60-day
window, so each rolling value uses only observations available through that
date. The descriptive volatility regimes are based on full-sample rolling
volatility quantiles:

- LOW_VOL: 0.005317 or lower
- NORMAL_VOL: between the 25th and 75th percentiles
- HIGH_VOL: 0.008027 or higher

These thresholds are DESCRIPTIVE RETROSPECTIVE REGIME ANALYSIS. They use
full-sample quantiles, are not causal monitoring thresholds, and must not be
presented as live trading or production monitoring signals. Phase 7 monitoring
thresholds will require a live-safe and predeclared approach.

| Regime | Obs. | Mean | Volatility | Skew | Excess Kurtosis | 99% Loss Quantile | Tail Limitation |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | --- |
| LOW_VOL | 499 | 0.000660 | 0.004789 | -0.504 | 2.187 | 1.2232% | no |
| NORMAL_VOL | 997 | 0.000427 | 0.006800 | -0.459 | 1.332 | 1.6978% | no |
| HIGH_VOL | 499 | 0.000628 | 0.011157 | 0.184 | 5.616 | 3.3168% | no |

The HIGH_VOL regime has the largest volatility and a materially larger 99% empirical loss quantile than the NORMAL_VOL regime, so Gaussian tail fragility appears most relevant in stressed volatility conditions.

## 7. Implications for MR-001

The statistical evidence shows returns are inconsistent with exact Gaussianity.
The model-risk implication is narrower and more practical: negative skewness,
excess kurtosis, and empirical tail differences may cause Gaussian VaR / ES to
understate downside risk in stressed or fat-tail periods. This does not by
itself establish model failure. Outcomes analysis and challenger comparison are
required in later validation phases.

Candidate concern: Gaussian tail assumptions may be materially weak during
high-volatility or fat-tail periods.

## 8. Limitations of Phase 2

- Public ETF proxies are used instead of real institutional positions.
- The sample is finite and covers one historical market period.
- Regime thresholds are retrospective/descriptive and not causal monitoring thresholds.
- The diagnostics use a daily horizon only.
- Conceptual diagnostics do not replace formal outcomes analysis.
- No challenger evidence is produced in Phase 2.
- No independent implementation verification is performed in Phase 2.

## 9. Phase 2 Conclusion

Conceptual soundness concerns identified. The evidence supports further testing
of MR-001 tail behavior in Phase 3 through Phase 5, but no final validation
decision is assigned in Phase 2.
