"""Validation and cleaning helpers for daily market data."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import pandas as pd


@dataclass(frozen=True)
class ValidationArtifacts:
    """Structured validation outputs for the downloaded market data."""

    summary: dict[str, Any]
    flags: pd.DataFrame


def prepare_price_panel(raw_prices: pd.DataFrame) -> pd.DataFrame:
    """Canonicalize price data prior to alignment and return calculation."""

    prices = raw_prices.copy()
    prices.index = pd.to_datetime(prices.index).tz_localize(None)
    prices.index.name = "date"
    prices.columns = [str(column).upper() for column in prices.columns]
    prices = prices.groupby(level=0).last()
    prices = prices.sort_index()
    return prices.astype(float)


def build_aligned_returns(raw_prices: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Create an aligned price panel and corresponding daily simple returns."""

    prepared_prices = prepare_price_panel(raw_prices)
    aligned_prices = prepared_prices.dropna(axis=0, how="any")
    returns = aligned_prices.pct_change().dropna(axis=0, how="any")
    returns.index.name = "date"
    return aligned_prices, returns


def validate_market_data(
    raw_prices: pd.DataFrame,
    aligned_prices: pd.DataFrame,
    returns: pd.DataFrame,
    spike_threshold: float,
) -> ValidationArtifacts:
    """Run a set of quality checks on raw prices and cleaned returns."""

    prepared_prices = prepare_price_panel(raw_prices)
    flag_frames = [
        _flag_duplicate_dates(raw_prices),
        _flag_non_monotonic_index(raw_prices),
        _flag_missing_values(prepared_prices),
        _flag_cross_asset_alignment(prepared_prices),
        _flag_return_spikes(returns, spike_threshold),
    ]
    non_empty_flag_frames = [frame for frame in flag_frames if not frame.empty]
    flags = _empty_flags()
    if non_empty_flag_frames:
        records = []
        for frame in non_empty_flag_frames:
            records.extend(frame.to_dict(orient="records"))
        flags = pd.DataFrame.from_records(records, columns=_empty_flags().columns).sort_values(
            by=["issue_type", "date", "ticker"],
            na_position="last",
        )

    summary = {
        "raw_start_date": _serialize_timestamp(prepared_prices.index.min()),
        "raw_end_date": _serialize_timestamp(prepared_prices.index.max()),
        "aligned_start_date": _serialize_timestamp(aligned_prices.index.min()),
        "aligned_end_date": _serialize_timestamp(aligned_prices.index.max()),
        "raw_observation_count": int(raw_prices.shape[0]),
        "aligned_observation_count": int(aligned_prices.shape[0]),
        "return_observation_count": int(returns.shape[0]),
        "ticker_count": int(prepared_prices.shape[1]),
        "duplicate_date_count": int(_count_duplicate_dates(raw_prices)),
        "has_non_monotonic_index": bool(not pd.Index(raw_prices.index).is_monotonic_increasing),
        "missing_value_count": int(prepared_prices.isna().sum().sum()),
        "rows_with_missing_values": int(prepared_prices.isna().any(axis=1).sum()),
        "cross_asset_misaligned_rows": int(prepared_prices.isna().any(axis=1).sum()),
        "rows_removed_during_alignment": int(prepared_prices.shape[0] - aligned_prices.shape[0]),
        "spike_threshold": float(spike_threshold),
        "suspicious_return_count": int((returns.abs() > spike_threshold).sum().sum()),
        "per_ticker_missing_values": {
            ticker: int(count) for ticker, count in prepared_prices.isna().sum().items()
        },
        "per_ticker_suspicious_returns": {
            ticker: int(count) for ticker, count in (returns.abs() > spike_threshold).sum().items()
        },
    }
    return ValidationArtifacts(summary=summary, flags=flags)


