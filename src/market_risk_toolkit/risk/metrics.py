"""VaR and ES formulas used in the rolling market risk engine.

Historical estimates use the empirical left-tail of the rolling return window.
Parametric estimates assume returns are approximately Gaussian over the horizon.
That normality assumption is intentionally explicit because it will later matter
for backtesting and model validation.
"""

from __future__ import annotations

import pandas as pd
from scipy.stats import norm


def historical_var(returns: pd.Series, confidence_level: float) -> float:
    """Estimate one-period VaR using the empirical lower-tail quantile."""

    cleaned = _validate_window(returns, confidence_level)
    tail_quantile = float(cleaned.quantile(1.0 - confidence_level))
    return max(0.0, -tail_quantile)


def historical_es(returns: pd.Series, confidence_level: float) -> float:
    """Estimate one-period Expected Shortfall from the empirical tail average."""

    cleaned = _validate_window(returns, confidence_level)
    tail_quantile = float(cleaned.quantile(1.0 - confidence_level))
    tail_losses = cleaned[cleaned <= tail_quantile]
    if tail_losses.empty:
        return historical_var(cleaned, confidence_level)
    return max(0.0, -float(tail_losses.mean()))


def parametric_var(returns: pd.Series, confidence_level: float) -> float:
    """Estimate one-period Gaussian VaR from sample mean and volatility."""

    cleaned = _validate_window(returns, confidence_level)
    mean = float(cleaned.mean())
    volatility = float(cleaned.std(ddof=1))
    z_score = float(norm.ppf(1.0 - confidence_level))
    return max(0.0, -(mean + volatility * z_score))


def parametric_es(returns: pd.Series, confidence_level: float) -> float:
    """Estimate one-period Gaussian Expected Shortfall.

    Under normal returns, the expected tail return below the VaR cutoff is:
    mu - sigma * phi(z) / (1 - alpha), where z = Phi^-1(1 - alpha).
    We negate that tail return so the result is reported as a positive loss.
    """

    cleaned = _validate_window(returns, confidence_level)
    mean = float(cleaned.mean())
    volatility = float(cleaned.std(ddof=1))
    z_score = float(norm.ppf(1.0 - confidence_level))
    tail_mean = mean - volatility * norm.pdf(z_score) / (1.0 - confidence_level)
    return max(0.0, -tail_mean)


def compute_rolling_risk_metrics(
    returns: pd.Series,
    window: int = 250,
    confidence_levels: tuple[float, ...] = (0.95, 0.99),
) -> pd.DataFrame:
    """Compute rolling historical and Gaussian VaR/ES estimates.

    The returned table keeps the realized portfolio return alongside the risk
    forecasts so downstream backtesting can compare realized next-day losses to
    prior-day model estimates without reshaping again.
    """

    if window < 2:
        raise ValueError("Rolling window must be at least 2 observations.")

    cleaned = returns.dropna().copy()
    cleaned.index.name = "date"
    records: list[dict[str, float | pd.Timestamp]] = []

    for end in range(window, len(cleaned)):
        window_returns = cleaned.iloc[end - window : end]
        record: dict[str, float | pd.Timestamp] = {
            "date": cleaned.index[end],
            "portfolio_return": float(cleaned.iloc[end]),
        }
        for level in confidence_levels:
            suffix = _format_confidence_level(level)
            record[f"historical_var_{suffix}"] = historical_var(window_returns, level)
            record[f"historical_es_{suffix}"] = historical_es(window_returns, level)
            record[f"parametric_var_{suffix}"] = parametric_var(window_returns, level)
            record[f"parametric_es_{suffix}"] = parametric_es(window_returns, level)
        records.append(record)

    frame = pd.DataFrame.from_records(records)
    frame["date"] = pd.to_datetime(frame["date"])
    frame = frame.set_index("date").sort_index()
    return frame


def _validate_window(returns: pd.Series, confidence_level: float) -> pd.Series:
    cleaned = returns.dropna().astype(float)
    if cleaned.empty:
        raise ValueError("Return window is empty.")
    if len(cleaned) < 2:
        raise ValueError("Return window must contain at least 2 observations.")
    if not 0.0 < confidence_level < 1.0:
        raise ValueError("Confidence level must be between 0 and 1.")
    return cleaned


def _format_confidence_level(confidence_level: float) -> str:
    return str(int(round(confidence_level * 100)))
