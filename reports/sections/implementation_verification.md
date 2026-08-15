# Implementation Verification - MR-001

## 1. Objective

Phase 3 tests whether the existing developer implementation correctly
calculates the formulas it claims to implement. This phase separates
implementation risk from methodology risk. The Phase 2 fat-tail concern remains
a conceptual assumption issue and does not imply an implementation defect.

## 2. Independence Design

Independent reference calculations live under
`market_risk_toolkit.validation.independent`. The reference modules do not
import `market_risk_toolkit.risk.metrics` or developer risk calculation modules.
The orchestration layer compares developer outputs with independent reference
outputs. This is project-level implementation independence, not organizational
independence.

Forbidden import check passed: `True`.

## 3. Formula Conventions

Gaussian VaR uses `mu + sigma * Phi^-1(1 - alpha)` as the lower-tail return
quantile and reports `max(0, -quantile)` as positive-loss VaR.

Gaussian ES uses lower-tail expected return
`mu - sigma * phi(z) / (1 - alpha)` where `z = Phi^-1(1 - alpha)`, then reports
`max(0, -tail_mean)` as positive-loss ES.

Historical VaR uses quantile probability `1 - alpha`, NumPy/Pandas linear
interpolation, and positive-loss reporting.

Historical ES includes observations at or below the historical VaR threshold,
averages those tail returns, and reports the positive loss.

All formulas drop NaN values, require at least two observations, use confidence
levels between 0 and 1, and Gaussian volatility uses sample standard deviation
with `ddof = 1`.

## 4. Test Cases

Evidence categories include hand-checkable fixtures, fixed-seed synthetic
windows, and 50 deterministic frozen portfolio windows selected evenly across
the Phase 0 local portfolio return snapshot.

## 5. Results

- Total cases: 58
- Total comparisons: 464
- Matches: 464
- Mismatches: 0
- Match fraction: 1.000000
- Required match fraction: 1.000000
- Maximum absolute difference: 0
- Mean absolute difference: 0
- Absolute tolerance: 1.0e-10

## 6. Discrepancy Analysis

No mismatches exceeded the predeclared tolerance.

If future discrepancies appear, likely root-cause categories include formula
defect, sign convention, quantile convention, degrees-of-freedom convention,
alignment issue, numerical precision, or unknown.

## 7. Conclusion

Implementation verification passed within the predeclared numerical tolerance. No final model validation decision is
assigned in Phase 3.
