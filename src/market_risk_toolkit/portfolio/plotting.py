"""Plotting helpers for portfolio outputs."""

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


def save_cumulative_return_plot(
    cumulative_returns: pd.Series,
    portfolio_name: str,
    destination: str | Path,
) -> Path:
    """Save a cumulative return line plot for the portfolio."""

    output_path = Path(destination)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    fig, ax = plt.subplots(figsize=(10, 5))
    ax.plot(cumulative_returns.index, cumulative_returns.values, color="#1f5aa6", linewidth=2.0)
    ax.axhline(0.0, color="#666666", linewidth=1.0, linestyle="--")
    ax.set_title(f"{portfolio_name} Cumulative Return")
    ax.set_xlabel("Date")
    ax.set_ylabel("Cumulative return")
    ax.grid(alpha=0.25)
    fig.tight_layout()
    fig.savefig(output_path, dpi=160)
    plt.close(fig)
    return output_path
