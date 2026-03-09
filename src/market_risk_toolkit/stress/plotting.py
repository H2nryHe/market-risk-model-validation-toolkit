"""Plotting helpers for deterministic stress scenarios."""

from __future__ import annotations

import os
import tempfile
from pathlib import Path

os.environ.setdefault(
    "MPLCONFIGDIR",
    str(Path(tempfile.gettempdir()) / "market_risk_toolkit_mpl"),
)

import matplotlib

matplotlib.use("Agg")

import matplotlib.pyplot as plt
import pandas as pd


def save_stress_bar_chart(
    scenario_summary: pd.DataFrame,
    portfolio_name: str,
    destination: str | Path,
) -> Path:
    """Save a bar chart of portfolio PnL by stress scenario."""

    output_path = Path(destination)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    ordered = scenario_summary.sort_values("portfolio_pnl")
    colors = ["#b2182b" if pnl < 0 else "#2166ac" for pnl in ordered["portfolio_pnl"]]

    fig, ax = plt.subplots(figsize=(10, 5))
    ax.bar(ordered["scenario_name"], ordered["portfolio_pnl"], color=colors)
    ax.axhline(0.0, color="#444444", linewidth=1.0)
    ax.set_title(f"{portfolio_name} Deterministic Stress Scenario PnL")
    ax.set_xlabel("Scenario")
    ax.set_ylabel("Portfolio PnL")
    ax.grid(axis="y", alpha=0.25)
    fig.tight_layout()
    fig.savefig(output_path, dpi=160)
    plt.close(fig)
    return output_path
