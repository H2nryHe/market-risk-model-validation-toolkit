"""Plotting helpers for exceedance-based validation outputs."""

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


def save_exceedance_plot(
    exceedance_table: pd.DataFrame,
    portfolio_name: str,
    confidence_level: float,
    destination: str | Path,
) -> Path:
    """Save a realized-loss versus VaR plot with exceedance markers."""

    suffix = str(int(round(confidence_level * 100)))
    output_path = Path(destination)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    fig, ax = plt.subplots(figsize=(11, 5))
    ax.plot(
        exceedance_table.index,
        exceedance_table["realized_loss"],
        color="#444444",
        linewidth=1.0,
        label="Realized loss",
    )
    for model, color in (("historical", "#1f5aa6"), ("parametric", "#bf5b17")):
        var_column = f"{model}_var_{suffix}"
        exceedance_column = f"{model}_exceedance_{suffix}"
        ax.plot(
            exceedance_table.index,
            exceedance_table[var_column],
            linewidth=1.5,
            color=color,
            label=f"{model.capitalize()} VaR {suffix}%",
        )
        exceedances = exceedance_table[exceedance_table[exceedance_column] == 1]
        ax.scatter(
            exceedances.index,
            exceedances["realized_loss"],
            color=color,
            s=18,
            alpha=0.75,
            label=f"{model.capitalize()} exceedances",
        )

    ax.set_title(f"{portfolio_name} VaR Exceedances ({suffix}%)")
    ax.set_xlabel("Date")
    ax.set_ylabel("Loss")
    ax.grid(alpha=0.25)
    ax.legend(frameon=False, ncol=2)
    fig.tight_layout()
    fig.savefig(output_path, dpi=160)
    plt.close(fig)
    return output_path
