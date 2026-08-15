from __future__ import annotations

import numpy as np
import pandas as pd

from market_risk_toolkit.monitoring.metrics import (
    AMBER,
    GREEN,
    INSUFFICIENT_DATA,
    RED,
    aggregate_overall_status,
    aggregate_overall_status_v1_1,
    assign_challenger_divergence_status,
    assign_cluster_status,
    assign_dependence_watch_status,
    assign_exception_rate_status,
    assign_far_tail_performance_watch,
    assign_p_value_status,
    calculate_challenger_divergence,
    calculate_recent_exception_counts,
    calculate_rolling_exception_rate,
    calculate_rolling_p_values,
    calibrate_volatility_regime,
)


def test_rolling_exception_rate_is_trailing_and_requires_full_window() -> None:
    exceptions = pd.Series([0, 0, 1, 0, 1], index=pd.date_range("2026-01-01", periods=5))

    rates = calculate_rolling_exception_rate(exceptions, window=3)

    assert pd.isna(rates.iloc[0])
    assert pd.isna(rates.iloc[1])
    assert rates.iloc[2] == 1 / 3
    assert rates.iloc[3] == 1 / 3
    assert rates.iloc[4] == 2 / 3


def test_rolling_exception_rate_does_not_look_forward() -> None:
    index = pd.date_range("2026-01-01", periods=6)
    base = pd.Series([0, 0, 0, 0, 0, 0], index=index)
    perturbed_future = pd.Series([0, 0, 0, 0, 0, 1], index=index)

    base_rates = calculate_rolling_exception_rate(base, window=3)
    perturbed_rates = calculate_rolling_exception_rate(perturbed_future, window=3)

    pd.testing.assert_series_equal(base_rates.iloc[:5], perturbed_rates.iloc[:5])
    assert perturbed_rates.iloc[5] == 1 / 3


def test_exception_rate_status_boundaries_follow_multiplier_specification() -> None:
    assert (
        assign_exception_rate_status(
            0.0125,
            confidence_level=0.99,
            amber_multiplier=1.25,
            red_multiplier=1.50,
        )
        == GREEN
    )
    assert (
        assign_exception_rate_status(
            0.0125001,
            confidence_level=0.99,
            amber_multiplier=1.25,
            red_multiplier=1.50,
        )
        == AMBER
    )
    assert (
        assign_exception_rate_status(
            0.015,
            confidence_level=0.99,
            amber_multiplier=1.25,
            red_multiplier=1.50,
        )
        == AMBER
    )
    assert (
        assign_exception_rate_status(
            0.015001,
            confidence_level=0.99,
            amber_multiplier=1.25,
            red_multiplier=1.50,
        )
        == RED
    )


def test_p_value_status_boundaries_use_project_early_warning_band() -> None:
    assert assign_p_value_status(0.10, red_p_value=0.05, amber_p_value=0.10) == GREEN
    assert assign_p_value_status(0.0999, red_p_value=0.05, amber_p_value=0.10) == AMBER
    assert assign_p_value_status(0.05, red_p_value=0.05, amber_p_value=0.10) == AMBER
    assert assign_p_value_status(0.0499, red_p_value=0.05, amber_p_value=0.10) == RED
    assert assign_p_value_status(np.nan, red_p_value=0.05, amber_p_value=0.10) == INSUFFICIENT_DATA


def test_cluster_status_uses_recent_10_day_exception_counts() -> None:
    assert assign_cluster_status(0, amber_exception_count=2, red_exception_count=3) == GREEN
    assert assign_cluster_status(1, amber_exception_count=2, red_exception_count=3) == GREEN
    assert assign_cluster_status(2, amber_exception_count=2, red_exception_count=3) == AMBER
    assert assign_cluster_status(3, amber_exception_count=2, red_exception_count=3) == RED


def test_recent_exception_counts_are_causal_and_include_current_day() -> None:
    exceptions = pd.Series([0, 1, 0, 0, 1, 0], index=pd.date_range("2026-01-01", periods=6))

    recent = calculate_recent_exception_counts(exceptions)

    assert recent.iloc[0]["exceptions_last_5d"] == 0
    assert recent.iloc[1]["exceptions_last_5d"] == 1
    assert recent.iloc[4]["exceptions_last_5d"] == 2
    assert recent.iloc[4]["days_since_last_exception"] == 0
    assert recent.iloc[5]["days_since_last_exception"] == 1


