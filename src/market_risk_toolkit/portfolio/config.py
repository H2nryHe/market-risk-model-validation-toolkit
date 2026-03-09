"""Configuration helpers for portfolio construction."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml


@dataclass(frozen=True)
class PortfolioConfig:
    """Configuration for a portfolio build."""

    name: str
    description: str
    strategy: str
    tickers: tuple[str, ...]
    weights: dict[str, float] | None = None
    returns_path: Path = Path("data/processed/returns.csv")
    output_dir: Path = Path("data/artifacts")
    figure_dir: Path = Path("reports/figures")
    annualization_factor: int = 252

    def normalized(self) -> "PortfolioConfig":
        normalized_tickers = tuple(dict.fromkeys(ticker.upper() for ticker in self.tickers))
        normalized_weights = None
        if self.weights is not None:
            normalized_weights = {ticker.upper(): float(weight) for ticker, weight in self.weights.items()}
        return PortfolioConfig(
            name=self.name,
            description=self.description,
            strategy=self.strategy.lower(),
            tickers=normalized_tickers,
            weights=normalized_weights,
            returns_path=Path(self.returns_path),
            output_dir=Path(self.output_dir),
            figure_dir=Path(self.figure_dir),
            annualization_factor=int(self.annualization_factor),
        )


def load_portfolio_config(path: str | Path) -> PortfolioConfig:
    """Load a portfolio configuration from YAML."""

    config_path = Path(path)
    with config_path.open("r", encoding="utf-8") as handle:
        payload: dict[str, Any] = yaml.safe_load(handle) or {}

    return PortfolioConfig(
        name=payload["name"],
        description=payload.get("description", ""),
        strategy=payload.get("strategy", "equal_weight"),
        tickers=tuple(payload.get("tickers", [])),
        weights=payload.get("weights"),
        returns_path=Path(payload.get("returns_path", "data/processed/returns.csv")),
        output_dir=Path(payload.get("output_dir", "data/artifacts")),
        figure_dir=Path(payload.get("figure_dir", "reports/figures")),
        annualization_factor=int(payload.get("annualization_factor", 252)),
    ).normalized()
