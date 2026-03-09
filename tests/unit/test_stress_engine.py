import pandas as pd
import pytest

from market_risk_toolkit.portfolio.config import PortfolioConfig
from market_risk_toolkit.stress.engine import build_stress_test
from market_risk_toolkit.stress.io import StressScenario


def test_stress_test_reconciles_portfolio_pnl_to_asset_contributions() -> None:
    portfolio_config = PortfolioConfig(
        name="stress_test_portfolio",
        description="",
        strategy="custom_weight",
        tickers=("SPY", "QQQ", "TLT"),
        weights={"SPY": 0.5, "QQQ": 0.3, "TLT": 0.2},
    )
    scenarios = [
        StressScenario(
            name="equity_hit",
            description="",
            shocks={"SPY": -0.10, "QQQ": -0.15, "TLT": 0.02},
        )
    ]

    result = build_stress_test(portfolio_config, scenarios, notional=1.0)

    summary_row = result.scenario_summary.iloc[0]
    contribution_sum = result.contribution_table["contribution"].sum()
    expected_pnl = 0.5 * -0.10 + 0.3 * -0.15 + 0.2 * 0.02

    assert summary_row["portfolio_pnl"] == pytest.approx(expected_pnl)
    assert summary_row["portfolio_pnl"] == pytest.approx(contribution_sum)
    assert summary_row["portfolio_loss"] == pytest.approx(-expected_pnl)


def test_equal_weight_portfolio_is_supported_for_stress_testing() -> None:
    portfolio_config = PortfolioConfig(
        name="equal_weight_stress",
        description="",
        strategy="equal_weight",
        tickers=("SPY", "GLD"),
    )
    scenarios = [
        StressScenario(
            name="mixed",
            description="",
            shocks={"SPY": -0.04, "GLD": 0.01},
        )
    ]

    result = build_stress_test(portfolio_config, scenarios, notional=2.0)

    weights = result.weights.sort_index()
    pd.testing.assert_series_equal(
        weights,
        pd.Series({"GLD": 0.5, "SPY": 0.5}, name="weight"),
    )
    assert result.scenario_summary.iloc[0]["portfolio_pnl"] == pytest.approx(-0.03)
