"""Independent Gaussian VaR / ES reference formulas.

Conventions:
- confidence_level is alpha, such as 0.95 or 0.99.
- NaN values are dropped before calculation.
- sample volatility uses ddof = 1.
- VaR and ES are reported as positive losses with a zero floor.
- lower-tail return probability is 1 - alpha.
"""

from __future__ import annotations

import numpy as np
from scipy.stats import norm


def gaussian_var(returns: object, confidence_level: float) -> float:
    """Compute positive-loss Gaussian VaR from a return window."""

    clean = _clean_window(returns, confidence_level)
    mean = float(np.mean(clean))
    volatility = float(np.std(clean, ddof=1))
    z_score = float(norm.ppf(1.0 - confidence_level))
    lower_tail_quantile = mean + volatility * z_score
    return max(0.0, -lower_tail_quantile)


def gaussian_expected_shortfall(returns: object, confidence_level: float) -> float:
    """Compute positive-loss Gaussian Expected Shortfall from a return window."""

    clean = _clean_window(returns, confidence_level)
    mean = float(np.mean(clean))
    volatility = float(np.std(clean, ddof=1))
    tail_probability = 1.0 - confidence_level
    z_score = float(norm.ppf(tail_probability))
    conditional_lower_tail_return = mean - volatility * float(norm.pdf(z_score)) / tail_probability
    return max(0.0, -conditional_lower_tail_return)


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
