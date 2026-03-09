"""Backtesting logic for VaR model validation.

Realized loss is defined as `-portfolio_return`. Exceedances occur when realized
loss is larger than the model's positive VaR forecast. This aligns with the
usual validation convention that VaR is reported as a positive loss threshold.
"""

from __future__ import annotations

import math
from dataclasses import dataclass

import numpy as np
import pandas as pd
from scipy.stats import chi2


@dataclass(frozen=True)
class LikelihoodRatioTestResult:
    """Likelihood-ratio test output."""

    statistic: float
    p_value: float


def build_exceedance_table(
    risk_table: pd.DataFrame,
    confidence_levels: tuple[float, ...],
) -> pd.DataFrame:
    """Append realized loss and exceedance indicators to the rolling risk table."""

    table = risk_table.copy()
    table["realized_loss"] = -table["portfolio_return"]

    for level in confidence_levels:
        suffix = _format_confidence_level(level)
        for model in ("historical", "parametric"):
            var_column = f"{model}_var_{suffix}"
            exceedance_column = f"{model}_exceedance_{suffix}"
            if var_column not in table.columns:
                raise ValueError(f"Expected VaR column '{var_column}' in the risk table.")
            table[exceedance_column] = (table["realized_loss"] > table[var_column]).astype(int)
    return table


def kupiec_unconditional_coverage(
    exceedances: pd.Series | np.ndarray | list[int],
    confidence_level: float,
) -> LikelihoodRatioTestResult:
    """Kupiec unconditional coverage test.

    Null hypothesis: the exception rate equals the nominal VaR tail probability.
    """

    sequence = _coerce_exceedance_sequence(exceedances)
    observation_count = len(sequence)
    exception_count = int(sequence.sum())
    failure_probability = 1.0 - confidence_level
    empirical_probability = exception_count / observation_count

    null_log_likelihood = _binomial_log_likelihood(
        observation_count=observation_count,
        exception_count=exception_count,
        probability=failure_probability,
    )
    empirical_log_likelihood = _binomial_log_likelihood(
        observation_count=observation_count,
        exception_count=exception_count,
        probability=empirical_probability,
    )
    statistic = max(0.0, -2.0 * (null_log_likelihood - empirical_log_likelihood))
    return LikelihoodRatioTestResult(statistic=statistic, p_value=float(chi2.sf(statistic, df=1)))


def christoffersen_independence_test(
    exceedances: pd.Series | np.ndarray | list[int],
) -> LikelihoodRatioTestResult:
    """Christoffersen independence test for exception clustering."""

    sequence = _coerce_exceedance_sequence(exceedances)
    if len(sequence) < 2:
        raise ValueError("Christoffersen test requires at least two observations.")

    n00, n01, n10, n11 = _transition_counts(sequence)
    total_transitions = n00 + n01 + n10 + n11
    pooled_probability = (n01 + n11) / total_transitions if total_transitions else 0.0
    probability_01 = n01 / (n00 + n01) if (n00 + n01) else 0.0
    probability_11 = n11 / (n10 + n11) if (n10 + n11) else 0.0

    restricted = (
        _safe_log_power(1.0 - pooled_probability, n00 + n10)
        + _safe_log_power(pooled_probability, n01 + n11)
    )
    unrestricted = (
        _safe_log_power(1.0 - probability_01, n00)
        + _safe_log_power(probability_01, n01)
        + _safe_log_power(1.0 - probability_11, n10)
        + _safe_log_power(probability_11, n11)
    )
    statistic = max(0.0, -2.0 * (restricted - unrestricted))
    return LikelihoodRatioTestResult(statistic=statistic, p_value=float(chi2.sf(statistic, df=1)))


def christoffersen_conditional_coverage_test(
    exceedances: pd.Series | np.ndarray | list[int],
    confidence_level: float,
) -> LikelihoodRatioTestResult:
    """Christoffersen conditional coverage test.

    Combines Kupiec coverage and Christoffersen independence into a single test.
    """

    kupiec_result = kupiec_unconditional_coverage(exceedances, confidence_level)
    independence_result = christoffersen_independence_test(exceedances)
    statistic = kupiec_result.statistic + independence_result.statistic
    return LikelihoodRatioTestResult(statistic=statistic, p_value=float(chi2.sf(statistic, df=2)))


