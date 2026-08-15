"""MR-002 Historical Simulation wrapper preserving the V1 implementation."""

from __future__ import annotations

import pandas as pd

from market_risk_toolkit.risk.metrics import historical_es, historical_var
from market_risk_toolkit.risk.models.base import RiskForecast

MODEL_ID = "MR-002"
MODEL_NAME = "Historical Simulation VaR / ES"


def forecast(
    returns: pd.Series,
    *,
    date: pd.Timestamp,
    confidence_level: float,
    estimation_window: int,
) -> RiskForecast:
    """Forecast Historical VaR / ES by calling the existing V1 formulas."""

    clean = returns.dropna().astype(float)
    return RiskForecast(
        model_id=MODEL_ID,
        model_name=MODEL_NAME,
        date=pd.Timestamp(date),
        confidence_level=float(confidence_level),
        var=float(historical_var(clean, confidence_level)),
        es=float(historical_es(clean, confidence_level)),
        estimation_window=int(estimation_window),
        method_parameters={"quantile_probability": 1.0 - float(confidence_level)},
    )
