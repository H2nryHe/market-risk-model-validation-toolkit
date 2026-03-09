"""Configuration helpers for rolling risk metric generation."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml


@dataclass(frozen=True)
class RiskConfig:
    """Configuration for rolling VaR/ES estimation."""

    portfolio_name: str
    returns_path: Path
    output_dir: Path = Path("data/artifacts")
    figure_dir: Path = Path("reports/figures")
    window: int = 250
    confidence_levels: tuple[float, ...] = (0.95, 0.99)

    def normalized(self) -> "RiskConfig":
        normalized_levels = tuple(sorted(float(level) for level in self.confidence_levels))
        return RiskConfig(
            portfolio_name=self.portfolio_name,
            returns_path=Path(self.returns_path),
            output_dir=Path(self.output_dir),
            figure_dir=Path(self.figure_dir),
            window=int(self.window),
            confidence_levels=normalized_levels,
        )


def load_risk_config(path: str | Path) -> RiskConfig:
    """Load a risk config from YAML."""

    config_path = Path(path)
    with config_path.open("r", encoding="utf-8") as handle:
        payload: dict[str, Any] = yaml.safe_load(handle) or {}

    return RiskConfig(
        portfolio_name=payload["portfolio_name"],
        returns_path=Path(payload["returns_path"]),
        output_dir=Path(payload.get("output_dir", "data/artifacts")),
        figure_dir=Path(payload.get("figure_dir", "reports/figures")),
        window=int(payload.get("window", 250)),
        confidence_levels=tuple(payload.get("confidence_levels", (0.95, 0.99))),
    ).normalized()
