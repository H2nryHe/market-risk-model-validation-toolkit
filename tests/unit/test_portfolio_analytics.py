import math

import pandas as pd
import pytest

from market_risk_toolkit.portfolio.analytics import build_portfolio, resolve_weights
from market_risk_toolkit.portfolio.config import PortfolioConfig


def test_equal_weight_portfolio_aggregates_returns_correctly() -> None:
    returns = pd.DataFrame(
        {
            "SPY": [0.01, -0.02, 0.03],
            "QQQ": [0.00, 0.01, 0.02],
        },
        index=pd.to_datetime(["2024-01-02", "2024-01-03", "2024-01-04"]),
    )
    config = PortfolioConfig(
        name="eq_test",
        description="",
        strategy="equal_weight",
        tickers=("SPY", "QQQ"),
        annualization_factor=252,
    )

    result = build_portfolio(returns, config)

    expected_returns = pd.Series([0.005, -0.005, 0.025], index=returns.index, name="portfolio_return")
    pd.testing.assert_series_equal(result.daily_returns, expected_returns)
    assert result.weights.to_dict() == {"SPY": 0.5, "QQQ": 0.5}


def test_custom_weight_portfolio_statistics_are_consistent() -> None:
    returns = pd.DataFrame(
        {
            "SPY": [0.01, 0.02, -0.01, 0.00],
            "TLT": [0.00, 0.01, 0.00, 0.01],
        },
        index=pd.to_datetime(["2024-01-02", "2024-01-03", "2024-01-04", "2024-01-05"]),
    )
    config = PortfolioConfig(
        name="custom_test",
        description="",
        strategy="custom_weight",
        tickers=("SPY", "TLT"),
        weights={"SPY": 0.6, "TLT": 0.4},
        annualization_factor=252,
    )

    result = build_portfolio(returns, config)
    summary = result.summary.iloc[0]

    expected_daily = pd.Series([0.006, 0.016, -0.006, 0.004], index=returns.index, name="portfolio_return")
    expected_nav = (1.0 + expected_daily).cumprod()
    expected_ann_return = float(expected_nav.iloc[-1] ** (252 / len(expected_daily)) - 1.0)
    expected_ann_vol = float(expected_daily.std(ddof=1) * math.sqrt(252))
    expected_sharpe = expected_ann_return / expected_ann_vol
    expected_drawdown = float((expected_nav / expected_nav.cummax() - 1.0).min())

    pd.testing.assert_series_equal(result.daily_returns, expected_daily)
    assert summary["annualized_return"] == pytest.approx(expected_ann_return)
    assert summary["annualized_volatility"] == pytest.approx(expected_ann_vol)
    assert summary["sharpe_ratio"] == pytest.approx(expected_sharpe)
    assert summary["max_drawdown"] == pytest.approx(expected_drawdown)


def test_resolve_weights_rejects_invalid_custom_sum() -> None:
    config = PortfolioConfig(
        name="bad_weights",
        description="",
        strategy="custom_weight",
        tickers=("SPY", "QQQ"),
        weights={"SPY": 0.7, "QQQ": 0.2},
    )

    with pytest.raises(ValueError, match="sum to 1.0"):
        resolve_weights(["SPY", "QQQ"], config)
