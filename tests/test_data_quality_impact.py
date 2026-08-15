from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd
import yaml

from market_risk_toolkit.data_quality.impact import (
    CANONICAL_CONFIDENCE_LEVELS,
    CANONICAL_LAMBDA,
    CANONICAL_SEED_WINDOW,
    CANONICAL_WINDOW,
    build_returns_from_prices,
    impacted_forecast_dates,
    summarize_risk_impact,
)
from market_risk_toolkit.data_quality.perturbations import build_scenario_table

ROOT = Path(__file__).resolve().parents[1]


def _forecast_fixture(var_multiplier: float = 1.0) -> pd.DataFrame:
    rows = []
    for date in pd.date_range("2026-01-01", periods=3, freq="D"):
        for model_id in ("MR-001", "MR-002", "MR-003", "MR-004"):
            for confidence_level in (0.95, 0.99):
                rows.append(
                    {
                        "date": date.strftime("%Y-%m-%d"),
                        "model_id": model_id,
                        "confidence_level": confidence_level,
                        "var": 1.0 * var_multiplier,
                        "es": 1.5 * var_multiplier,
                        "realized_loss": 0.0,
                    }
                )
    return pd.DataFrame(rows)


def test_clean_corrupted_comparison_uses_identical_unaffected_configuration() -> None:
    clean = _forecast_fixture()
    corrupted = _forecast_fixture(var_multiplier=1.2)

    impact = summarize_risk_impact(
        clean_forecasts=clean,
        corrupted_forecasts=corrupted,
        impacted_dates=set(clean["date"]),
        scenario_id="DQ-X",
        scenario_name="Fixture",
        material_threshold=0.10,
        control_policy={
            "control_detected": True,
            "blocking_control_triggered": True,
            "risk_pipeline_allowed": False,
        },
    )

    assert set(impact["model_id"]) == {"MR-001", "MR-002", "MR-003", "MR-004"}
    assert set(impact["confidence_level"]) == {0.95, 0.99}
    assert impact["affected_forecast_count"].eq(3).all()


def test_materiality_threshold_is_unchanged_from_phase1() -> None:
    with (ROOT / "configs/validation/validation_plan.yaml").open() as file:
        plan = yaml.safe_load(file)

    assert plan["thresholds"]["data_quality_impact"]["material_relative_var_change"] == 0.10


def test_material_impact_boolean_is_calculated_correctly() -> None:
    clean = _forecast_fixture()
    corrupted = _forecast_fixture(var_multiplier=1.11)

    impact = summarize_risk_impact(
        clean_forecasts=clean,
        corrupted_forecasts=corrupted,
        impacted_dates=set(clean["date"]),
        scenario_id="DQ-X",
        scenario_name="Fixture",
        material_threshold=0.10,
        control_policy={
            "control_detected": True,
            "blocking_control_triggered": True,
            "risk_pipeline_allowed": False,
        },
    )

    assert impact["material_var_impact"].eq(True).all()
    assert np.isclose(impact["relative_var_change"], 0.11).all()


def test_generated_impact_artifact_includes_all_models_and_confidence_levels() -> None:
    impact = pd.read_csv(ROOT / "data/artifacts/data_quality_risk_impact.csv")

    assert set(impact["model_id"]) == {"MR-001", "MR-002", "MR-003", "MR-004"}
    assert set(impact["confidence_level"]) == set(CANONICAL_CONFIDENCE_LEVELS)
    assert set(impact["scenario_id"]) == {"DQ-01", "DQ-02", "DQ-03", "DQ-04", "DQ-05"}
    assert impact["risk_pipeline_allowed"].eq(False).all()


def test_no_scenario_is_selected_based_on_maximum_observed_impact() -> None:
    prices = pd.read_csv(ROOT / "data/processed/adjusted_close.csv", parse_dates=["date"]).set_index("date")
    scenarios = build_scenario_table(prices)

    assert scenarios["selection_rule"].str.contains("fixed-position").all()
    assert scenarios["selection_rule"].str.contains("not selected based on impact").all()


def test_impacted_forecast_dates_follow_changed_returns_window() -> None:
    index = pd.date_range("2026-01-01", periods=8, freq="D")
    clean = pd.Series([0.0] * 8, index=index)
    corrupted = clean.copy()
    corrupted.iloc[2] = 0.1

    impacted = impacted_forecast_dates(clean, corrupted, window=3)

    assert impacted == {
        index[3].strftime("%Y-%m-%d"),
        index[4].strftime("%Y-%m-%d"),
        index[5].strftime("%Y-%m-%d"),
    }


def test_returns_from_prices_does_not_mutate_prices() -> None:
    prices = pd.DataFrame(
        {"SPY": [100.0, 101.0], "QQQ": [200.0, 202.0], "TLT": [90.0, 91.0], "GLD": [50.0, 51.0]},
        index=pd.date_range("2026-01-01", periods=2),
    )
    original = prices.copy(deep=True)

    returns = build_returns_from_prices(prices)

    pd.testing.assert_frame_equal(prices, original)
    assert returns.shape == (1, 4)


def test_canonical_risk_configuration_is_phase4_configuration() -> None:
    assert CANONICAL_WINDOW == 250
    assert CANONICAL_LAMBDA == 0.94
    assert CANONICAL_SEED_WINDOW == 20
    assert CANONICAL_CONFIDENCE_LEVELS == (0.95, 0.99)


def test_phase6_impact_module_requires_no_network_access() -> None:
    source = (ROOT / "src/market_risk_toolkit/data_quality/impact.py").read_text()

    assert "yfinance" not in source
    assert "requests." not in source
