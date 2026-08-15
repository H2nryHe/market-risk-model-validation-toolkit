"""Lightweight forecast structures for risk models."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

import pandas as pd


@dataclass(frozen=True)
class RiskForecast:
    """One model forecast for one date and confidence level."""

    model_id: str
    model_name: str
    date: pd.Timestamp
    confidence_level: float
    var: float
    es: float
    forecast_volatility: float | None = None
    estimation_window: int | None = None
    method_parameters: dict[str, Any] = field(default_factory=dict)
