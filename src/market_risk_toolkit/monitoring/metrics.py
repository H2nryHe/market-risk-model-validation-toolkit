"""Phase 7 monitoring metrics and traffic-light status rules."""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd

from market_risk_toolkit.validation.backtesting import (
    christoffersen_conditional_coverage_test,
    kupiec_unconditional_coverage,
)

GREEN = "GREEN"
AMBER = "AMBER"
RED = "RED"
INSUFFICIENT_DATA = "INSUFFICIENT_DATA"


@dataclass(frozen=True)
class VolatilityCalibration:
    calibration_start: str
    calibration_end: str
    lower_threshold: float
    upper_threshold: float
    rolling_window: int
    calibration_observations: int
    methodology: str


def calculate_rolling_exception_rate(exceptions: pd.Series, window: int) -> pd.Series:
    """Calculate trailing exception rates."""

    sequence = exceptions.astype(int).copy()
    return sequence.rolling(window=window, min_periods=window).mean()


def calculate_rolling_p_values(
    exceptions: pd.Series,
    *,
    confidence_level: float,
    window: int,
    min_exception_count_for_dependence_test: int,
) -> pd.DataFrame:
    """Calculate trailing Kupiec and conditional-coverage p-values."""

    sequence = exceptions.astype(int).copy()
    rows = []
    for position, date in enumerate(sequence.index):
        if position + 1 < window:
            rows.append(
                {
                    "date": date,
                    "kupiec_p_value_250": np.nan,
                    "conditional_coverage_p_value_250": np.nan,
                    "kupiec_status": INSUFFICIENT_DATA,
                    "conditional_coverage_status": INSUFFICIENT_DATA,
                }
            )
            continue
        trailing = sequence.iloc[position + 1 - window : position + 1]
        kupiec = kupiec_unconditional_coverage(trailing, confidence_level)
        exception_count = int(trailing.sum())
        conditional_p = np.nan
        conditional_status = INSUFFICIENT_DATA
        if exception_count >= min_exception_count_for_dependence_test and _has_valid_transition_structure(trailing):
            conditional = christoffersen_conditional_coverage_test(trailing, confidence_level)
            conditional_p = float(conditional.p_value)
            conditional_status = ""
        rows.append(
            {
                "date": date,
                "kupiec_p_value_250": float(kupiec.p_value),
                "conditional_coverage_p_value_250": conditional_p,
                "kupiec_status": "",
                "conditional_coverage_status": conditional_status,
            }
        )
    result = pd.DataFrame.from_records(rows).set_index("date")
    return result


def calculate_recent_exception_counts(exceptions: pd.Series) -> pd.DataFrame:
    """Calculate causal recent exception counts and spacing."""

    sequence = exceptions.astype(int).copy()
    last_exception_position: int | None = None
    rows = []
    for position, (date, value) in enumerate(sequence.items()):
        start_5 = max(0, position - 4)
        start_10 = max(0, position - 9)
        if int(value) == 1:
            last_exception_position = position
        rows.append(
            {
                "date": date,
                "exceptions_last_5d": int(sequence.iloc[start_5 : position + 1].sum()),
                "exceptions_last_10d": int(sequence.iloc[start_10 : position + 1].sum()),
                "days_since_last_exception": (
                    np.nan if last_exception_position is None else int(position - last_exception_position)
                ),
            }
        )
    return pd.DataFrame.from_records(rows).set_index("date")


def calculate_challenger_divergence(
    mr001_var: pd.Series,
    challenger_var: pd.Series,
) -> pd.Series:
    """Calculate absolute relative challenger VaR divergence from MR-001."""

    baseline = mr001_var.astype(float).copy()
    challenger = challenger_var.astype(float).copy()
    denominator = baseline.where(baseline.abs() > 1.0e-12)
    return ((challenger - baseline).abs() / denominator).replace([np.inf, -np.inf], np.nan)


def assign_exception_rate_status(
    exception_rate: float | None,
    *,
    confidence_level: float,
    amber_multiplier: float,
    red_multiplier: float,
) -> str:
    if exception_rate is None or pd.isna(exception_rate):
        return INSUFFICIENT_DATA
    expected = 1.0 - confidence_level
    if exception_rate > expected * red_multiplier:
        return RED
    if exception_rate > expected * amber_multiplier:
        return AMBER
    return GREEN


def assign_p_value_status(
    p_value: float | None,
    *,
    red_p_value: float,
    amber_p_value: float,
) -> str:
    if p_value is None or pd.isna(p_value):
        return INSUFFICIENT_DATA
    if p_value < red_p_value:
        return RED
    if p_value < amber_p_value:
        return AMBER
    return GREEN


def assign_cluster_status(
    exceptions_last_10d: int | float | None,
    *,
    amber_exception_count: int,
    red_exception_count: int,
) -> str:
    if exceptions_last_10d is None or pd.isna(exceptions_last_10d):
        return INSUFFICIENT_DATA
    if int(exceptions_last_10d) >= red_exception_count:
        return RED
    if int(exceptions_last_10d) >= amber_exception_count:
        return AMBER
    return GREEN


def assign_challenger_divergence_status(
    divergence: float | None,
    *,
    amber_threshold: float,
    red_threshold: float,
) -> str:
    if divergence is None or pd.isna(divergence):
        return INSUFFICIENT_DATA
    if divergence >= red_threshold:
        return RED
    if divergence >= amber_threshold:
        return AMBER
    return GREEN


