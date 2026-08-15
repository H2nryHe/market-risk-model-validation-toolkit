"""MR-004 Filtered Historical Simulation challenger."""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd

from market_risk_toolkit.risk.models.base import RiskForecast
from market_risk_toolkit.risk.models.ewma import _validate_parameters

MODEL_ID = "MR-004"
MODEL_NAME = "Filtered Historical Simulation VaR / ES"


@dataclass(frozen=True)
class FilteredHistoricalConfig:
    """Configuration for the FHS challenger."""

    model_id: str = MODEL_ID
    estimation_window: int = 250
    lambda_: float = 0.94
    seed_window: int = 20
    mean_assumption: str = "zero"
    confidence_levels: tuple[float, ...] = (0.95, 0.99)

    def validated(self) -> "FilteredHistoricalConfig":
        _validate_parameters(self.estimation_window, self.lambda_, self.seed_window)
        if self.mean_assumption != "zero":
            raise ValueError("FHS challenger currently supports only zero mean assumption.")
        return self


@dataclass(frozen=True)
class FHSResidualState:
    """Causal standardized residual pool and next-day volatility."""

    residuals: np.ndarray
    forecast_volatility: float


def build_filtered_residual_state(
    returns: pd.Series,
    *,
    lambda_: float = 0.94,
    seed_window: int = 20,
) -> FHSResidualState:
    """Build causal FHS residuals and next-day EWMA volatility.

    Seed observations initialize variance and are not included as standardized
    residuals. Each eligible residual uses volatility based only on returns
    available before that residual date.
    """

    clean = returns.dropna().astype(float).copy()
    _validate_parameters(len(clean), lambda_, seed_window)
    variance = float(clean.iloc[:seed_window].var(ddof=1))
    residuals: list[float] = []
    for value in clean.iloc[seed_window:]:
        sigma = float(np.sqrt(max(variance, 0.0)))
        residuals.append(0.0 if sigma == 0.0 else float(value) / sigma)
        variance = lambda_ * variance + (1.0 - lambda_) * float(value) ** 2
    return FHSResidualState(
        residuals=np.asarray(residuals, dtype=float),
        forecast_volatility=float(np.sqrt(max(variance, 0.0))),
    )


def forecast(
    returns: pd.Series,
    *,
    date: pd.Timestamp,
    confidence_level: float,
    config: FilteredHistoricalConfig,
) -> RiskForecast:
    """Forecast Filtered Historical Simulation VaR / ES."""

    normalized = config.validated()
    if not 0.0 < confidence_level < 1.0:
        raise ValueError("Confidence level must be between 0 and 1.")
    state = build_filtered_residual_state(
        returns,
        lambda_=normalized.lambda_,
        seed_window=normalized.seed_window,
    )
    probability = 1.0 - confidence_level
    residual_quantile = float(np.quantile(state.residuals, probability, method="linear"))
    tail_residuals = state.residuals[state.residuals <= residual_quantile]
    mean_tail_residual = residual_quantile if tail_residuals.size == 0 else float(np.mean(tail_residuals))
    var = max(0.0, -(state.forecast_volatility * residual_quantile))
    es = max(0.0, -(state.forecast_volatility * mean_tail_residual))
    return RiskForecast(
        model_id=normalized.model_id,
        model_name=MODEL_NAME,
        date=pd.Timestamp(date),
        confidence_level=float(confidence_level),
        var=float(var),
        es=float(es),
        forecast_volatility=state.forecast_volatility,
        estimation_window=normalized.estimation_window,
        method_parameters={
            "lambda": normalized.lambda_,
            "seed_window": normalized.seed_window,
            "mean_assumption": normalized.mean_assumption,
            "residual_pool_size": int(state.residuals.size),
        },
    )
