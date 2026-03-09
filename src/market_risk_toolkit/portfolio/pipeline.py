"""Orchestration for portfolio construction artifacts."""

from __future__ import annotations

import argparse
import json
from dataclasses import dataclass
from pathlib import Path

import pandas as pd

from market_risk_toolkit.portfolio.analytics import (
    PortfolioBuildResult,
    build_portfolio,
    build_portfolio_timeseries,
)
from market_risk_toolkit.portfolio.config import PortfolioConfig, load_portfolio_config
from market_risk_toolkit.portfolio.io import load_returns_panel
from market_risk_toolkit.portfolio.plotting import save_cumulative_return_plot


@dataclass(frozen=True)
class PortfolioArtifactPaths:
    """Paths written during a portfolio build."""

    summary_path: Path
    timeseries_path: Path
    weights_path: Path
    figure_path: Path


@dataclass(frozen=True)
class PortfolioPipelineResult:
    """Full output of the portfolio pipeline."""

    config: PortfolioConfig
    portfolio: PortfolioBuildResult
    artifacts: PortfolioArtifactPaths


def run_portfolio_pipeline(config: PortfolioConfig) -> PortfolioPipelineResult:
    """Load returns, build a portfolio, and write report-friendly artifacts."""

    normalized_config = config.normalized()
    returns = load_returns_panel(normalized_config.returns_path)
    portfolio = build_portfolio(returns, normalized_config)
    artifacts = _write_artifacts(portfolio, normalized_config)
    return PortfolioPipelineResult(
        config=normalized_config,
        portfolio=portfolio,
        artifacts=artifacts,
    )


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Build a portfolio from the cleaned return panel.")
    parser.add_argument(
        "--config",
        default="configs/portfolios/example_portfolio.yaml",
        help="Path to the portfolio YAML config.",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    config = load_portfolio_config(args.config)
    result = run_portfolio_pipeline(config)
    print(
        json.dumps(
            {
                "portfolio_name": result.config.name,
                "summary_path": str(result.artifacts.summary_path),
                "timeseries_path": str(result.artifacts.timeseries_path),
                "figure_path": str(result.artifacts.figure_path),
                "summary": result.portfolio.summary.iloc[0].to_dict(),
            },
            indent=2,
            default=_json_default,
        )
    )
    return 0


def _write_artifacts(
    portfolio: PortfolioBuildResult,
    config: PortfolioConfig,
) -> PortfolioArtifactPaths:
    config.output_dir.mkdir(parents=True, exist_ok=True)
    config.figure_dir.mkdir(parents=True, exist_ok=True)

    summary_path = config.output_dir / f"{config.name}_summary.csv"
    timeseries_path = config.output_dir / f"{config.name}_timeseries.csv"
    weights_path = config.output_dir / f"{config.name}_weights.csv"
    figure_path = config.figure_dir / f"{config.name}_cumulative_returns.png"

    portfolio.summary.to_csv(summary_path, index=False)
    build_portfolio_timeseries(portfolio).to_csv(timeseries_path, index=False)
    portfolio.weights.rename_axis("ticker").reset_index().to_csv(weights_path, index=False)
    save_cumulative_return_plot(
        cumulative_returns=portfolio.cumulative_returns,
        portfolio_name=config.name,
        destination=figure_path,
    )
    return PortfolioArtifactPaths(
        summary_path=summary_path,
        timeseries_path=timeseries_path,
        weights_path=weights_path,
        figure_path=figure_path,
    )


def _json_default(value: object) -> object:
    if isinstance(value, (pd.Timestamp,)):
        return value.isoformat()
    return value


if __name__ == "__main__":
    raise SystemExit(main())
