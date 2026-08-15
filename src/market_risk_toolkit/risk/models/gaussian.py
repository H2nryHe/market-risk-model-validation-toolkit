"""MR-001 Gaussian model wrapper preserving the V1 implementation."""

from __future__ import annotations

import pandas as pd

from market_risk_toolkit.risk.metrics import parametric_es, parametric_var
from market_risk_toolkit.risk.models.base import RiskForecast

MODEL_ID = "MR-001"
MODEL_NAME = "Gaussian Parametric VaR / ES"


def forecast(
    returns: pd.Series,
    *,
    date: pd.Timestamp,
    confidence_level: float,
    estimation_window: int,
) -> RiskForecast:
    """Forecast Gaussian VaR / ES by calling the existing V1 formulas."""

    clean = returns.dropna().astype(float)
    return RiskForecast(
        model_id=MODEL_ID,
        model_name=MODEL_NAME,
        date=pd.Timestamp(date),
        confidence_level=float(confidence_level),
        var=float(parametric_var(clean, confidence_level)),
        es=float(parametric_es(clean, confidence_level)),
        forecast_volatility=float(clean.std(ddof=1)),
        estimation_window=int(estimation_window),
        method_parameters={"mean_assumption": "sample_mean", "volatility_ddof": 1},
    )
