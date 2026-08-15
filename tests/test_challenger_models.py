from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from market_risk_toolkit.risk.models.ewma import EWMAModelConfig, ewma_forecast_variance
from market_risk_toolkit.risk.models.ewma import forecast as ewma_forecast
from market_risk_toolkit.risk.models.filtered_historical import (
    FilteredHistoricalConfig,
    build_filtered_residual_state,
)
from market_risk_toolkit.risk.models.filtered_historical import (
    forecast as fhs_forecast,
)


def test_ewma_variance_recursion_on_hand_checkable_fixture() -> None:
    returns = pd.Series([0.01, -0.01, 0.02, -0.03])
    seed_variance = float(returns.iloc[:2].var(ddof=1))
    expected = 0.94 * seed_variance + 0.06 * returns.iloc[2] ** 2
    expected = 0.94 * expected + 0.06 * returns.iloc[3] ** 2

    assert ewma_forecast_variance(returns, lambda_=0.94, seed_window=2) == pytest.approx(expected)


def test_ewma_forecast_uses_prior_observations_and_responds_to_recent_shock() -> None:
    calm = pd.Series([0.001] * 30)
    shocked = calm.copy()
    shocked.iloc[-1] = -0.10

    calm_forecast = ewma_forecast(
        calm,
        date=pd.Timestamp("2026-01-31"),
        confidence_level=0.99,
        config=EWMAModelConfig(estimation_window=30, seed_window=5),
    )
    shocked_forecast = ewma_forecast(
        shocked,
        date=pd.Timestamp("2026-01-31"),
        confidence_level=0.99,
        config=EWMAModelConfig(estimation_window=30, seed_window=5),
    )

    assert shocked_forecast.forecast_volatility > calm_forecast.forecast_volatility
    assert shocked_forecast.var >= 0.0
    assert shocked_forecast.es >= 0.0
    assert shocked_forecast.es >= shocked_forecast.var


def test_fhs_residual_construction_is_causal_and_excludes_seed_observations() -> None:
    returns = pd.Series([0.01, -0.01, 0.02, -0.02, 0.03, -0.03])

    state = build_filtered_residual_state(returns, lambda_=0.94, seed_window=2)

    assert state.residuals.size == len(returns) - 2
    seed_variance = float(returns.iloc[:2].var(ddof=1))
    expected_first_residual = returns.iloc[2] / np.sqrt(seed_variance)
    assert state.residuals[0] == pytest.approx(expected_first_residual)


def test_fhs_forecast_positive_loss_invariants() -> None:
    returns = pd.Series([-0.02, -0.01, 0.0, 0.01, 0.02] * 20)

    forecast = fhs_forecast(
        returns,
        date=pd.Timestamp("2026-01-31"),
        confidence_level=0.95,
        config=FilteredHistoricalConfig(estimation_window=100, seed_window=20),
    )

    assert forecast.var >= 0.0
    assert forecast.es >= 0.0
    assert forecast.es + 1.0e-12 >= forecast.var
    assert forecast.method_parameters["residual_pool_size"] == 80


def test_future_return_perturbation_does_not_alter_earlier_ewma_or_fhs_forecasts() -> None:
    index = pd.date_range("2026-01-01", periods=80, freq="D")
    returns = pd.Series(np.sin(np.arange(80)) / 100.0, index=index)
    perturbed = returns.copy(deep=True)
    perturbed.iloc[-1] = -99.0
    config_ewma = EWMAModelConfig(estimation_window=40, seed_window=10)
    config_fhs = FilteredHistoricalConfig(estimation_window=40, seed_window=10)
    date = index[-2]
    window = returns.loc[:date].iloc[-40:]
    perturbed_window = perturbed.loc[:date].iloc[-40:]

    assert ewma_forecast(
        window,
        date=date,
        confidence_level=0.99,
        config=config_ewma,
    ).var == pytest.approx(
        ewma_forecast(perturbed_window, date=date, confidence_level=0.99, config=config_ewma).var
    )
    assert fhs_forecast(
        window,
        date=date,
        confidence_level=0.99,
        config=config_fhs,
    ).var == pytest.approx(
        fhs_forecast(perturbed_window, date=date, confidence_level=0.99, config=config_fhs).var
    )


def test_input_return_series_is_not_mutated() -> None:
    returns = pd.Series(np.linspace(-0.02, 0.02, 50))
    original = returns.copy(deep=True)

    ewma_forecast(
        returns,
        date=pd.Timestamp("2026-01-31"),
        confidence_level=0.95,
        config=EWMAModelConfig(estimation_window=50, seed_window=10),
    )
    fhs_forecast(
        returns,
        date=pd.Timestamp("2026-01-31"),
        confidence_level=0.95,
        config=FilteredHistoricalConfig(estimation_window=50, seed_window=10),
    )

    pd.testing.assert_series_equal(returns, original)


@pytest.mark.parametrize(
    "config",
    [
        EWMAModelConfig(lambda_=1.0),
        EWMAModelConfig(lambda_=0.0),
        EWMAModelConfig(seed_window=1),
        EWMAModelConfig(estimation_window=20, seed_window=20),
    ],
)
def test_invalid_ewma_parameters_are_rejected(config: EWMAModelConfig) -> None:
    with pytest.raises(ValueError):
        config.validated()


def test_all_identical_returns_produce_zero_ewma_and_fhs_risk() -> None:
    returns = pd.Series([0.0] * 60)

    ewma = ewma_forecast(
        returns,
        date=pd.Timestamp("2026-01-31"),
        confidence_level=0.99,
        config=EWMAModelConfig(estimation_window=60, seed_window=10),
    )
    fhs = fhs_forecast(
        returns,
        date=pd.Timestamp("2026-01-31"),
        confidence_level=0.99,
        config=FilteredHistoricalConfig(estimation_window=60, seed_window=10),
    )

    assert ewma.var == pytest.approx(0.0)
    assert ewma.es == pytest.approx(0.0)
    assert fhs.var == pytest.approx(0.0)
    assert fhs.es == pytest.approx(0.0)
