"""I/O helpers for validation artifacts."""

from __future__ import annotations

from pathlib import Path

import pandas as pd


def load_risk_table(path: str | Path) -> pd.DataFrame:
    """Load the Stage 3 rolling risk table."""

    risk_path = Path(path)
    frame = pd.read_csv(risk_path, parse_dates=["date"])
    frame = frame.set_index("date").sort_index()
    frame.index.name = "date"
    return frame
