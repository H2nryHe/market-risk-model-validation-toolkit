import pandas as pd
import pytest

from market_risk_toolkit.data.validation import (
    build_aligned_returns,
    validate_market_data,
)


def test_build_aligned_returns_drops_partial_rows_and_computes_returns() -> None:
    raw_prices = pd.DataFrame(
        {
            "SPY": [100.0, 101.0, 130.0],
            "QQQ": [200.0, None, 260.0],
        },
        index=pd.to_datetime(["2024-01-02", "2024-01-03", "2024-01-04"]),
    )

    aligned_prices, returns = build_aligned_returns(raw_prices)

    assert aligned_prices.index.tolist() == list(pd.to_datetime(["2024-01-02", "2024-01-04"]))
    assert aligned_prices.columns.tolist() == ["SPY", "QQQ"]
    assert returns.shape == (1, 2)
    assert returns.loc[pd.Timestamp("2024-01-04"), "SPY"] == pytest.approx(0.30)
    assert returns.loc[pd.Timestamp("2024-01-04"), "QQQ"] == pytest.approx(0.30)


def test_validate_market_data_flags_duplicates_missing_non_monotonic_and_spikes() -> None:
    raw_prices = pd.DataFrame(
        {
            "SPY": [101.0, 100.0, 100.0, 130.0],
            "QQQ": [None, 200.0, 200.0, 260.0],
        },
        index=pd.to_datetime(["2024-01-03", "2024-01-02", "2024-01-02", "2024-01-04"]),
    )

    aligned_prices, returns = build_aligned_returns(raw_prices)
    validation = validate_market_data(
        raw_prices=raw_prices,
        aligned_prices=aligned_prices,
        returns=returns,
        spike_threshold=0.15,
    )

    issue_types = set(validation.flags["issue_type"])

    assert validation.summary["duplicate_date_count"] == 1
    assert validation.summary["has_non_monotonic_index"] is True
    assert validation.summary["missing_value_count"] == 1
    assert validation.summary["cross_asset_misaligned_rows"] == 1
    assert validation.summary["suspicious_return_count"] == 2
    assert {
        "duplicate_date",
        "missing_value",
        "non_monotonic_index",
        "cross_asset_alignment",
        "suspicious_return_spike",
    }.issubset(issue_types)
