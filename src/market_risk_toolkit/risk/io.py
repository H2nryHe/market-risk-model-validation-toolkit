"""I/O helpers for risk analytics."""

from __future__ import annotations

from pathlib import Path

import pandas as pd


def load_portfolio_returns(path: str | Path) -> pd.Series:
    """Load the portfolio return series from a Stage 2 time-series artifact."""

    timeseries_path = Path(path)
    frame = pd.read_csv(timeseries_path, parse_dates=["date"])
    frame = frame.set_index("date").sort_index()
    if "portfolio_return" not in frame.columns:
        raise ValueError("Expected a 'portfolio_return' column in the portfolio time-series file.")
    returns = frame["portfolio_return"].astype(float).copy()
    returns.index.name = "date"
    returns.name = "portfolio_return"
    return returns
