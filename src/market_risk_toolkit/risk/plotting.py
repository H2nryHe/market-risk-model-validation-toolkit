"""Plotting helpers for rolling VaR/ES comparisons."""

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


def save_risk_comparison_plot(
    risk_table: pd.DataFrame,
    portfolio_name: str,
    confidence_level: float,
    destination: str | Path,
) -> Path:
    """Save a rolling VaR/ES comparison plot for one confidence level."""

    suffix = str(int(round(confidence_level * 100)))
    output_path = Path(destination)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    fig, ax = plt.subplots(figsize=(11, 5))
    ax.plot(
        risk_table.index,
        -risk_table["portfolio_return"],
        color="#444444",
        linewidth=1.2,
        label="Realized loss",
    )
    ax.plot(
        risk_table.index,
        risk_table[f"historical_var_{suffix}"],
        color="#1f5aa6",
        linewidth=1.6,
        label=f"Historical VaR {suffix}%",
    )
    ax.plot(
        risk_table.index,
        risk_table[f"parametric_var_{suffix}"],
        color="#bf5b17",
        linewidth=1.6,
        label=f"Parametric VaR {suffix}%",
    )
    ax.plot(
        risk_table.index,
        risk_table[f"historical_es_{suffix}"],
        color="#2b8cbe",
        linewidth=1.2,
        linestyle="--",
        label=f"Historical ES {suffix}%",
    )
    ax.plot(
        risk_table.index,
        risk_table[f"parametric_es_{suffix}"],
        color="#d95f0e",
        linewidth=1.2,
        linestyle="--",
        label=f"Parametric ES {suffix}%",
    )
    ax.set_title(f"{portfolio_name} Rolling VaR / ES Comparison ({suffix}%)")
    ax.set_xlabel("Date")
    ax.set_ylabel("Loss")
    ax.grid(alpha=0.25)
    ax.legend(ncol=2, frameon=False)
    fig.tight_layout()
    fig.savefig(output_path, dpi=160)
    plt.close(fig)
    return output_path
