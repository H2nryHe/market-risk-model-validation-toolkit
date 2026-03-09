"""Deterministic scenario stress engine."""

from __future__ import annotations

from dataclasses import dataclass

import pandas as pd

from market_risk_toolkit.portfolio.analytics import resolve_weights
from market_risk_toolkit.portfolio.config import PortfolioConfig
from market_risk_toolkit.stress.io import StressScenario


@dataclass(frozen=True)
class StressTestResult:
    """Structured outputs from deterministic stress testing."""

    weights: pd.Series
    scenario_summary: pd.DataFrame
    contribution_table: pd.DataFrame


def build_stress_test(
    portfolio_config: PortfolioConfig,
    scenarios: list[StressScenario],
    notional: float = 1.0,
) -> StressTestResult:
    """Apply deterministic shocks to a portfolio weight vector."""

    normalized_portfolio = portfolio_config.normalized()
    weights = resolve_weights(list(normalized_portfolio.tickers), normalized_portfolio)

    contribution_records: list[dict[str, float | str]] = []
    summary_records: list[dict[str, float | str | int]] = []
    for scenario in scenarios:
        scenario_contributions = []
        shocked_asset_count = 0
        for ticker, weight in weights.items():
            shock = float(scenario.shocks.get(ticker, 0.0))
            contribution = float(notional * weight * shock)
            scenario_contributions.append(contribution)
            contribution_records.append(
                {
                    "scenario_name": scenario.name,
                    "scenario_description": scenario.description,
                    "ticker": ticker,
                    "weight": float(weight),
                    "shock": shock,
                    "contribution": contribution,
                }
            )
            if shock != 0.0:
                shocked_asset_count += 1

        scenario_pnl = float(sum(scenario_contributions))
        summary_records.append(
            {
                "scenario_name": scenario.name,
                "scenario_description": scenario.description,
                "portfolio_pnl": scenario_pnl,
                "portfolio_loss": -scenario_pnl,
                "shocked_asset_count": shocked_asset_count,
                "notional": float(notional),
            }
        )

    scenario_summary = pd.DataFrame.from_records(summary_records).sort_values("portfolio_pnl")
    contribution_table = pd.DataFrame.from_records(contribution_records).sort_values(
        ["scenario_name", "contribution"]
    )
    return StressTestResult(
        weights=weights,
        scenario_summary=scenario_summary,
        contribution_table=contribution_table,
    )
