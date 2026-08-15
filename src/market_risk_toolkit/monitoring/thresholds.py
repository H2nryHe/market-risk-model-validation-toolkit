"""Monitoring threshold configuration."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml


@dataclass(frozen=True)
class MonitoringThresholds:
    threshold_version: str
    effective_date: str
    project_disclaimer: str
    exception_short_window: int
    exception_long_window: int
    statistical_window: int
    exception_rate_amber_multiplier: float
    exception_rate_red_multiplier: float
    statistical_red_p_value: float
    statistical_amber_p_value: float
    min_exception_count_for_dependence_test: int
    cluster_lookback_days: int
    cluster_amber_exception_count: int
    cluster_red_exception_count: int
    challenger_amber_relative_difference: float
    challenger_red_relative_difference: float
    volatility_window: int
    volatility_calibration_observations: int
    volatility_lower_quantile: float
    volatility_upper_quantile: float
    stale_price_threshold: int
    extreme_return_threshold: float
    raw_config: dict[str, Any]


def load_monitoring_thresholds(
    path: str | Path = "configs/monitoring/thresholds.yaml",
) -> MonitoringThresholds:
    """Load Phase 7 monitoring thresholds."""

    with Path(path).open("r", encoding="utf-8") as file:
        payload = yaml.safe_load(file) or {}
    return MonitoringThresholds(
        threshold_version=str(payload["threshold_version"]),
        effective_date=str(payload["effective_date"]),
        project_disclaimer=str(payload["project_disclaimer"]),
        exception_short_window=int(payload["rolling_windows"]["exception_short"]),
        exception_long_window=int(payload["rolling_windows"]["exception_long"]),
        statistical_window=int(payload["rolling_windows"]["statistical"]),
        exception_rate_amber_multiplier=float(payload["exception_rate"]["multiplier_amber"]),
        exception_rate_red_multiplier=float(payload["exception_rate"]["multiplier_red"]),
        statistical_red_p_value=float(payload["statistical_tests"]["red_p_value"]),
        statistical_amber_p_value=float(payload["statistical_tests"]["amber_p_value"]),
        min_exception_count_for_dependence_test=int(
            payload["statistical_tests"]["min_exception_count_for_dependence_test"]
        ),
        cluster_lookback_days=int(payload["recent_cluster"]["lookback_days"]),
        cluster_amber_exception_count=int(payload["recent_cluster"]["amber_exception_count"]),
        cluster_red_exception_count=int(payload["recent_cluster"]["red_exception_count"]),
        challenger_amber_relative_difference=float(
            payload["challenger_divergence"]["amber_relative_difference"]
        ),
        challenger_red_relative_difference=float(payload["challenger_divergence"]["red_relative_difference"]),
        volatility_window=int(payload["volatility_regime"]["rolling_window"]),
        volatility_calibration_observations=int(payload["volatility_regime"]["calibration_observations"]),
        volatility_lower_quantile=float(payload["volatility_regime"]["lower_quantile"]),
        volatility_upper_quantile=float(payload["volatility_regime"]["upper_quantile"]),
        stale_price_threshold=int(payload["data_quality"]["staleness_consecutive_unchanged_threshold"]),
        extreme_return_threshold=float(payload["data_quality"]["extreme_return_threshold"]),
        raw_config=payload,
    )
