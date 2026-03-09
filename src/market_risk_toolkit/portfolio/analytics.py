"""Core portfolio construction and summary analytics."""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd

from market_risk_toolkit.portfolio.config import PortfolioConfig


@dataclass(frozen=True)
class PortfolioBuildResult:
    """In-memory portfolio outputs for downstream reporting."""

    weights: pd.Series
    daily_returns: pd.Series
    cumulative_returns: pd.Series
    nav: pd.Series
    summary: pd.DataFrame
    asset_returns: pd.DataFrame


def build_portfolio(returns: pd.DataFrame, config: PortfolioConfig) -> PortfolioBuildResult:
    """Build a portfolio return series from a return panel and config."""

    normalized_config = config.normalized()
    asset_returns = _select_asset_returns(returns, normalized_config.tickers)
    weights = resolve_weights(asset_returns.columns.tolist(), normalized_config)
    portfolio_returns = asset_returns.mul(weights, axis=1).sum(axis=1)
    portfolio_returns.name = "portfolio_return"
    nav = (1.0 + portfolio_returns).cumprod()
    nav.name = "nav"
    cumulative_returns = nav - 1.0
    cumulative_returns.name = "cumulative_return"
    summary = compute_summary_statistics(
        portfolio_returns=portfolio_returns,
        nav=nav,
        config=normalized_config,
    )
    return PortfolioBuildResult(
        weights=weights,
        daily_returns=portfolio_returns,
        cumulative_returns=cumulative_returns,
        nav=nav,
        summary=summary,
        asset_returns=asset_returns,
    )


def resolve_weights(available_tickers: list[str], config: PortfolioConfig) -> pd.Series:
    """Resolve a portfolio weight vector from config."""

    tickers = list(dict.fromkeys(ticker.upper() for ticker in available_tickers))
    if config.strategy == "equal_weight":
        if not tickers:
            raise ValueError("Cannot build an equal-weight portfolio with no tickers.")
        weight = 1.0 / len(tickers)
        return pd.Series({ticker: weight for ticker in tickers}, name="weight")

    if config.strategy == "custom_weight":
        if not config.weights:
            raise ValueError("Custom-weight portfolios require a non-empty weights mapping.")
        missing = [ticker for ticker in config.weights if ticker not in tickers]
        if missing:
            raise ValueError(f"Weight tickers are not available in the return panel: {missing}")
        weights = pd.Series({ticker: config.weights[ticker] for ticker in tickers}, name="weight")
        if not np.isclose(float(weights.sum()), 1.0, atol=1e-8):
            raise ValueError("Portfolio weights must sum to 1.0.")
        return weights

    raise ValueError(f"Unsupported portfolio strategy: {config.strategy}")


def compute_summary_statistics(
    portfolio_returns: pd.Series,
    nav: pd.Series,
    config: PortfolioConfig,
) -> pd.DataFrame:
    """Compute standard portfolio summary statistics."""

    if portfolio_returns.empty:
        raise ValueError("Portfolio returns are empty.")

    periods = float(len(portfolio_returns))
    annualization_factor = float(config.annualization_factor)
    ending_nav = float(nav.iloc[-1])
    annualized_return = ending_nav ** (annualization_factor / periods) - 1.0
    annualized_volatility = float(portfolio_returns.std(ddof=1) * np.sqrt(annualization_factor))
    sharpe_ratio = np.nan
    if annualized_volatility > 0:
        sharpe_ratio = annualized_return / annualized_volatility

    running_peak = nav.cummax()
    drawdown_series = nav / running_peak - 1.0
    max_drawdown = float(drawdown_series.min())

    summary = pd.DataFrame(
        [
            {
                "portfolio_name": config.name,
                "strategy": config.strategy,
                "start_date": portfolio_returns.index.min().strftime("%Y-%m-%d"),
                "end_date": portfolio_returns.index.max().strftime("%Y-%m-%d"),
                "observation_count": int(len(portfolio_returns)),
                "annualized_return": annualized_return,
                "annualized_volatility": annualized_volatility,
                "sharpe_ratio": sharpe_ratio,
                "max_drawdown": max_drawdown,
            }
        ]
    )
    return summary


def build_portfolio_timeseries(result: PortfolioBuildResult) -> pd.DataFrame:
    """Combine core portfolio time series into a single artifact table."""

    return pd.concat(
        [result.daily_returns, result.cumulative_returns, result.nav],
        axis=1,
    ).reset_index()


def _select_asset_returns(returns: pd.DataFrame, requested_tickers: tuple[str, ...]) -> pd.DataFrame:
    if not requested_tickers:
        raise ValueError("Portfolio config must specify at least one ticker.")
    missing = [ticker for ticker in requested_tickers if ticker not in returns.columns]
    if missing:
        raise ValueError(f"Requested tickers are missing from the return panel: {missing}")
    return returns.loc[:, list(requested_tickers)].copy()