def test_challenger_divergence_status_boundaries_are_unchanged_from_phase1() -> None:
    assert assign_challenger_divergence_status(0.1499, amber_threshold=0.15, red_threshold=0.25) == GREEN
    assert assign_challenger_divergence_status(0.15, amber_threshold=0.15, red_threshold=0.25) == AMBER
    assert assign_challenger_divergence_status(0.2499, amber_threshold=0.15, red_threshold=0.25) == AMBER
    assert assign_challenger_divergence_status(0.25, amber_threshold=0.15, red_threshold=0.25) == RED


def test_challenger_divergence_handles_near_zero_mr001_var_as_insufficient_data() -> None:
    index = pd.date_range("2026-01-01", periods=2)
    divergence = calculate_challenger_divergence(
        pd.Series([0.0, 1.0], index=index),
        pd.Series([0.5, 1.2], index=index),
    )

    assert pd.isna(divergence.iloc[0])
    assert np.isclose(divergence.iloc[1], 0.2)


def test_challenger_red_alone_creates_amber_review_not_far_tail_red() -> None:
    assert (
        assign_far_tail_performance_watch(
            exception_rate_status=GREEN,
            kupiec_status=GREEN,
            challenger_divergence_status=RED,
        )
        == AMBER
    )
    assert (
        aggregate_overall_status_v1_1(
            data_quality_status=GREEN,
            far_tail_performance_watch=AMBER,
            dependence_watch_status=GREEN,
            exception_rate_status=GREEN,
            kupiec_status=GREEN,
            challenger_review_required=True,
            high_vol_tail_escalation=False,
        )
        == AMBER
    )


def test_exception_rate_or_kupiec_red_forces_far_tail_performance_red() -> None:
    assert (
        assign_far_tail_performance_watch(
            exception_rate_status=RED,
            kupiec_status=GREEN,
            challenger_divergence_status=GREEN,
        )
        == RED
    )
    assert (
        assign_far_tail_performance_watch(
            exception_rate_status=GREEN,
            kupiec_status=RED,
            challenger_divergence_status=GREEN,
        )
        == RED
    )


def test_far_tail_watch_is_insufficient_until_performance_evidence_is_available() -> None:
    assert (
        assign_far_tail_performance_watch(
            exception_rate_status=INSUFFICIENT_DATA,
            kupiec_status=INSUFFICIENT_DATA,
            challenger_divergence_status=GREEN,
        )
        == INSUFFICIENT_DATA
    )


def test_dependence_watch_combines_conditional_coverage_and_clustering_context() -> None:
    assert (
        assign_dependence_watch_status(
            conditional_coverage_status=RED,
            cluster_status=GREEN,
        )
        == AMBER
    )
    assert (
        assign_dependence_watch_status(
            conditional_coverage_status=RED,
            cluster_status=AMBER,
        )
        == RED
    )
    assert (
        assign_dependence_watch_status(
            conditional_coverage_status=GREEN,
            cluster_status=RED,
        )
        == RED
    )
    assert (
        assign_dependence_watch_status(
            conditional_coverage_status=INSUFFICIENT_DATA,
            cluster_status=GREEN,
        )
        == INSUFFICIENT_DATA
    )