def summarize_backtests(
    exceedance_table: pd.DataFrame,
    confidence_levels: tuple[float, ...],
) -> pd.DataFrame:
    """Create a model comparison table across VaR methods and confidence levels."""

    records: list[dict[str, float | int | str | bool]] = []
    observation_count = int(len(exceedance_table))
    for level in confidence_levels:
        suffix = _format_confidence_level(level)
        expected_rate = 1.0 - level
        for model in ("historical", "parametric"):
            exceedance_column = f"{model}_exceedance_{suffix}"
            sequence = exceedance_table[exceedance_column]
            kupiec_result = kupiec_unconditional_coverage(sequence, level)
            independence_result = christoffersen_independence_test(sequence)
            conditional_result = christoffersen_conditional_coverage_test(sequence, level)
            exception_count = int(sequence.sum())
            exception_rate = exception_count / observation_count
            records.append(
                {
                    "model": model,
                    "confidence_level": level,
                    "observation_count": observation_count,
                    "expected_exception_rate": expected_rate,
                    "exception_count": exception_count,
                    "exception_rate": exception_rate,
                    "kupiec_lr": kupiec_result.statistic,
                    "kupiec_p_value": kupiec_result.p_value,
                    "christoffersen_independence_lr": independence_result.statistic,
                    "christoffersen_independence_p_value": independence_result.p_value,
                    "christoffersen_cc_lr": conditional_result.statistic,
                    "christoffersen_cc_p_value": conditional_result.p_value,
                    "passes_5pct_coverage": kupiec_result.p_value >= 0.05,
                    "passes_5pct_conditional_coverage": conditional_result.p_value >= 0.05,
                    "interpretation": interpret_backtest_result(
                        model=model,
                        confidence_level=level,
                        exception_rate=exception_rate,
                        expected_rate=expected_rate,
                        kupiec_p_value=kupiec_result.p_value,
                        independence_p_value=independence_result.p_value,
                        conditional_p_value=conditional_result.p_value,
                    ),
                }
            )
    return pd.DataFrame.from_records(records)


def interpret_backtest_result(
    model: str,
    confidence_level: float,
    exception_rate: float,
    expected_rate: float,
    kupiec_p_value: float,
    independence_p_value: float,
    conditional_p_value: float,
) -> str:
    """Generate concise interpretation text for memo-style outputs."""

    coverage_view = "coverage is broadly consistent with the nominal tail rate"
    if exception_rate > expected_rate and kupiec_p_value < 0.05:
        coverage_view = "exceptions are too frequent, suggesting VaR underestimates risk"
    elif exception_rate < expected_rate and kupiec_p_value < 0.05:
        coverage_view = "exceptions are too infrequent, suggesting VaR may be overly conservative"

    clustering_view = "exceptions do not show strong clustering at the 5% level"
    if conditional_p_value < 0.05:
        clustering_view = "exceptions appear clustered, which weakens conditional coverage"
    elif independence_p_value < 0.05:
        clustering_view = "the independence test shows some clustering, but conditional coverage is not rejected"

    suffix = int(round(confidence_level * 100))
    return f"{model.capitalize()} VaR {suffix}%: {coverage_view}; {clustering_view}."


def _coerce_exceedance_sequence(
    exceedances: pd.Series | np.ndarray | list[int],
) -> np.ndarray:
    sequence = np.asarray(exceedances, dtype=int)
    if sequence.ndim != 1:
        raise ValueError("Exceedance sequence must be one-dimensional.")
    if len(sequence) == 0:
        raise ValueError("Exceedance sequence must not be empty.")
    if not np.isin(sequence, [0, 1]).all():
        raise ValueError("Exceedance sequence must contain only 0/1 values.")
    return sequence


def _binomial_log_likelihood(
    observation_count: int,
    exception_count: int,
    probability: float,
) -> float:
    return _safe_log_power(probability, exception_count) + _safe_log_power(
        1.0 - probability,
        observation_count - exception_count,
    )


def _transition_counts(sequence: np.ndarray) -> tuple[int, int, int, int]:
    previous = sequence[:-1]
    current = sequence[1:]
    n00 = int(np.sum((previous == 0) & (current == 0)))
    n01 = int(np.sum((previous == 0) & (current == 1)))
    n10 = int(np.sum((previous == 1) & (current == 0)))
    n11 = int(np.sum((previous == 1) & (current == 1)))
    return n00, n01, n10, n11


def _safe_log_power(probability: float, count: int) -> float:
    if count == 0:
        return 0.0
    if probability <= 0.0:
        return -math.inf
    if probability >= 1.0:
        return 0.0 if count == 0 else 0.0
    return count * math.log(probability)


def _format_confidence_level(confidence_level: float) -> str:
    return str(int(round(confidence_level * 100)))
