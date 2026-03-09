"""I/O helpers for stress testing."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

import pandas as pd
import yaml


@dataclass(frozen=True)
class StressScenario:
    """A deterministic scenario definition."""

    name: str
    description: str
    shocks: dict[str, float]


def load_scenarios(path: str | Path) -> list[StressScenario]:
    """Load deterministic scenarios from YAML."""

    scenarios_path = Path(path)
    with scenarios_path.open("r", encoding="utf-8") as handle:
        payload: dict[str, Any] = yaml.safe_load(handle) or {}

    scenario_payloads = payload.get("scenarios", [])
    scenarios = []
    for scenario_payload in scenario_payloads:
        shocks = {
            str(asset).upper(): float(shock)
            for asset, shock in (scenario_payload.get("shocks") or {}).items()
        }
        scenarios.append(
            StressScenario(
                name=scenario_payload["name"],
                description=scenario_payload.get("description", ""),
                shocks=shocks,
            )
        )
    if not scenarios:
        raise ValueError("At least one stress scenario must be defined.")
    return scenarios


def weights_to_frame(weights: pd.Series) -> pd.DataFrame:
    """Convert a weight vector into a stable table format."""

    return weights.rename("weight").rename_axis("ticker").reset_index()
