"""Data-quality controls and blocking policy for Phase 6."""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd

STALE_PRICE_RUN_THRESHOLD = 3
EXTREME_RETURN_THRESHOLD = 0.15
CONTROL_POLICY = {
    "PASS": "No project control trigger.",
    "FLAG": "Project control detected a non-blocking issue for review.",
    "BLOCK": "Project policy blocks downstream risk calculation before remediation.",
}


@dataclass(frozen=True)
class ControlResult:
    control_name: str
    control_status: str
    detected: bool
    blocking_control_triggered: bool
    metric_value: float
    threshold: float
    details: str


def run_control_suite(
    *,
    clean_prices: pd.DataFrame,
    candidate_prices: pd.DataFrame,
    shifted_assets: tuple[str, ...] = (),
    stale_threshold: int = STALE_PRICE_RUN_THRESHOLD,
    extreme_return_threshold: float = EXTREME_RETURN_THRESHOLD,
) -> list[ControlResult]:
    """Run all Phase 6 data-quality controls."""

    return [
        run_missingness_control(candidate_prices),
        run_staleness_control(candidate_prices, threshold=stale_threshold),
        run_extreme_return_control(candidate_prices, threshold=extreme_return_threshold),
        run_alignment_control(
            clean_prices=clean_prices,
            candidate_prices=candidate_prices,
            shifted_assets=shifted_assets,
        ),
        run_price_validity_control(candidate_prices),
    ]


def run_missingness_control(prices: pd.DataFrame) -> ControlResult:
    missing_count = int(prices.isna().sum().sum())
    missing_fraction = float(missing_count / prices.size) if prices.size else 0.0
    return ControlResult(
        control_name="missingness",
        control_status="BLOCK" if missing_count > 0 else "PASS",
        detected=missing_count > 0,
        blocking_control_triggered=missing_count > 0,
        metric_value=missing_count,
        threshold=0.0,
        details=f"missing_count={missing_count}; missing_fraction={missing_fraction:.6f}",
    )


def run_staleness_control(
    prices: pd.DataFrame,
    *,
    threshold: int = STALE_PRICE_RUN_THRESHOLD,
) -> ControlResult:
    max_run = 0
    max_asset = ""
    for asset in prices.columns:
        run = _max_consecutive_unchanged(prices[asset])
        if run > max_run:
            max_run = run
            max_asset = str(asset)
    detected = max_run >= threshold
    return ControlResult(
        control_name="staleness",
        control_status="BLOCK" if detected else "PASS",
        detected=detected,
        blocking_control_triggered=detected,
        metric_value=float(max_run),
        threshold=float(threshold),
        details=(
            f"max_consecutive_unchanged_prices={max_run}; asset={max_asset}; "
            "threshold is project-specific, not regulatory"
        ),
    )


def run_extreme_return_control(
    prices: pd.DataFrame,
    *,
    threshold: float = EXTREME_RETURN_THRESHOLD,
) -> ControlResult:
    returns = prices.pct_change(fill_method=None)
    spike_mask = returns.abs() > threshold
    spike_count = int(spike_mask.sum().sum())
    max_abs_return = float(returns.abs().max().max()) if not returns.empty else 0.0
    return ControlResult(
        control_name="extreme_return",
        control_status="BLOCK" if spike_count > 0 else "PASS",
        detected=spike_count > 0,
        blocking_control_triggered=spike_count > 0,
        metric_value=max_abs_return,
        threshold=float(threshold),
        details=(
            f"suspicious_return_count={spike_count}; max_abs_return={max_abs_return:.6f}; "
            "15% is a project QA threshold, not a regulatory threshold"
        ),
    )


def run_alignment_control(
    *,
    clean_prices: pd.DataFrame,
    candidate_prices: pd.DataFrame,
    shifted_assets: tuple[str, ...] = (),
) -> ControlResult:
    same_index = clean_prices.index.equals(candidate_prices.index)
    missing_dates = int(len(clean_prices.index.difference(candidate_prices.index)))
    shifted_detected = False
    shifted_details: list[str] = []
    for asset in shifted_assets:
        if asset in clean_prices.columns and asset in candidate_prices.columns:
            clean_shifted = clean_prices[asset].shift(1)
            comparable = pd.concat([clean_shifted, candidate_prices[asset]], axis=1).dropna()
            if not comparable.empty and np.allclose(comparable.iloc[:, 0], comparable.iloc[:, 1]):
                shifted_detected = True
                shifted_details.append(f"{asset}=clean_shift_plus_one")
    detected = (not same_index) or missing_dates > 0 or shifted_detected
    return ControlResult(
        control_name="date_alignment",
        control_status="BLOCK" if detected else "PASS",
        detected=detected,
        blocking_control_triggered=detected,
        metric_value=float(missing_dates + int(shifted_detected)),
        threshold=0.0,
        details=(
            f"same_required_index={same_index}; missing_dates={missing_dates}; "
            f"shift_detection={','.join(shifted_details) if shifted_details else 'none'}"
        ),
    )


def run_price_validity_control(prices: pd.DataFrame) -> ControlResult:
    numeric = prices.astype(float)
    invalid_mask = ~np.isfinite(numeric) | (numeric <= 0.0)
    invalid_count = int(invalid_mask.sum().sum())
    return ControlResult(
        control_name="price_validity",
        control_status="BLOCK" if invalid_count > 0 else "PASS",
        detected=invalid_count > 0,
        blocking_control_triggered=invalid_count > 0,
        metric_value=float(invalid_count),
        threshold=0.0,
        details=f"non_finite_or_non_positive_price_count={invalid_count}",
    )


def summarize_policy(results: list[ControlResult]) -> dict[str, object]:
    """Summarize a scenario's control outcome."""

    detected = any(result.detected for result in results)
    blocked = any(result.blocking_control_triggered for result in results)
    status = "BLOCK" if blocked else "FLAG" if detected else "PASS"
    return {
        "control_status": status,
        "control_detected": detected,
        "blocking_control_triggered": blocked,
        "risk_pipeline_allowed": not blocked,
    }


def controls_to_frame(
    scenario_id: str,
    scenario_name: str,
    expected_control: str,
    results: list[ControlResult],
) -> pd.DataFrame:
    """Flatten control results for artifact output."""

    rows = []
    summary = summarize_policy(results)
    expected_detected = any(
        result.control_name == expected_control and result.detected for result in results
    )
    for result in results:
        rows.append(
            {
                "scenario_id": scenario_id,
                "scenario_name": scenario_name,
                "control_name": result.control_name,
                "expected_control": expected_control,
                "control_status": result.control_status,
                "detected": bool(result.detected),
                "blocking_control_triggered": bool(result.blocking_control_triggered),
                "metric_value": result.metric_value,
                "threshold": result.threshold,
                "risk_pipeline_allowed": bool(summary["risk_pipeline_allowed"]),
                "expected_control_detected": bool(expected_detected),
                "false_negative": bool(not expected_detected),
                "details": result.details,
            }
        )
    return pd.DataFrame.from_records(rows)


def _max_consecutive_unchanged(series: pd.Series) -> int:
    clean = series.dropna()
    if clean.empty:
        return 0
    max_run = 0
    current_run = 0
    previous = None
    for value in clean:
        if previous is not None and float(value) == float(previous):
            current_run += 1
            max_run = max(max_run, current_run)
        else:
            current_run = 1
        previous = value
    return max_run
