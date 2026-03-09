"""Configuration helpers for deterministic stress testing."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml


@dataclass(frozen=True)
class StressConfig:
    """Configuration for running deterministic stress scenarios."""

    portfolio_name: str
    portfolio_config_path: Path
    scenarios_path: Path
    output_dir: Path = Path("data/artifacts")
    figure_dir: Path = Path("reports/figures")
    notional: float = 1.0

    def normalized(self) -> "StressConfig":
        return StressConfig(
            portfolio_name=self.portfolio_name,
            portfolio_config_path=Path(self.portfolio_config_path),
            scenarios_path=Path(self.scenarios_path),
            output_dir=Path(self.output_dir),
            figure_dir=Path(self.figure_dir),
            notional=float(self.notional),
        )


def load_stress_config(path: str | Path) -> StressConfig:
    """Load a stress-engine config from YAML."""

    config_path = Path(path)
    with config_path.open("r", encoding="utf-8") as handle:
        payload: dict[str, Any] = yaml.safe_load(handle) or {}

    return StressConfig(
        portfolio_name=payload["portfolio_name"],
        portfolio_config_path=Path(payload["portfolio_config_path"]),
        scenarios_path=Path(payload["scenarios_path"]),
        output_dir=Path(payload.get("output_dir", "data/artifacts")),
        figure_dir=Path(payload.get("figure_dir", "reports/figures")),
        notional=float(payload.get("notional", 1.0)),
    ).normalized()
