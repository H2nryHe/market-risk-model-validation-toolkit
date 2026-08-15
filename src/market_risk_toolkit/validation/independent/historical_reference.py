"""Independent Historical VaR / ES reference formulas.

Conventions:
- confidence_level is alpha, such as 0.95 or 0.99.
- quantile probability is 1 - alpha.
- quantiles use NumPy's linear interpolation method, matching the documented
  empirical lower-tail quantile convention used by the V1 project.
- NaN values are dropped before calculation.
- observations exactly at the quantile threshold are included in ES.
- VaR and ES are reported as positive losses with a zero floor.
"""

from __future__ import annotations

import numpy as np


def historical_var(returns: object, confidence_level: float) -> float:
    """Compute positive-loss Historical VaR from a return window."""

    clean = _clean_window(returns, confidence_level)
    threshold = _linear_quantile(clean, 1.0 - confidence_level)
    return max(0.0, -threshold)


def historical_expected_shortfall(returns: object, confidence_level: float) -> float:
    """Compute positive-loss Historical ES from a return window."""

    clean = _clean_window(returns, confidence_level)
    threshold = _linear_quantile(clean, 1.0 - confidence_level)
    tail_returns = clean[clean <= threshold]
    if tail_returns.size == 0:
        return historical_var(clean, confidence_level)
    return max(0.0, -float(np.mean(tail_returns)))


def _linear_quantile(values: np.ndarray, probability: float) -> float:
    try:
        return float(np.quantile(values, probability, method="linear"))
    except TypeError:
        return float(np.quantile(values, probability, interpolation="linear"))


def _clean_window(returns: object, confidence_level: float) -> np.ndarray:
    values = np.asarray(returns, dtype=float).reshape(-1)
    clean = values[np.isfinite(values)]
    if clean.size == 0:
        raise ValueError("Return window is empty.")
    if clean.size < 2:
        raise ValueError("Return window must contain at least 2 observations.")
    if not 0.0 < confidence_level < 1.0:
        raise ValueError("Confidence level must be between 0 and 1.")
    return clean
