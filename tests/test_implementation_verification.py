from __future__ import annotations

import math

import numpy as np
import pandas as pd
import pytest
from scipy.stats import norm

from market_risk_toolkit.risk.metrics import (
    parametric_es,
    parametric_var,
)
from market_risk_toolkit.validation.implementation_verification import (
    COMPARISON_COLUMNS,
    build_frozen_portfolio_window_cases,
    build_hand_checkable_cases,
    check_independent_imports,
    compare_implementations,
)
from market_risk_toolkit.validation.independent.gaussian_reference import (
    gaussian_expected_shortfall,
    gaussian_var,
)
from market_risk_toolkit.validation.independent.historical_reference import (
    historical_expected_shortfall,
    historical_var,
)


def test_gaussian_var_reference_on_deterministic_fixture() -> None:
    returns = pd.Series([-0.02, -0.01, 0.0, 0.01, 0.02])
    mean = float(np.mean(returns))
    volatility = float(np.std(returns, ddof=1))
    expected = max(0.0, -(mean + volatility * float(norm.ppf(0.05))))

    assert gaussian_var(returns, 0.95) == pytest.approx(expected)


def test_gaussian_es_reference_on_deterministic_fixture() -> None:
    returns = pd.Series([-0.02, -0.01, 0.0, 0.01, 0.02])
    mean = float(np.mean(returns))
    volatility = float(np.std(returns, ddof=1))
    z_score = float(norm.ppf(0.05))
    expected = max(0.0, -(mean - volatility * float(norm.pdf(z_score)) / 0.05))

    assert gaussian_expected_shortfall(returns, 0.95) == pytest.approx(expected)


def test_historical_var_reference_on_deterministic_fixture() -> None:
    returns = pd.Series([-0.10, -0.05] + [0.0] * 19)

    assert historical_var(returns, 0.95) == pytest.approx(0.05)


def test_historical_es_reference_on_deterministic_fixture() -> None:
    returns = pd.Series([-0.10, -0.05] + [0.0] * 19)

    assert historical_expected_shortfall(returns, 0.95) == pytest.approx(0.075)


def test_nan_handling_matches_drop_nan_convention() -> None:
    with_nan = pd.Series([-0.02, np.nan, 0.0, 0.02])
    without_nan = pd.Series([-0.02, 0.0, 0.02])

    assert gaussian_var(with_nan, 0.95) == pytest.approx(gaussian_var(without_nan, 0.95))
    assert historical_expected_shortfall(with_nan, 0.95) == pytest.approx(
        historical_expected_shortfall(without_nan, 0.95)
    )


def test_positive_loss_sign_convention_and_near_zero_values() -> None:
    positive_returns = pd.Series([0.01, 0.01, 0.01, 0.01])

    assert gaussian_var(positive_returns, 0.95) == pytest.approx(0.0)
    assert historical_var(positive_returns, 0.95) == pytest.approx(0.0)
    assert historical_expected_shortfall(positive_returns, 0.95) == pytest.approx(0.0)


def test_sample_standard_deviation_uses_ddof_one() -> None:
    returns = pd.Series([-0.03, -0.01, 0.01, 0.03])
    mean = float(np.mean(returns))
    expected_ddof_one = max(0.0, -(mean + float(np.std(returns, ddof=1)) * norm.ppf(0.05)))
    expected_ddof_zero = max(0.0, -(mean + float(np.std(returns, ddof=0)) * norm.ppf(0.05)))

    assert gaussian_var(returns, 0.95) == pytest.approx(expected_ddof_one)
    assert not math.isclose(gaussian_var(returns, 0.95), expected_ddof_zero)


def test_quantile_convention_is_linear_and_reproducible() -> None:
    returns = pd.Series([-0.10, -0.05, 0.0, 0.05, 0.10])
    expected_threshold = float(np.quantile(returns.to_numpy(), 0.05, method="linear"))

    assert historical_var(returns, 0.95) == pytest.approx(max(0.0, -expected_threshold))


def test_independent_reference_modules_do_not_import_forbidden_developer_modules() -> None:
    result = check_independent_imports()

    assert result["passed"] is True
    assert result["violations"] == []


def test_developer_vs_reference_match_on_fixed_synthetic_window_at_95_and_99() -> None:
    rng = np.random.default_rng(42)
    case = build_hand_checkable_cases()[0]
    synthetic = case.__class__(
        case_id="synthetic_match",
        case_type="synthetic",
        date_or_fixture="fixed_rng",
        returns=pd.Series(rng.normal(0.0, 0.01, size=300)),
    )

    comparison = compare_implementations([synthetic], (0.95, 0.99), tolerance=1.0e-10)

    assert set(comparison["confidence_level"]) == {0.95, 0.99}
    assert comparison["match"].all()


def test_frozen_portfolio_verification_cases_are_deterministic() -> None:
    index = pd.date_range("2020-01-01", periods=320, freq="D")
    returns = pd.Series(np.arange(320, dtype=float) / 10_000, index=index)

    first = build_frozen_portfolio_window_cases(returns, window=50, count=5)
    second = build_frozen_portfolio_window_cases(returns, window=50, count=5)

    assert [case.date_or_fixture for case in first] == [case.date_or_fixture for case in second]
    assert [case.case_id for case in first] == [
        "frozen_window_01",
        "frozen_window_02",
        "frozen_window_03",
        "frozen_window_04",
        "frozen_window_05",
    ]


def test_input_series_objects_are_not_mutated_by_comparison() -> None:
    case = build_hand_checkable_cases()[0]
    original = case.returns.copy(deep=True)

    compare_implementations([case], (0.95,), tolerance=1.0e-10)

    pd.testing.assert_series_equal(case.returns, original)


def test_implementation_comparison_output_schema_is_deterministic() -> None:
    comparison = compare_implementations([build_hand_checkable_cases()[0]], (0.95,), 1.0e-10)

    assert list(comparison.columns) == COMPARISON_COLUMNS
    assert len(comparison) == 4
    assert comparison["match"].all()


@pytest.mark.parametrize(
    "values",
    [
        [],
        [0.01],
    ],
)
def test_reference_rejects_empty_or_one_observation_windows(values: list[float]) -> None:
    with pytest.raises(ValueError):
        gaussian_var(pd.Series(values), 0.95)
    with pytest.raises(ValueError):
        historical_var(pd.Series(values), 0.95)


def test_reference_rejects_invalid_confidence_level() -> None:
    returns = pd.Series([-0.01, 0.01])

    with pytest.raises(ValueError):
        gaussian_expected_shortfall(returns, 1.0)
    with pytest.raises(ValueError):
        historical_expected_shortfall(returns, 0.0)


def test_extreme_finite_observations_are_handled() -> None:
    returns = pd.Series([-1.0e6, -0.01, 0.0, 0.02, 1.0e6])

    assert math.isfinite(gaussian_var(returns, 0.99))
    assert math.isfinite(gaussian_expected_shortfall(returns, 0.99))
    assert math.isfinite(historical_var(returns, 0.99))
    assert math.isfinite(historical_expected_shortfall(returns, 0.99))


def test_developer_gaussian_functions_match_reference_without_modifying_developer_code() -> None:
    returns = pd.Series([-0.02, -0.01, 0.0, 0.01, 0.02])

    assert parametric_var(returns, 0.99) == pytest.approx(gaussian_var(returns, 0.99))
    assert parametric_es(returns, 0.99) == pytest.approx(
        gaussian_expected_shortfall(returns, 0.99)
    )
