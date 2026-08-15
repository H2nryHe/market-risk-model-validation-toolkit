from __future__ import annotations

import numpy as np
import pandas as pd

from market_risk_toolkit.data_quality.controls import run_control_suite, summarize_policy
from market_risk_toolkit.data_quality.perturbations import apply_scenario


def _prices(periods: int = 40) -> pd.DataFrame:
    index = pd.date_range("2026-01-01", periods=periods, freq="D")
    base = np.arange(periods, dtype=float)
    return pd.DataFrame(
        {
            "SPY": 100.0 + base,
            "QQQ": 200.0 + base * 1.1,
            "TLT": 90.0 + base * 0.7,
            "GLD": 150.0 + base * 0.5,
        },
        index=index,
    )


def _result_map(clean: pd.DataFrame, scenario_id: str):
    corrupted = apply_scenario(clean, scenario_id)
    shifted = ("GLD",) if scenario_id == "DQ-04" else ()
    return {
        result.control_name: result
        for result in run_control_suite(
            clean_prices=clean,
            candidate_prices=corrupted,
            shifted_assets=shifted,
        )
    }


def test_missingness_control_detects_dq01() -> None:
    results = _result_map(_prices(), "DQ-01")

    assert results["missingness"].detected
    assert results["missingness"].blocking_control_triggered


def test_staleness_control_detects_dq02() -> None:
    results = _result_map(_prices(), "DQ-02")

    assert results["staleness"].detected
    assert results["staleness"].control_status == "BLOCK"


def test_extreme_return_control_detects_dq03() -> None:
    results = _result_map(_prices(), "DQ-03")

    assert results["extreme_return"].detected
    assert results["extreme_return"].metric_value > results["extreme_return"].threshold


def test_alignment_control_detects_dq04() -> None:
    results = _result_map(_prices(), "DQ-04")

    assert results["date_alignment"].detected
    assert "GLD=clean_shift_plus_one" in results["date_alignment"].details


def test_discontinuity_control_detects_dq05_as_outlier() -> None:
    results = _result_map(_prices(), "DQ-05")

    assert results["extreme_return"].detected
    assert results["extreme_return"].control_status == "BLOCK"


def test_clean_fixture_does_not_trigger_blocking_controls() -> None:
    clean = _prices()
    results = run_control_suite(clean_prices=clean, candidate_prices=clean)
    policy = summarize_policy(results)

    assert not any(result.blocking_control_triggered for result in results)
    assert policy["control_status"] == "PASS"
    assert policy["risk_pipeline_allowed"] is True


def test_block_flag_pass_behavior_is_deterministic() -> None:
    clean = _prices()
    corrupted = apply_scenario(clean, "DQ-03")

    first = summarize_policy(run_control_suite(clean_prices=clean, candidate_prices=corrupted))
    second = summarize_policy(run_control_suite(clean_prices=clean, candidate_prices=corrupted))

    assert first == second
    assert first["control_status"] == "BLOCK"
