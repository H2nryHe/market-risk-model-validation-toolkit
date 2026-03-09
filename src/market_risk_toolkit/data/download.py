"""Download helpers for daily market data."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Iterable

import pandas as pd
import yfinance as yf


def download_adjusted_close(
    tickers: Iterable[str],
    start_date: str,
    end_date: str | None = None,
) -> tuple[pd.DataFrame, dict[str, object]]:
    """Download daily adjusted close data for the requested ticker universe.

    The returned price panel is indexed by date and uses uppercase ticker symbols
    as columns.
    """

    ordered_tickers = tuple(dict.fromkeys(str(ticker).upper() for ticker in tickers))
    if not ordered_tickers:
        raise ValueError("At least one ticker is required.")

    raw_frame = yf.download(
        tickers=list(ordered_tickers),
        start=start_date,
        end=end_date,
        interval="1d",
        auto_adjust=False,
        actions=False,
        progress=False,
        threads=False,
        group_by="column",
    )
    if raw_frame.empty:
        raise ValueError("No data was returned by yfinance for the requested universe.")

    prices = _extract_adjusted_close(raw_frame, ordered_tickers)
    downloaded_at = datetime.now(timezone.utc).replace(microsecond=0).isoformat()
    metadata = {
        "source": "yfinance",
        "downloaded_at_utc": downloaded_at,
        "tickers": list(ordered_tickers),
        "start_date": start_date,
        "end_date": end_date,
        "rows": int(prices.shape[0]),
        "columns": int(prices.shape[1]),
    }
    return prices, metadata


def _extract_adjusted_close(raw_frame: pd.DataFrame, tickers: tuple[str, ...]) -> pd.DataFrame:
    """Extract an adjusted close panel from the yfinance output shape."""

    if isinstance(raw_frame.columns, pd.MultiIndex):
        fields = raw_frame.columns.get_level_values(0)
        field_name = "Adj Close" if "Adj Close" in fields else "Close"
        price_panel = raw_frame[field_name].copy()
    else:
        field_name = "Adj Close" if "Adj Close" in raw_frame.columns else "Close"
        price_panel = raw_frame[[field_name]].copy()
        if len(tickers) != 1:
            raise ValueError("Unexpected flat yfinance output for multiple tickers.")
        price_panel.columns = [tickers[0]]

    if isinstance(price_panel, pd.Series):
        price_panel = price_panel.to_frame(name=tickers[0])

    price_panel.columns = [str(column).upper() for column in price_panel.columns]
    price_panel.index = pd.to_datetime(price_panel.index).tz_localize(None)
    price_panel.index.name = "date"
    price_panel = price_panel.sort_index()
    return price_panel.astype(float)
