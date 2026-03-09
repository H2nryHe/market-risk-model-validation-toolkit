import numpy as np
import pandas as pd
import pytest

from market_risk_toolkit.validation.backtesting import (
    build_exceedance_table,
    christoffersen_conditional_coverage_test,
    christoffersen_independence_test,
    kupiec_unconditional_coverage,
    summarize_backtests,
)


def test_build_exceedance_table_compares_realized_loss_to_var() -> None:
    risk_table = pd.DataFrame(
        {
            "portfolio_return": [-0.02, 0.01, -0.03],
            "historical_var_95": [0.015, 0.015, 0.025],
            "parametric_var_95": [0.010, 0.020, 0.040],
            "historical_var_99": [0.030, 0.030, 0.030],
            "parametric_var_99": [0.025, 0.025, 0.025],
        },
        index=pd.to_datetime(["2024-01-02", "2024-01-03", "2024-01-04"]),
    )

    exceedance_table = build_exceedance_table(risk_table, confidence_levels=(0.95, 0.99))

    assert exceedance_table["realized_loss"].tolist() == [0.02, -0.01, 0.03]
    assert exceedance_table["historical_exceedance_95"].tolist() == [1, 0, 1]
    assert exceedance_table["parametric_exceedance_95"].tolist() == [1, 0, 0]
    assert exceedance_table["historical_exceedance_99"].tolist() == [0, 0, 0]
    assert exceedance_table["parametric_exceedance_99"].tolist() == [0, 0, 1]


def test_kupiec_test_is_near_zero_when_exception_rate_matches_nominal() -> None:
    exceedances = np.array([0] * 95 + [1] * 5)

    result = kupiec_unconditional_coverage(exceedances, 0.95)

    assert result.statistic == pytest.approx(0.0, abs=1e-10)
    assert result.p_value == pytest.approx(1.0, abs=1e-10)


def test_christoffersen_tests_detect_clustered_exceptions() -> None:
    clustered = np.array([0, 0, 0, 0, 1, 1, 1, 1, 0, 0, 0, 0, 1, 1, 1, 1])

    independence = christoffersen_independence_test(clustered)
    conditional = christoffersen_conditional_coverage_test(clustered, 0.95)

    assert independence.statistic > 0.0
    assert independence.p_value < 0.10
    assert conditional.statistic >= independence.statistic


def test_summarize_backtests_returns_model_comparison_rows() -> None:
    exceedance_table = pd.DataFrame(
        {
            "portfolio_return": [-0.01, -0.02, 0.01, -0.03, 0.00],
            "realized_loss": [0.01, 0.02, -0.01, 0.03, -0.0],
            "historical_var_95": [0.015] * 5,
            "parametric_var_95": [0.012] * 5,
            "historical_var_99": [0.025] * 5,
            "parametric_var_99": [0.020] * 5,
            "historical_exceedance_95": [0, 1, 0, 1, 0],
            "parametric_exceedance_95": [0, 1, 0, 1, 0],
            "historical_exceedance_99": [0, 0, 0, 1, 0],
            "parametric_exceedance_99": [0, 0, 0, 1, 0],
        },
        index=pd.date_range("2024-01-01", periods=5, freq="D"),
    )

    summary = summarize_backtests(exceedance_table, confidence_levels=(0.95, 0.99))

    assert len(summary) == 4
    assert set(summary["model"]) == {"historical", "parametric"}
    assert set(summary["confidence_level"]) == {0.95, 0.99}
    assert "interpretation" in summary.columns
