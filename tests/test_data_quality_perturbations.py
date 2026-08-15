from __future__ import annotations

import numpy as np
import pandas as pd

from market_risk_toolkit.data_quality.perturbations import (
    apply_scenario,
    build_scenario_table,
    select_scenario_dates,
)


def _prices(periods: int = 20) -> pd.DataFrame:
    index = pd.date_range("2026-01-01", periods=periods, freq="D")
    return pd.DataFrame(
        {
            "SPY": np.linspace(100.0, 119.0, periods),
            "QQQ": np.linspace(200.0, 219.0, periods),
            "TLT": np.linspace(90.0, 109.0, periods),
            "GLD": np.linspace(150.0, 169.0, periods),
        },
        index=index,
    )


def test_clean_input_is_never_mutated_by_perturbations() -> None:
    clean = _prices()
    original = clean.copy(deep=True)

    for scenario_id in ("DQ-01", "DQ-02", "DQ-03", "DQ-04", "DQ-05"):
        apply_scenario(clean, scenario_id)

    pd.testing.assert_frame_equal(clean, original)


def test_dq01_introduces_exact_missing_block() -> None:
    clean = _prices()
    corrupted = apply_scenario(clean, "DQ-01")
    start, end = select_scenario_dates(clean)["DQ-01"]

    assert corrupted.loc[start:end, "SPY"].isna().sum() == 5
    assert corrupted.drop(columns=["SPY"]).equals(clean.drop(columns=["SPY"]))


def test_dq02_creates_exact_stale_sequence() -> None:
    clean = _prices()
    corrupted = apply_scenario(clean, "DQ-02")
    start, end = select_scenario_dates(clean)["DQ-02"]
    previous_value = clean.loc[:start, "TLT"].iloc[-2]

    assert (corrupted.loc[start:end, "TLT"] == previous_value).all()
    assert corrupted.drop(columns=["TLT"]).equals(clean.drop(columns=["TLT"]))


def test_dq03_applies_configured_multiplier() -> None:
    clean = _prices()
    corrupted = apply_scenario(clean, "DQ-03")
    start, _ = select_scenario_dates(clean)["DQ-03"]

    assert corrupted.loc[start, "QQQ"] == clean.loc[start, "QQQ"] * 100.0


def test_dq04_shifts_only_intended_asset() -> None:
    clean = _prices()
    corrupted = apply_scenario(clean, "DQ-04")

    pd.testing.assert_series_equal(corrupted["GLD"], clean["GLD"].shift(1), check_names=False)
    pd.testing.assert_frame_equal(corrupted.drop(columns=["GLD"]), clean.drop(columns=["GLD"]))


def test_dq05_creates_one_discontinuity_structure() -> None:
    clean = _prices()
    corrupted = apply_scenario(clean, "DQ-05")
    start, _ = select_scenario_dates(clean)["DQ-05"]

    assert (corrupted.loc[start:, "SPY"] == clean.loc[start:, "SPY"] * 0.5).all()
    assert (corrupted.loc[: start - pd.Timedelta(days=1), "SPY"] == clean.loc[: start - pd.Timedelta(days=1), "SPY"]).all()


def test_scenario_date_selection_is_deterministic_and_not_impact_based() -> None:
    clean = _prices(100)

    first = build_scenario_table(clean)
    second = build_scenario_table(clean)

    pd.testing.assert_frame_equal(first, second)
    assert set(first["scenario_id"]) == {"DQ-01", "DQ-02", "DQ-03", "DQ-04", "DQ-05"}
    assert first["selection_rule"].str.contains("not selected based on impact").all()
