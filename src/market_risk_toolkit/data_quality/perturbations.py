"""Deterministic market-data perturbations for Phase 6."""

from __future__ import annotations

import json
from dataclasses import dataclass

import pandas as pd

SELECTION_RULE = (
    "deterministic fixed-position rule on frozen price sample: DQ-01 begins at "
    "40%, DQ-02 begins at 50%, DQ-03 occurs at 60%, DQ-04 begins at 70%, "
    "DQ-05 occurs at 80%; dates are not selected based on impact"
)


@dataclass(frozen=True)
class ScenarioDefinition:
    scenario_id: str
    scenario_name: str
    asset: str
    injection_level: str
    position_fraction: float
    length: int
    injection_type: str
    parameters: dict[str, object]
    expected_control: str


SCENARIO_DEFINITIONS: tuple[ScenarioDefinition, ...] = (
    ScenarioDefinition(
        scenario_id="DQ-01",
        scenario_name="Missing observation block",
        asset="SPY",
        injection_level="price",
        position_fraction=0.40,
        length=5,
        injection_type="set_price_missing",
        parameters={"missing_observations": 5},
        expected_control="missingness",
    ),
    ScenarioDefinition(
        scenario_id="DQ-02",
        scenario_name="Stale price sequence",
        asset="TLT",
        injection_level="price",
        position_fraction=0.50,
        length=5,
        injection_type="forward_fill_stale_price",
        parameters={"stale_observations": 5, "stale_source": "previous_clean_price"},
        expected_control="staleness",
    ),
    ScenarioDefinition(
        scenario_id="DQ-03",
        scenario_name="Extreme bad print",
        asset="QQQ",
        injection_level="price",
        position_fraction=0.60,
        length=1,
        injection_type="multiply_single_price",
        parameters={"multiplier": 100.0},
        expected_control="extreme_return",
    ),
    ScenarioDefinition(
        scenario_id="DQ-04",
        scenario_name="Cross-asset date misalignment",
        asset="GLD",
        injection_level="price",
        position_fraction=0.70,
        length=0,
        injection_type="shift_asset_plus_one_observation",
        parameters={"shift_observations": 1},
        expected_control="date_alignment",
    ),
    ScenarioDefinition(
        scenario_id="DQ-05",
        scenario_name="Corporate-action-like discontinuity",
        asset="SPY",
        injection_level="price",
        position_fraction=0.80,
        length=1,
        injection_type="multiply_price_from_date_forward",
        parameters={"factor": 0.5, "synthetic_not_actual_corporate_action": True},
        expected_control="extreme_return",
    ),
)


def load_price_panel(path: str) -> pd.DataFrame:
    """Load a frozen adjusted-close panel."""

    prices = pd.read_csv(path, parse_dates=["date"]).set_index("date").sort_index()
    prices.index.name = "date"
    return prices.astype(float).copy(deep=True)


def select_scenario_dates(prices: pd.DataFrame) -> dict[str, tuple[pd.Timestamp, pd.Timestamp]]:
    """Select deterministic scenario dates from fixed sample positions."""

    if prices.empty:
        raise ValueError("Price panel must not be empty.")
    dates = pd.Index(prices.index)
    selected: dict[str, tuple[pd.Timestamp, pd.Timestamp]] = {}
    for scenario in SCENARIO_DEFINITIONS:
        start_position = min(int(len(dates) * scenario.position_fraction), len(dates) - 1)
        end_position = start_position if scenario.length <= 1 else min(
            start_position + scenario.length - 1,
            len(dates) - 1,
        )
        selected[scenario.scenario_id] = (
            pd.Timestamp(dates[start_position]),
            pd.Timestamp(dates[end_position]),
        )
    return selected


def build_scenario_table(prices: pd.DataFrame) -> pd.DataFrame:
    """Create scenario metadata with deterministic dates and parameters."""

    dates = select_scenario_dates(prices)
    rows = []
    for scenario in SCENARIO_DEFINITIONS:
        start_date, end_date = dates[scenario.scenario_id]
        rows.append(
            {
                "scenario_id": scenario.scenario_id,
                "scenario_name": scenario.scenario_name,
                "asset": scenario.asset,
                "injection_level": scenario.injection_level,
                "start_date": start_date.strftime("%Y-%m-%d"),
                "end_date": end_date.strftime("%Y-%m-%d"),
                "injection_type": scenario.injection_type,
                "parameters": json.dumps(scenario.parameters, sort_keys=True),
                "selection_rule": SELECTION_RULE,
                "expected_control": scenario.expected_control,
            }
        )
    return pd.DataFrame.from_records(rows)


def apply_scenario(
    clean_prices: pd.DataFrame,
    scenario_id: str,
) -> pd.DataFrame:
    """Apply one deterministic scenario to a copy of clean prices."""

    scenario = _get_scenario(scenario_id)
    if scenario.asset not in clean_prices.columns:
        raise ValueError(f"Missing scenario asset '{scenario.asset}' in price panel.")
    corrupted = clean_prices.copy(deep=True)
    dates = select_scenario_dates(clean_prices)
    start_date, end_date = dates[scenario.scenario_id]

    if scenario.scenario_id == "DQ-01":
        mask = (corrupted.index >= start_date) & (corrupted.index <= end_date)
        corrupted.loc[mask, scenario.asset] = pd.NA
    elif scenario.scenario_id == "DQ-02":
        previous_position = clean_prices.index.get_loc(start_date) - 1
        if previous_position < 0:
            raise ValueError("Stale scenario requires a previous clean observation.")
        stale_value = float(clean_prices.iloc[previous_position][scenario.asset])
        mask = (corrupted.index >= start_date) & (corrupted.index <= end_date)
        corrupted.loc[mask, scenario.asset] = stale_value
    elif scenario.scenario_id == "DQ-03":
        multiplier = float(scenario.parameters["multiplier"])
        corrupted.loc[start_date, scenario.asset] = float(clean_prices.loc[start_date, scenario.asset]) * multiplier
    elif scenario.scenario_id == "DQ-04":
        corrupted[scenario.asset] = clean_prices[scenario.asset].shift(1)
    elif scenario.scenario_id == "DQ-05":
        factor = float(scenario.parameters["factor"])
        corrupted.loc[corrupted.index >= start_date, scenario.asset] = (
            corrupted.loc[corrupted.index >= start_date, scenario.asset] * factor
        )
    else:
        raise ValueError(f"Unsupported scenario_id '{scenario_id}'.")
    return corrupted


def _get_scenario(scenario_id: str) -> ScenarioDefinition:
    for scenario in SCENARIO_DEFINITIONS:
        if scenario.scenario_id == scenario_id:
            return scenario
    raise ValueError(f"Unknown scenario_id '{scenario_id}'.")
