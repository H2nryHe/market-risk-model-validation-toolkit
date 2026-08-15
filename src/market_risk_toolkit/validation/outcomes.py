"""Phase 5 exception outcomes and ES diagnostics."""

from __future__ import annotations

import hashlib
from pathlib import Path
from typing import Iterable

import numpy as np
import pandas as pd

CLUSTER_GAP_OBSERVATIONS = 5


def sha256_file(path: str | Path) -> str:
    """Return the SHA-256 digest for a local file."""

    digest = hashlib.sha256()
    with Path(path).open("rb") as file:
        for chunk in iter(lambda: file.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def build_exception_diagnostics(
    forecasts: pd.DataFrame,
    regimes: pd.DataFrame,
) -> pd.DataFrame:
    """Create date-level exception diagnostics for every model/confidence pair."""

    required = {
        "date",
        "model_id",
        "confidence_level",
        "var",
        "es",
        "realized_loss",
    }
    missing = required.difference(forecasts.columns)
    if missing:
        raise ValueError(f"Forecast table missing required columns: {sorted(missing)}")

    table = forecasts.copy(deep=True)
    table["date"] = pd.to_datetime(table["date"])
    table = table.sort_values(["model_id", "confidence_level", "date"]).reset_index(drop=True)
    table["is_exception"] = table["realized_loss"] > table["var"]
    table["exceedance_amount"] = np.where(
        table["is_exception"],
        table["realized_loss"] - table["var"],
        0.0,
    )
    table["severity_ratio"] = np.where(
        table["is_exception"] & (table["var"].abs() > 1.0e-12),
        table["realized_loss"] / table["var"],
        np.nan,
    )

    spacing = []
    for _, group in table.groupby(["model_id", "confidence_level"], sort=False):
        previous_exception_position: int | None = None
        for position, is_exception in enumerate(group["is_exception"].to_numpy(dtype=bool)):
            if is_exception:
                spacing.append(
                    np.nan
                    if previous_exception_position is None
                    else position - previous_exception_position
                )
                previous_exception_position = position
            else:
                spacing.append(np.nan)
    table["days_since_previous_exception"] = spacing

    regime_map = _normalize_regimes(regimes)
    table = table.merge(regime_map, on="date", how="left")
    table["volatility_regime"] = table["volatility_regime"].fillna("UNCLASSIFIED")
    output_columns = [
        "date",
        "model_id",
        "model_name",
        "confidence_level",
        "var",
        "es",
        "realized_loss",
        "is_exception",
        "exceedance_amount",
        "severity_ratio",
        "days_since_previous_exception",
        "volatility_regime",
    ]
    present = [column for column in output_columns if column in table.columns]
    return table[present].assign(date=lambda frame: frame["date"].dt.strftime("%Y-%m-%d"))


def build_cluster_summary(
    exception_diagnostics: pd.DataFrame,
    *,
    cluster_gap_observations: int = CLUSTER_GAP_OBSERVATIONS,
) -> pd.DataFrame:
    """Summarize exception clustering by model/confidence pair."""

    rows: list[dict[str, float | int | str]] = []
    table = exception_diagnostics.copy()
    table["date"] = pd.to_datetime(table["date"])
    table["is_exception"] = table["is_exception"].astype(bool)
    for (model_id, confidence_level), group in table.groupby(["model_id", "confidence_level"]):
        ordered = group.sort_values("date").reset_index(drop=True)
        exception_positions = ordered.index[ordered["is_exception"]].to_numpy(dtype=int)
        gaps = np.diff(exception_positions)
        cluster_lengths = _cluster_lengths(exception_positions, cluster_gap_observations)
        consecutive_lengths = _cluster_lengths(exception_positions, 1)
        exception_count = int(len(exception_positions))
        observation_count = int(len(ordered))
        rows.append(
            {
                "model_id": str(model_id),
                "confidence_level": float(confidence_level),
                "observation_count": observation_count,
                "exception_count": exception_count,
                "exception_rate": float(exception_count / observation_count) if observation_count else np.nan,
                "expected_exception_rate": float(1.0 - confidence_level),
                "longest_consecutive_exception_run": int(max(consecutive_lengths, default=0)),
                "cluster_gap_observations": int(cluster_gap_observations),
                "cluster_definition": (
                    "project diagnostic: adjacent exceptions separated by <=5 trading "
                    "observations are assigned to the same cluster; not a regulatory threshold"
                ),
                "number_of_clusters": int(len(cluster_lengths)),
                "mean_cluster_length": float(np.mean(cluster_lengths)) if cluster_lengths else np.nan,
                "max_cluster_length": int(max(cluster_lengths, default=0)),
                "median_days_between_exceptions": float(np.median(gaps)) if gaps.size else np.nan,
                "min_days_between_exceptions": int(np.min(gaps)) if gaps.size else np.nan,
                "fraction_exceptions_within_5_days": _fraction_nearby_exception(exception_positions, 5),
                "fraction_exceptions_within_10_days": _fraction_nearby_exception(exception_positions, 10),
                "average_exception_severity": _safe_mean(ordered.loc[ordered["is_exception"], "severity_ratio"]),
                "maximum_exception_severity": _safe_max(ordered.loc[ordered["is_exception"], "severity_ratio"]),
            }
        )
    return pd.DataFrame.from_records(rows).sort_values(["confidence_level", "model_id"])


def build_rolling_exception_rates(
    exception_diagnostics: pd.DataFrame,
    *,
    windows: Iterable[int] = (125, 250),
) -> pd.DataFrame:
    """Calculate trailing exception rates without centered or future data."""

    table = exception_diagnostics.copy()
    table["date"] = pd.to_datetime(table["date"])
    table["is_exception"] = table["is_exception"].astype(int)
    outputs = []
    for _, group in table.groupby(["model_id", "confidence_level"], sort=False):
        ordered = group.sort_values("date").copy()
        for window in windows:
            ordered[f"rolling_exception_rate_{int(window)}"] = (
                ordered["is_exception"].rolling(window=int(window), min_periods=1).mean()
            )
        outputs.append(ordered)
    result = pd.concat(outputs, ignore_index=True)
    return result.sort_values(["date", "confidence_level", "model_id"]).assign(
        date=lambda frame: frame["date"].dt.strftime("%Y-%m-%d")
    )


def build_es_diagnostics(exception_diagnostics: pd.DataFrame) -> pd.DataFrame:
    """Create descriptive ES diagnostics conditional on VaR exceptions."""

    rows = []
    table = exception_diagnostics.copy()
    table["is_exception"] = table["is_exception"].astype(bool)
    for (model_id, confidence_level), group in table.groupby(["model_id", "confidence_level"]):
        exceptions = group[group["is_exception"]]
        mean_es = _safe_mean(exceptions["es"])
        mean_loss = _safe_mean(exceptions["realized_loss"])
        rows.append(
            {
                "model_id": str(model_id),
                "confidence_level": float(confidence_level),
                "observation_count": int(len(group)),
                "exception_count": int(len(exceptions)),
                "mean_forecast_es_on_exception_dates": mean_es,
                "mean_realized_loss_on_exception_dates": mean_loss,
                "mean_realized_loss_minus_es": mean_loss - mean_es if not np.isnan(mean_loss + mean_es) else np.nan,
                "realized_loss_to_es_ratio": mean_loss / mean_es if mean_es and not np.isnan(mean_es) else np.nan,
                "fraction_exceptions_exceeding_es": (
                    float((exceptions["realized_loss"] > exceptions["es"]).mean())
                    if len(exceptions)
                    else np.nan
                ),
                "average_es_to_var_ratio": _safe_mean(group["es"] / group["var"].where(group["var"].abs() > 1.0e-12)),
                "diagnostic_scope": "descriptive ES outcome diagnostic; not a definitive regulatory ES backtest",
            }
        )
    return pd.DataFrame.from_records(rows).sort_values(["confidence_level", "model_id"])


def top_exception_dates(
    exception_diagnostics: pd.DataFrame,
    *,
    count: int = 5,
) -> pd.DataFrame:
    """Return the largest exception severity rows for report display."""

    table = exception_diagnostics.copy()
    table["is_exception"] = table["is_exception"].astype(bool)
    return (
        table[table["is_exception"]]
        .sort_values("severity_ratio", ascending=False)
        .head(count)
        .reset_index(drop=True)
    )


def _normalize_regimes(regimes: pd.DataFrame) -> pd.DataFrame:
    table = regimes.copy()
    table["date"] = pd.to_datetime(table["date"])
    if "volatility_regime" not in table.columns:
        if "regime" not in table.columns:
            raise ValueError("Regime table must contain 'regime' or 'volatility_regime'.")
        table["volatility_regime"] = table["regime"]
    table["volatility_regime"] = table["volatility_regime"].fillna("UNCLASSIFIED")
    return table[["date", "volatility_regime"]].drop_duplicates("date")


def _cluster_lengths(exception_positions: np.ndarray, gap: int) -> list[int]:
    if exception_positions.size == 0:
        return []
    lengths = [1]
    for distance in np.diff(exception_positions):
        if distance <= gap:
            lengths[-1] += 1
        else:
            lengths.append(1)
    return lengths


def _fraction_nearby_exception(exception_positions: np.ndarray, gap: int) -> float:
    if exception_positions.size == 0:
        return np.nan
    nearby = []
    for index, position in enumerate(exception_positions):
        previous_gap = position - exception_positions[index - 1] if index > 0 else np.inf
        next_gap = exception_positions[index + 1] - position if index < len(exception_positions) - 1 else np.inf
        nearby.append(previous_gap <= gap or next_gap <= gap)
    return float(np.mean(nearby))


def _safe_mean(values: pd.Series) -> float:
    clean = pd.Series(values).dropna()
    return float(clean.mean()) if not clean.empty else np.nan


def _safe_max(values: pd.Series) -> float:
    clean = pd.Series(values).dropna()
    return float(clean.max()) if not clean.empty else np.nan
