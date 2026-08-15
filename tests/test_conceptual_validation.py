from __future__ import annotations

import json

import numpy as np
import pandas as pd

from market_risk_toolkit.validation.conceptual import (
    analyze_distribution,
    build_conceptual_summary,
    classify_descriptive_regimes,
    compute_rolling_diagnostics,
    compute_tail_comparison,
)


def test_distribution_diagnostics_return_expected_fields() -> None:
    returns = pd.Series([0.01, -0.02, 0.005, 0.0, 0.03])

    diagnostics = analyze_distribution(returns)
    tail = compute_tail_comparison(returns)

    assert diagnostics["observation_count"] == 5
    assert "skewness" in diagnostics
    assert "excess_kurtosis" in diagnostics
    assert "jarque_bera_statistic" in diagnostics
    assert "jarque_bera_p_value" in diagnostics
    assert "empirical_1pct_return_quantile" in diagnostics
    assert "gaussian_1pct_return_quantile" in diagnostics
    assert "empirical_95_loss_quantile" in tail
    assert "gaussian_99_loss_quantile" in tail


def test_fixed_seed_gaussian_sample_has_near_zero_shape_diagnostics() -> None:
    rng = np.random.default_rng(123)
    returns = pd.Series(rng.normal(0.0, 1.0, size=20_000))

    diagnostics = analyze_distribution(returns)

    assert abs(float(diagnostics["skewness"])) < 0.05
    assert abs(float(diagnostics["excess_kurtosis"])) < 0.10


def test_heavy_tailed_fixture_has_higher_kurtosis_than_gaussian_fixture() -> None:
    rng = np.random.default_rng(123)
    gaussian = pd.Series(rng.normal(0.0, 1.0, size=10_000))
    heavy_tailed = pd.Series(rng.standard_t(df=3, size=10_000))

    gaussian_kurtosis = analyze_distribution(gaussian)["excess_kurtosis"]
    heavy_tailed_kurtosis = analyze_distribution(heavy_tailed)["excess_kurtosis"]

    assert heavy_tailed_kurtosis > gaussian_kurtosis


def test_negatively_skewed_fixture_has_negative_skewness() -> None:
    rng = np.random.default_rng(456)
    returns = pd.Series(-(rng.exponential(scale=1.0, size=5_000) - 1.0))

    diagnostics = analyze_distribution(returns)

    assert diagnostics["skewness"] < 0


def test_rolling_diagnostics_are_trailing_with_expected_first_valid_index() -> None:
    index = pd.date_range("2026-01-01", periods=5, freq="D")
    returns = pd.Series([1.0, 2.0, 3.0, 100.0, 200.0], index=index)

    rolling = compute_rolling_diagnostics(returns, window=3)

    assert rolling["rolling_volatility"].first_valid_index() == index[2]
    expected = pd.Series([1.0, 2.0, 3.0], index=index[:3]).std(ddof=1)
    assert rolling.loc[index[2], "rolling_volatility"] == expected


def test_future_observation_change_does_not_alter_earlier_rolling_values() -> None:
    index = pd.date_range("2026-01-01", periods=8, freq="D")
    returns = pd.Series(np.arange(8, dtype=float), index=index)
    perturbed = returns.copy(deep=True)
    perturbed.iloc[-1] = 10_000.0

    base = compute_rolling_diagnostics(returns, window=3)
    changed = compute_rolling_diagnostics(perturbed, window=3)

    pd.testing.assert_series_equal(
        base.loc[: index[-2], "rolling_volatility"],
        changed.loc[: index[-2], "rolling_volatility"],
    )
    pd.testing.assert_series_equal(
        base.loc[: index[-2], "rolling_skewness"],
        changed.loc[: index[-2], "rolling_skewness"],
    )


def test_regime_classification_labels_and_boundaries_are_deterministic() -> None:
    volatility = pd.Series([1.0, 2.0, 3.0, 4.0, 5.0])

    regimes, metadata = classify_descriptive_regimes(volatility)

    assert set(regimes) <= {"LOW_VOL", "NORMAL_VOL", "HIGH_VOL"}
    assert regimes.iloc[0] == "LOW_VOL"
    assert regimes.iloc[-1] == "HIGH_VOL"
    assert metadata["retrospective_descriptive"] is True


def test_input_series_is_not_mutated_by_rolling_diagnostics() -> None:
    returns = pd.Series([0.01, -0.02, 0.03, -0.01])
    original = returns.copy(deep=True)

    compute_rolling_diagnostics(returns, window=2)

    pd.testing.assert_series_equal(returns, original)


def test_summary_serialization_is_deterministic(tmp_path) -> None:
    index = pd.date_range("2026-01-01", periods=120, freq="D")
    values = np.sin(np.arange(120) / 5.0) / 100.0
    returns = pd.Series(values, index=index, name="portfolio_return")
    input_data_path = tmp_path / "returns.csv"
    returns.to_csv(input_data_path)

    summary_a, _, _, _ = build_conceptual_summary(
        returns,
        portfolio_name="test_portfolio",
        portfolio_weights={"SPY": 0.25, "QQQ": 0.25, "TLT": 0.25, "GLD": 0.25},
        input_data_path=str(input_data_path),
        rolling_window=20,
    )
    summary_b, _, _, _ = build_conceptual_summary(
        returns,
        portfolio_name="test_portfolio",
        portfolio_weights={"SPY": 0.25, "QQQ": 0.25, "TLT": 0.25, "GLD": 0.25},
        input_data_path=str(input_data_path),
        rolling_window=20,
    )

    assert json.dumps(summary_a, sort_keys=True) == json.dumps(summary_b, sort_keys=True)
    assert summary_a["final_validation_decision"] is None
