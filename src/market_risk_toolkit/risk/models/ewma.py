"""MR-003 EWMA Gaussian VaR / ES challenger."""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd
from scipy.stats import norm

from market_risk_toolkit.risk.models.base import RiskForecast

MODEL_ID = "MR-003"
MODEL_NAME = "EWMA Gaussian VaR / ES"


@dataclass(frozen=True)
class EWMAModelConfig:
    """Configuration for the EWMA Gaussian challenger."""

    model_id: str = MODEL_ID
    estimation_window: int = 250
    lambda_: float = 0.94
    seed_window: int = 20
    mean_assumption: str = "zero"
    confidence_levels: tuple[float, ...] = (0.95, 0.99)

    def validated(self) -> "EWMAModelConfig":
        _validate_parameters(self.estimation_window, self.lambda_, self.seed_window)
        if self.mean_assumption != "zero":
            raise ValueError("EWMA challenger currently supports only zero mean assumption.")
        return self


def ewma_forecast_variance(
    returns: pd.Series,
    *,
    lambda_: float = 0.94,
    seed_window: int = 20,
) -> float:
    """Forecast next-day EWMA variance from an observed return window.

    The first `seed_window` observations initialize sample variance using
    `ddof=1`. Each subsequent observed return updates variance with
    lambda * sigma_current^2 + (1 - lambda) * r_previous^2. The resulting
    variance is the forecast variance for the next day.
    """

    clean = returns.dropna().astype(float).copy()
    _validate_parameters(len(clean), lambda_, seed_window)
    variance = float(clean.iloc[:seed_window].var(ddof=1))
    for value in clean.iloc[seed_window:]:
        variance = lambda_ * variance + (1.0 - lambda_) * float(value) ** 2
    return max(0.0, float(variance))


def forecast(
    returns: pd.Series,
    *,
    date: pd.Timestamp,
    confidence_level: float,
    config: EWMAModelConfig,
) -> RiskForecast:
    """Forecast EWMA Gaussian VaR / ES with zero conditional mean."""

    normalized = config.validated()
    if not 0.0 < confidence_level < 1.0:
        raise ValueError("Confidence level must be between 0 and 1.")
    variance = ewma_forecast_variance(
        returns,
        lambda_=normalized.lambda_,
        seed_window=normalized.seed_window,
    )
    sigma = float(np.sqrt(variance))
    z_score = float(norm.ppf(1.0 - confidence_level))
    var = max(0.0, -(sigma * z_score))
    es = max(0.0, sigma * float(norm.pdf(z_score)) / (1.0 - confidence_level))
    return RiskForecast(
        model_id=normalized.model_id,
        model_name=MODEL_NAME,
        date=pd.Timestamp(date),
        confidence_level=float(confidence_level),
        var=float(var),
        es=float(es),
        forecast_volatility=sigma,
        estimation_window=normalized.estimation_window,
        method_parameters={
            "lambda": normalized.lambda_,
            "seed_window": normalized.seed_window,
            "mean_assumption": normalized.mean_assumption,
        },
    )


def _validate_parameters(estimation_window: int, lambda_: float, seed_window: int) -> None:
    if not 0.0 < lambda_ < 1.0:
        raise ValueError("EWMA lambda must be between 0 and 1.")
    if seed_window < 2:
        raise ValueError("EWMA seed_window must be at least 2 observations.")
    if seed_window >= estimation_window:
        raise ValueError("EWMA seed_window must be smaller than the estimation window.")
