from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pandas as pd

from market_risk_toolkit.validation.sensitivity import (
    DEFAULT_LAMBDA,
    LAMBDA_GRID,
    PORTFOLIO_VARIANTS,
    SENSITIVITY_CONFIDENCE_LEVELS,
    WINDOW_GRID,
    build_portfolio_returns,
    common_date_intersection,
    effective_empirical_tail_observation_count,
    validate_predeclared_portfolios,
)

ROOT = Path(__file__).resolve().parents[1]


def test_sensitivity_windows_and_confidence_levels_are_predeclared() -> None:
    assert WINDOW_GRID == (125, 250, 500)
    assert SENSITIVITY_CONFIDENCE_LEVELS == (0.95, 0.975, 0.99)


def test_ewma_lambda_grid_includes_default_without_changing_canonical_default() -> None:
    assert LAMBDA_GRID == (0.94, 0.97, 0.99)
    assert DEFAULT_LAMBDA == 0.94


def test_portfolio_weights_sum_to_one_and_are_not_optimized() -> None:
    portfolios = validate_predeclared_portfolios()

    assert set(portfolios["portfolio_id"]) == {
        "equal_weight",
        "equity_heavy",
        "rates_heavy",
        "diversified_balanced",
    }
    assert np.allclose(portfolios["weight_sum"], 1.0)
    assert portfolios["optimized_after_results"].eq(False).all()
    assert all(np.isclose(sum(weights.values()), 1.0) for weights in PORTFOLIO_VARIANTS.values())


def test_common_sensitivity_sample_is_date_intersection_across_windows() -> None:
    frames = {
        125: pd.DataFrame({"date": ["2026-01-01", "2026-01-02", "2026-01-03"]}),
        250: pd.DataFrame({"date": ["2026-01-02", "2026-01-03"]}),
        500: pd.DataFrame({"date": ["2026-01-03", "2026-01-04"]}),
    }

    assert common_date_intersection(frames) == {"2026-01-03"}


def test_native_and_common_samples_are_distinguishable_in_generated_artifact() -> None:
    results = pd.read_csv(ROOT / "data/artifacts/sensitivity_results.csv")
    lookback = results[results["analysis_dimension"].eq("lookback_window")]

    assert {"native_sample", "common_sensitivity_sample"}.issubset(set(lookback["sample_type"]))
    native_counts = set(lookback[lookback["sample_type"].eq("native_sample")]["observation_count"])
    common_counts = set(lookback[lookback["sample_type"].eq("common_sensitivity_sample")]["observation_count"])
    assert native_counts != common_counts


def test_effective_tail_counts_and_warnings_are_deterministic() -> None:
    assert np.isclose(
        effective_empirical_tail_observation_count("MR-002", window=125, confidence_level=0.99),
        1.25,
    )
    assert np.isclose(
        effective_empirical_tail_observation_count("MR-004", window=125, confidence_level=0.975),
        2.625,
    )
    assert effective_empirical_tail_observation_count("MR-001", window=125, confidence_level=0.99) is None

    results = pd.read_csv(ROOT / "data/artifacts/sensitivity_results.csv")
    limited = results[
        results["effective_tail_observation_count"].notna()
        & (results["effective_tail_observation_count"] < 5.0)
    ]
    assert not limited.empty
    assert set(limited["tail_sample_warning"]) == {"TAIL_SAMPLE_LIMITED"}


def test_every_predeclared_sensitivity_configuration_is_retained() -> None:
    results = pd.read_csv(ROOT / "data/artifacts/sensitivity_results.csv")

    expected_rows = (
        len(WINDOW_GRID) * 4 * len(SENSITIVITY_CONFIDENCE_LEVELS) * 2
        + len(LAMBDA_GRID) * 2 * len(SENSITIVITY_CONFIDENCE_LEVELS)
        + len(PORTFOLIO_VARIANTS) * 4 * 2
    )
    assert len(results) == expected_rows
    assert results["configuration_retained"].eq(True).all()
    assert set(results["window"]).issuperset(WINDOW_GRID)
    assert set(results["confidence_level"]).issuperset(SENSITIVITY_CONFIDENCE_LEVELS)


def test_portfolio_return_builder_does_not_mutate_input_returns() -> None:
    asset_returns = pd.DataFrame(
        {
            "SPY": [0.01, 0.02],
            "QQQ": [0.03, 0.04],
            "TLT": [0.00, 0.01],
            "GLD": [-0.01, 0.02],
        },
        index=pd.date_range("2026-01-01", periods=2),
    )
    original = asset_returns.copy(deep=True)

    portfolio = build_portfolio_returns(asset_returns, PORTFOLIO_VARIANTS["equal_weight"])

    pd.testing.assert_frame_equal(asset_returns, original)
    assert np.isclose(portfolio.iloc[0], 0.0075)


def test_phase5_sensitivity_module_requires_no_network_data_refresh() -> None:
    source = (ROOT / "src/market_risk_toolkit/validation/sensitivity.py").read_text()

    assert "yfinance" not in source
    assert "requests." not in source


def test_phase5_creates_no_formal_findings_or_final_decision() -> None:
    summary = json.loads((ROOT / "data/artifacts/sensitivity_summary.json").read_text())

    assert summary["formal_findings_created"] is False
    assert summary["final_validation_decision"] is None
    assert "final validation decision" in (ROOT / "reports/sections/outcomes_and_stability.md").read_text().lower()
    if (ROOT / "governance/findings.csv").exists():
        assert "phase 6" in (ROOT / "reports/sections/data_quality_and_findings.md").read_text().lower()