def test_v1_1_overall_status_precedence_preserves_hard_red_and_contextual_amber() -> None:
    assert (
        aggregate_overall_status_v1_1(
            data_quality_status="BLOCK",
            far_tail_performance_watch=GREEN,
            dependence_watch_status=GREEN,
            exception_rate_status=GREEN,
            kupiec_status=GREEN,
            challenger_review_required=False,
            high_vol_tail_escalation=False,
        )
        == RED
    )
    assert (
        aggregate_overall_status_v1_1(
            data_quality_status=GREEN,
            far_tail_performance_watch=RED,
            dependence_watch_status=GREEN,
            exception_rate_status=GREEN,
            kupiec_status=GREEN,
            challenger_review_required=False,
            high_vol_tail_escalation=False,
        )
        == RED
    )
    assert (
        aggregate_overall_status_v1_1(
            data_quality_status=GREEN,
            far_tail_performance_watch=GREEN,
            dependence_watch_status=RED,
            exception_rate_status=GREEN,
            kupiec_status=GREEN,
            challenger_review_required=False,
            high_vol_tail_escalation=False,
        )
        == RED
    )
    assert (
        aggregate_overall_status_v1_1(
            data_quality_status=GREEN,
            far_tail_performance_watch=GREEN,
            dependence_watch_status=GREEN,
            exception_rate_status=GREEN,
            kupiec_status=GREEN,
            challenger_review_required=True,
            high_vol_tail_escalation=False,
        )
        == AMBER
    )
    assert (
        aggregate_overall_status_v1_1(
            data_quality_status=GREEN,
            far_tail_performance_watch=GREEN,
            dependence_watch_status=GREEN,
            exception_rate_status=GREEN,
            kupiec_status=GREEN,
            challenger_review_required=False,
            high_vol_tail_escalation=True,
        )
        == AMBER
    )


def test_rolling_p_values_require_full_window_and_sparse_conditional_coverage_is_insufficient() -> None:
    index = pd.date_range("2026-01-01", periods=250)
    exceptions = pd.Series([0] * 249 + [1], index=index)

    p_values = calculate_rolling_p_values(
        exceptions,
        confidence_level=0.99,
        window=250,
        min_exception_count_for_dependence_test=5,
    )

    assert p_values.iloc[248]["kupiec_status"] == INSUFFICIENT_DATA
    assert p_values.iloc[249]["kupiec_status"] == ""
    assert not pd.isna(p_values.iloc[249]["kupiec_p_value_250"])
    assert p_values.iloc[249]["conditional_coverage_status"] == INSUFFICIENT_DATA
    assert pd.isna(p_values.iloc[249]["conditional_coverage_p_value_250"])


def test_conditional_coverage_is_evaluated_when_window_has_enough_exceptions_and_transitions() -> None:
    index = pd.date_range("2026-01-01", periods=250)
    values = [0] * 250
    for position in [10, 50, 100, 150, 200]:
        values[position] = 1
    exceptions = pd.Series(values, index=index)

    p_values = calculate_rolling_p_values(
        exceptions,
        confidence_level=0.99,
        window=250,
        min_exception_count_for_dependence_test=5,
    )

    assert p_values.iloc[-1]["conditional_coverage_status"] == ""
    assert not pd.isna(p_values.iloc[-1]["conditional_coverage_p_value_250"])


def test_volatility_regime_calibration_uses_first_valid_observations_not_full_sample() -> None:
    index = pd.date_range("2024-01-01", periods=700)
    returns = pd.Series(np.sin(np.arange(700) / 17) / 100 + np.arange(700) / 1_000_000, index=index)
    rolling = returns.rolling(window=60, min_periods=60).std(ddof=1)
    first_500 = rolling.dropna().iloc[:500]
    full_sample = rolling.dropna()

    regimes, calibration = calibrate_volatility_regime(
        returns,
        rolling_window=60,
        calibration_observations=500,
        lower_quantile=0.25,
        upper_quantile=0.75,
    )

    assert np.isclose(calibration.lower_threshold, first_500.quantile(0.25))
    assert np.isclose(calibration.upper_threshold, first_500.quantile(0.75))
    assert not np.isclose(calibration.lower_threshold, full_sample.quantile(0.25))
    assert not np.isclose(calibration.upper_threshold, full_sample.quantile(0.75))
    assert regimes.iloc[:59].eq(INSUFFICIENT_DATA).all()


def test_overall_status_precedence_includes_blocking_data_quality_gate() -> None:
    assert aggregate_overall_status([GREEN, GREEN], data_quality_status="BLOCK") == RED
    assert aggregate_overall_status([AMBER, RED], data_quality_status=GREEN) == RED
    assert aggregate_overall_status([GREEN, AMBER], data_quality_status=GREEN) == AMBER
    assert aggregate_overall_status([GREEN, INSUFFICIENT_DATA], data_quality_status=GREEN) == INSUFFICIENT_DATA
    assert aggregate_overall_status([GREEN, GREEN], data_quality_status=GREEN) == GREEN
