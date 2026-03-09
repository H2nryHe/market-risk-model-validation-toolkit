"""Configuration helpers for VaR backtesting and model validation."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml


@dataclass(frozen=True)
class ValidationConfig:
    """Configuration for VaR backtesting on rolling risk outputs."""

    portfolio_name: str
    risk_table_path: Path
    output_dir: Path = Path("data/artifacts")
    figure_dir: Path = Path("reports/figures")
    confidence_levels: tuple[float, ...] = (0.95, 0.99)

    def normalized(self) -> "ValidationConfig":
        return ValidationConfig(
            portfolio_name=self.portfolio_name,
            risk_table_path=Path(self.risk_table_path),
            output_dir=Path(self.output_dir),
            figure_dir=Path(self.figure_dir),
            confidence_levels=tuple(sorted(float(level) for level in self.confidence_levels)),
        )


def load_validation_config(path: str | Path) -> ValidationConfig:
    """Load a validation config from YAML."""

    config_path = Path(path)
    with config_path.open("r", encoding="utf-8") as handle:
        payload: dict[str, Any] = yaml.safe_load(handle) or {}

    return ValidationConfig(
        portfolio_name=payload["portfolio_name"],
        risk_table_path=Path(payload["risk_table_path"]),
        output_dir=Path(payload.get("output_dir", "data/artifacts")),
        figure_dir=Path(payload.get("figure_dir", "reports/figures")),
        confidence_levels=tuple(payload.get("confidence_levels", (0.95, 0.99))),
    ).normalized()
