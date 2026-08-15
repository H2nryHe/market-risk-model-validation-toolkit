from __future__ import annotations

import csv
from pathlib import Path

import numpy as np
import pandas as pd
import yaml

from market_risk_toolkit.risk.models import EWMAModelConfig, FilteredHistoricalConfig
from market_risk_toolkit.validation.benchmarking import (
    MODEL_ORDER,
    build_challenger_divergence,
    build_model_comparison,
    build_unified_forecasts,
    filter_common_comparison_sample,
)

ROOT = Path(__file__).resolve().parents[1]


def test_fixed_model_config_is_parsed_deterministically_and_lambda_is_not_tuned() -> None:
    with (ROOT / "configs/models/ewma_var.yaml").open() as file:
        ewma = yaml.safe_load(file)
    with (ROOT / "configs/models/filtered_historical.yaml").open() as file:
        fhs = yaml.safe_load(file)

    assert ewma["model_id"] == "MR-003"
    assert ewma["lambda"] == 0.94
    assert ewma["confidence_levels"] == [0.95, 0.99]
    assert fhs["model_id"] == "MR-004"
    assert fhs["lambda"] == 0.94
    assert "0.97" not in str(ewma)
    assert "0.99" not in str(ewma["lambda"])


def test_unified_forecast_table_contains_all_models_and_confidence_levels() -> None:
    returns = pd.Series(
        np.sin(np.arange(90)) / 100.0,
        index=pd.date_range("2025-01-01", periods=90, freq="D"),
        name="portfolio_return",
    )

    forecasts = build_unified_forecasts(
        returns=returns,
        confidence_levels=(0.95, 0.99),
        estimation_window=50,
        ewma_config=EWMAModelConfig(estimation_window=50, seed_window=10),
        fhs_config=FilteredHistoricalConfig(estimation_window=50, seed_window=10),
    )

    assert set(forecasts["model_id"]) == set(MODEL_ORDER)
    assert set(forecasts["confidence_level"]) == {0.95, 0.99}
    assert {"date", "var", "es", "realized_return", "realized_loss"}.issubset(forecasts.columns)


def test_common_comparison_sample_uses_one_date_intersection() -> None:
    returns = pd.Series(
        np.cos(np.arange(95)) / 100.0,
        index=pd.date_range("2025-01-01", periods=95, freq="D"),
    )
    forecasts = build_unified_forecasts(
        returns=returns,
        confidence_levels=(0.95, 0.99),
        estimation_window=50,
        ewma_config=EWMAModelConfig(estimation_window=50, seed_window=10),
        fhs_config=FilteredHistoricalConfig(estimation_window=50, seed_window=10),
    )

    common = filter_common_comparison_sample(forecasts)
    counts = common.groupby(["date", "confidence_level"])["model_id"].nunique()

    assert (counts == 4).all()
    assert common["date"].nunique() == len(returns) - 50


def test_backtesting_model_comparison_is_deterministic() -> None:
    returns = pd.Series(
        np.sin(np.arange(120)) / 100.0,
        index=pd.date_range("2025-01-01", periods=120, freq="D"),
    )
    forecasts = filter_common_comparison_sample(
        build_unified_forecasts(
            returns=returns,
            confidence_levels=(0.95, 0.99),
            estimation_window=60,
            ewma_config=EWMAModelConfig(estimation_window=60, seed_window=10),
            fhs_config=FilteredHistoricalConfig(estimation_window=60, seed_window=10),
        )
    )

    first = build_model_comparison(forecasts, (0.95, 0.99))
    second = build_model_comparison(forecasts, (0.95, 0.99))

    pd.testing.assert_frame_equal(first, second)
    assert set(first["model_id"]) == set(MODEL_ORDER)


def test_challenger_divergence_uses_phase_one_thresholds() -> None:
    rows = []
    for date in pd.date_range("2025-01-01", periods=3, freq="D"):
        for confidence_level in (0.95,):
            rows.extend(
                [
                    {"date": str(date.date()), "confidence_level": confidence_level, "model_id": "MR-001", "var": 1.0},
                    {"date": str(date.date()), "confidence_level": confidence_level, "model_id": "MR-002", "var": 1.10},
                    {"date": str(date.date()), "confidence_level": confidence_level, "model_id": "MR-003", "var": 1.20},
                    {"date": str(date.date()), "confidence_level": confidence_level, "model_id": "MR-004", "var": 1.30},
                ]
            )
    forecasts = pd.DataFrame(rows)

    divergence = build_challenger_divergence(
        forecasts,
        amber_threshold=0.15,
        red_threshold=0.25,
    )

    assert set(divergence["amber_threshold"]) == {0.15}
    assert set(divergence["red_threshold"]) == {0.25}
    assert "not regulatory limits" in " ".join(divergence["threshold_interpretation"])


def test_model_inventory_records_implemented_challengers_not_validated() -> None:
    with (ROOT / "governance/model_inventory.csv").open(newline="") as file:
        rows = {row["model_id"]: row for row in csv.DictReader(file)}

    for model_id in ("MR-003", "MR-004"):
        assert rows[model_id]["model_type"] == "implemented_challenger"
        assert "implemented challenger" in rows[model_id]["status"]
        assert rows[model_id]["validation_status"] == "pending V2 validation"
        assert rows[model_id]["validation_status"] != "validated"
