"""Phase 5 retrospective volatility-regime analysis."""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd

from market_risk_toolkit.validation.backtesting import kupiec_unconditional_coverage

REGIME_SCOPE_LABEL = "retrospective/descriptive Phase 2 full-sample volatility regime"


def load_phase2_regimes(
    path: str | Path = "data/artifacts/rolling_distribution_diagnostics.csv",
) -> pd.DataFrame:
    """Load Phase 2 regime labels."""

    table = pd.read_csv(path, parse_dates=["date"])
    if "regime" not in table.columns:
        raise ValueError("Phase 2 rolling diagnostics must include a 'regime' column.")
    return table[["date", "regime"]].rename(columns={"regime": "volatility_regime"})


def build_regime_backtest(
    exception_diagnostics: pd.DataFrame,
    *,
    min_observations_for_test: int = 30,
    min_expected_exceptions_for_test: float = 1.0,
) -> pd.DataFrame:
    """Summarize backtesting outcomes by retrospective volatility regime."""

    table = exception_diagnostics.copy()
    table["is_exception"] = table["is_exception"].astype(int)
    table["volatility_regime"] = table["volatility_regime"].fillna("UNCLASSIFIED")
    rows: list[dict[str, float | int | str | None]] = []
    for (model_id, confidence_level), model_group in table.groupby(["model_id", "confidence_level"]):
        high_exception_count = int(
            model_group.loc[
                model_group["volatility_regime"].eq("HIGH_VOL"),
                "is_exception",
            ].sum()
        )
        total_exception_count = int(model_group["is_exception"].sum())
        high_observation_count = int(model_group["volatility_regime"].eq("HIGH_VOL").sum())
        total_observation_count = int(len(model_group))
        high_exception_fraction = (
            high_exception_count / total_exception_count if total_exception_count else np.nan
        )
        high_observation_fraction = (
            high_observation_count / total_observation_count if total_observation_count else np.nan
        )
        high_concentration_ratio = (
            high_exception_fraction / high_observation_fraction
            if high_observation_fraction and not np.isnan(high_observation_fraction)
            else np.nan
        )

        for regime, group in model_group.groupby("volatility_regime", dropna=False):
            observation_count = int(len(group))
            exception_count = int(group["is_exception"].sum())
            expected_exception_rate = float(1.0 - confidence_level)
            expected_exception_count = observation_count * expected_exception_rate
            can_test = (
                observation_count >= min_observations_for_test
                and expected_exception_count >= min_expected_exceptions_for_test
            )
            kupiec_p_value: float | None = None
            test_status = "CALCULATED"
            insufficient_reason: str | None = None
            if can_test:
                kupiec_p_value = float(kupiec_unconditional_coverage(group["is_exception"], confidence_level).p_value)
            else:
                test_status = "INSUFFICIENT_DATA"
                insufficient_reason = (
                    f"obs={observation_count}, expected_exceptions={expected_exception_count:.3f}; "
                    "below project minimum for stable regime-level p-value"
                )

            exceptions = group[group["is_exception"].eq(1)]
            rows.append(
                {
                    "model_id": str(model_id),
                    "confidence_level": float(confidence_level),
                    "volatility_regime": str(regime),
                    "regime_scope": REGIME_SCOPE_LABEL,
                    "observation_count": observation_count,
                    "expected_exception_count": float(expected_exception_count),
                    "exception_count": exception_count,
                    "exception_rate": float(exception_count / observation_count) if observation_count else np.nan,
                    "expected_exception_rate": expected_exception_rate,
                    "mean_var": float(group["var"].mean()) if observation_count else np.nan,
                    "mean_es": float(group["es"].mean()) if observation_count else np.nan,
                    "mean_realized_loss": float(group["realized_loss"].mean()) if observation_count else np.nan,
                    "average_exception_severity": (
                        float(exceptions["severity_ratio"].mean()) if len(exceptions) else np.nan
                    ),
                    "maximum_exception_severity": (
                        float(exceptions["severity_ratio"].max()) if len(exceptions) else np.nan
                    ),
                    "kupiec_p_value": kupiec_p_value,
                    "regime_test_status": test_status,
                    "insufficient_data_reason": insufficient_reason,
                    "fraction_all_exceptions_in_high_vol": high_exception_fraction,
                    "fraction_observations_in_high_vol": high_observation_fraction,
                    "high_vol_exception_concentration_ratio": high_concentration_ratio,
                }
            )
    return pd.DataFrame.from_records(rows).sort_values(
        ["confidence_level", "model_id", "volatility_regime"]
    )


def pivot_regime_exception_rates(regime_backtest: pd.DataFrame) -> pd.DataFrame:
    """Create a compact model/confidence row with LOW/NORMAL/HIGH exception rates."""

    pivot = regime_backtest.pivot_table(
        index=["model_id", "confidence_level"],
        columns="volatility_regime",
        values="exception_rate",
        aggfunc="first",
    ).reset_index()
    pivot.columns.name = None
    return pivot.rename(
        columns={
            "LOW_VOL": "low_vol_exception_rate",
            "NORMAL_VOL": "normal_vol_exception_rate",
            "HIGH_VOL": "high_vol_exception_rate",
        }
    )