def _flag_duplicate_dates(raw_prices: pd.DataFrame) -> pd.DataFrame:
    duplicate_mask = pd.Index(raw_prices.index).duplicated(keep=False)
    duplicate_dates = pd.to_datetime(pd.Index(raw_prices.index)[duplicate_mask]).tz_localize(None)
    if duplicate_dates.empty:
        return _empty_flags()

    unique_duplicate_dates = pd.Index(duplicate_dates.unique()).sort_values()
    return pd.DataFrame(
        {
            "issue_type": ["duplicate_date"] * len(unique_duplicate_dates),
            "date": unique_duplicate_dates,
            "ticker": [pd.NA] * len(unique_duplicate_dates),
            "value": [pd.NA] * len(unique_duplicate_dates),
            "details": ["Raw price panel contains duplicated dates."] * len(unique_duplicate_dates),
        }
    )


def _flag_non_monotonic_index(raw_prices: pd.DataFrame) -> pd.DataFrame:
    raw_index = pd.Index(raw_prices.index)
    if raw_index.is_monotonic_increasing:
        return _empty_flags()

    return pd.DataFrame(
        {
            "issue_type": ["non_monotonic_index"],
            "date": [pd.NA],
            "ticker": [pd.NA],
            "value": [pd.NA],
            "details": ["Raw price index is not strictly increasing."],
        }
    )


def _flag_missing_values(prepared_prices: pd.DataFrame) -> pd.DataFrame:
    missing_mask = prepared_prices.isna()
    if not missing_mask.any().any():
        return _empty_flags()

    stacked = missing_mask.stack()
    missing_entries = stacked[stacked].reset_index()
    missing_entries.columns = ["date", "ticker", "flag"]
    missing_entries["issue_type"] = "missing_value"
    missing_entries["value"] = pd.NA
    missing_entries["details"] = "Adjusted close is missing for this date/ticker."
    return missing_entries[["issue_type", "date", "ticker", "value", "details"]]


def _flag_cross_asset_alignment(prepared_prices: pd.DataFrame) -> pd.DataFrame:
    misaligned_rows = prepared_prices[prepared_prices.isna().any(axis=1)]
    if misaligned_rows.empty:
        return _empty_flags()

    records = []
    for date, row in misaligned_rows.iterrows():
        missing_tickers = [ticker for ticker, value in row.items() if pd.isna(value)]
        records.append(
            {
                "issue_type": "cross_asset_alignment",
                "date": date,
                "ticker": pd.NA,
                "value": len(missing_tickers),
                "details": f"Missing tickers: {', '.join(missing_tickers)}",
            }
        )
    return pd.DataFrame.from_records(records)


def _flag_return_spikes(returns: pd.DataFrame, spike_threshold: float) -> pd.DataFrame:
    spike_mask = returns.abs() > spike_threshold
    if not spike_mask.any().any():
        return _empty_flags()

    spike_entries = spike_mask.stack()
    spike_entries = spike_entries[spike_entries].reset_index()
    spike_entries.columns = ["date", "ticker", "flag"]
    spike_entries["issue_type"] = "suspicious_return_spike"
    spike_entries["value"] = [
        float(returns.loc[row.date, row.ticker]) for row in spike_entries.itertuples(index=False)
    ]
    spike_entries["details"] = (
        "Absolute daily return exceeds the configured suspicious-move threshold."
    )
    return spike_entries[["issue_type", "date", "ticker", "value", "details"]]


def _empty_flags() -> pd.DataFrame:
    return pd.DataFrame(columns=["issue_type", "date", "ticker", "value", "details"])


def _count_duplicate_dates(raw_prices: pd.DataFrame) -> int:
    duplicate_mask = pd.Index(raw_prices.index).duplicated(keep=False)
    duplicate_dates = pd.to_datetime(pd.Index(raw_prices.index)[duplicate_mask]).tz_localize(None)
    return int(pd.Index(duplicate_dates).nunique())


def _serialize_timestamp(timestamp: pd.Timestamp | Any) -> str | None:
    if timestamp is None or pd.isna(timestamp):
        return None
    return pd.Timestamp(timestamp).strftime("%Y-%m-%d")
