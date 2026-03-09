"""I/O helpers for portfolio construction artifacts."""

from __future__ import annotations

from pathlib import Path

import pandas as pd


def load_returns_panel(path: str | Path) -> pd.DataFrame:
    """Load a cleaned daily returns panel from CSV."""

    returns_path = Path(path)
    frame = pd.read_csv(returns_path, parse_dates=["date"])
    frame = frame.set_index("date").sort_index()
    frame.columns = [str(column).upper() for column in frame.columns]
    frame.index.name = "date"
    return frame.astype(float)