def assign_far_tail_performance_watch(
    *,
    exception_rate_status: str,
    kupiec_status: str,
    challenger_divergence_status: str,
) -> str:
    """Aggregate far-tail performance with challenger disagreement as context.

    Challenger divergence can raise review priority to AMBER, but it does not
    create a hard RED model-performance state without MR-001 performance
    evidence from exception frequency or Kupiec coverage.
    """

    if exception_rate_status == RED or kupiec_status == RED:
        return RED
    if (
        exception_rate_status == AMBER
        or kupiec_status == AMBER
        or challenger_divergence_status in {AMBER, RED}
    ):
        return AMBER
    if (
        exception_rate_status == GREEN
        and kupiec_status == GREEN
        and challenger_divergence_status == GREEN
    ):
        return GREEN
    return INSUFFICIENT_DATA


def assign_dependence_watch_status(
    *,
    conditional_coverage_status: str,
    cluster_status: str,
) -> str:
    """Combine conditional coverage and recent clustering into one watch state."""

    if cluster_status == RED:
        return RED
    if conditional_coverage_status == RED and cluster_status in {AMBER, RED}:
        return RED
    if conditional_coverage_status in {RED, AMBER} or cluster_status == AMBER:
        return AMBER
    if conditional_coverage_status == GREEN and cluster_status == GREEN:
        return GREEN
    if cluster_status in {AMBER, RED}:
        return cluster_status
    return INSUFFICIENT_DATA


def aggregate_overall_status_v1_1(
    *,
    data_quality_status: str,
    far_tail_performance_watch: str,
    dependence_watch_status: str,
    exception_rate_status: str,
    kupiec_status: str,
    challenger_review_required: bool,
    high_vol_tail_escalation: bool,
) -> str:
    """Aggregate v1.1 monitoring status by governance role precedence."""

    if data_quality_status in {"BLOCK", RED}:
        return RED
    if far_tail_performance_watch == RED:
        return RED
    if dependence_watch_status == RED:
        return RED
    if (
        far_tail_performance_watch == AMBER
        or dependence_watch_status == AMBER
        or exception_rate_status == AMBER
        or kupiec_status == AMBER
    ):
        return AMBER
    if challenger_review_required:
        return AMBER
    if high_vol_tail_escalation:
        return AMBER
    if (
        far_tail_performance_watch == INSUFFICIENT_DATA
        or dependence_watch_status == INSUFFICIENT_DATA
        or exception_rate_status == INSUFFICIENT_DATA
        or kupiec_status == INSUFFICIENT_DATA
    ):
        return INSUFFICIENT_DATA
    return GREEN


def aggregate_overall_status(component_statuses: list[str], *, data_quality_status: str = GREEN) -> str:
    """Aggregate statuses by deterministic precedence."""

    if data_quality_status in {"BLOCK", RED}:
        return RED
    if RED in component_statuses:
        return RED
    if AMBER in component_statuses:
        return AMBER
    if INSUFFICIENT_DATA in component_statuses:
        return INSUFFICIENT_DATA
    return GREEN


def calibrate_volatility_regime(
    returns: pd.Series,
    *,
    rolling_window: int,
    calibration_observations: int,
    lower_quantile: float,
    upper_quantile: float,
) -> tuple[pd.Series, VolatilityCalibration]:
    """Calibrate live-safe volatility regimes from initial rolling observations."""

    rolling_vol = returns.astype(float).copy().rolling(window=rolling_window, min_periods=rolling_window).std(ddof=1)
    valid = rolling_vol.dropna()
    if len(valid) < calibration_observations:
        raise ValueError("Not enough valid rolling volatility observations for calibration.")
    calibration_sample = valid.iloc[:calibration_observations]
    lower = float(calibration_sample.quantile(lower_quantile))
    upper = float(calibration_sample.quantile(upper_quantile))
    regimes = classify_volatility_regime(rolling_vol, lower_threshold=lower, upper_threshold=upper)
    metadata = VolatilityCalibration(
        calibration_start=calibration_sample.index.min().strftime("%Y-%m-%d"),
        calibration_end=calibration_sample.index.max().strftime("%Y-%m-%d"),
        lower_threshold=lower,
        upper_threshold=upper,
        rolling_window=rolling_window,
        calibration_observations=calibration_observations,
        methodology=(
            "Trailing 60-day volatility thresholds calibrated on the first 500 valid "
            "rolling-volatility observations and then frozen for historical replay."
        ),
    )
    return regimes, metadata


def classify_volatility_regime(
    rolling_volatility: pd.Series,
    *,
    lower_threshold: float,
    upper_threshold: float,
) -> pd.Series:
    values = rolling_volatility.copy()
    regimes = pd.Series(index=values.index, dtype=object)
    regimes[values <= lower_threshold] = "LOW_VOL"
    regimes[(values > lower_threshold) & (values < upper_threshold)] = "NORMAL_VOL"
    regimes[values >= upper_threshold] = "HIGH_VOL"
    regimes[values.isna()] = "INSUFFICIENT_DATA"
    return regimes


def _has_valid_transition_structure(exceptions: pd.Series) -> bool:
    sequence = exceptions.astype(int).to_numpy()
    if len(sequence) < 2:
        return False
    previous = sequence[:-1]
    current = sequence[1:]
    return bool(len(set(zip(previous, current, strict=False))) >= 2)
