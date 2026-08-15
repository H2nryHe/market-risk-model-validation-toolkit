"""Phase 7 monitoring pipeline."""

from __future__ import annotations

import argparse
import json
from dataclasses import asdict, dataclass
from datetime import date, timedelta
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

from market_risk_toolkit.data_quality.controls import run_control_suite, summarize_policy
from market_risk_toolkit.data_quality.perturbations import load_price_panel
from market_risk_toolkit.monitoring.metrics import (
    AMBER,
    GREEN,
    INSUFFICIENT_DATA,
    RED,
    aggregate_overall_status_v1_1,
    assign_challenger_divergence_status,
    assign_cluster_status,
    assign_dependence_watch_status,
    assign_exception_rate_status,
    assign_far_tail_performance_watch,
    assign_p_value_status,
    calculate_challenger_divergence,
    calculate_recent_exception_counts,
    calculate_rolling_exception_rate,
    calculate_rolling_p_values,
    calibrate_volatility_regime,
)
from market_risk_toolkit.monitoring.thresholds import (
    MonitoringThresholds,
    load_monitoring_thresholds,
)
from market_risk_toolkit.risk.io import load_portfolio_returns
from market_risk_toolkit.validation.outcomes import sha256_file


@dataclass(frozen=True)
class MonitoringPaths:
    history_csv: Path
    snapshot_csv: Path
    breaches_csv: Path
    summary_json: Path
    framework_comparison_csv: Path
    remediation_log_csv: Path
    report_md: Path


REMEDIATION_COLUMNS = [
    "remediation_id",
    "finding_id",
    "action",
    "owner_role",
    "status",
    "target_date",
    "completion_date",
    "evidence",
]


def run_monitoring_pipeline(
    *,
    thresholds_path: str | Path = "configs/monitoring/thresholds.yaml",
    forecasts_path: str | Path = "data/artifacts/challenger_forecasts.csv",
    portfolio_returns_path: str | Path = "data/artifacts/baseline_multi_asset_equal_weight_timeseries.csv",
    price_path: str | Path = "data/processed/adjusted_close.csv",
    findings_path: str | Path = "governance/findings.csv",
    output_dir: str | Path = "data/artifacts",
    remediation_log_path: str | Path = "governance/remediation_log.csv",
    report_path: str | Path = "reports/monitoring_report.md",
    v1_history_path: str | Path = "data/artifacts/monitoring_v1_0/monitoring_history.csv",
    v1_summary_path: str | Path = "data/artifacts/monitoring_v1_0/monitoring_summary.json",
    v1_thresholds_path: str | Path = "configs/monitoring/thresholds_v1_0.yaml",
) -> MonitoringPaths:
    """Generate Phase 7 monitoring artifacts."""

    output = Path(output_dir)
    output.mkdir(parents=True, exist_ok=True)
    remediation_log = Path(remediation_log_path)
    remediation_log.parent.mkdir(parents=True, exist_ok=True)
    report = Path(report_path)
    report.parent.mkdir(parents=True, exist_ok=True)
    paths = MonitoringPaths(
        history_csv=output / "monitoring_history.csv",
        snapshot_csv=output / "monitoring_snapshot.csv",
        breaches_csv=output / "monitoring_breaches.csv",
        summary_json=output / "monitoring_summary.json",
        framework_comparison_csv=output / "monitoring_framework_comparison.csv",
        remediation_log_csv=remediation_log,
        report_md=report,
    )

    thresholds = load_monitoring_thresholds(thresholds_path)
    forecasts = pd.read_csv(forecasts_path)
    portfolio_returns = load_portfolio_returns(portfolio_returns_path)
    prices = load_price_panel(str(price_path))
    findings = pd.read_csv(findings_path, keep_default_na=False)

    data_quality_status = _data_quality_status(prices, thresholds)
    regimes, calibration = calibrate_volatility_regime(
        portfolio_returns,
        rolling_window=thresholds.volatility_window,
        calibration_observations=thresholds.volatility_calibration_observations,
        lower_quantile=thresholds.volatility_lower_quantile,
        upper_quantile=thresholds.volatility_upper_quantile,
    )
    volatility = portfolio_returns.rolling(
        window=thresholds.volatility_window,
        min_periods=thresholds.volatility_window,
    ).std(ddof=1)

    history = build_monitoring_history(
        forecasts=forecasts,
        volatility=volatility,
        regimes=regimes,
        thresholds=thresholds,
        data_quality_status=data_quality_status,
        open_findings=findings["finding_id"].tolist(),
    )
    snapshot = build_monitoring_snapshot(history, findings=findings)
    breaches = build_breach_log(history, thresholds=thresholds)
    v1_history = pd.read_csv(v1_history_path)
    framework_comparison = build_framework_comparison(v1_history=v1_history, v1_1_history=history)
    remediation = build_remediation_log(
        effective_date=thresholds.effective_date,
        evidence_paths=[
            str(paths.history_csv),
            str(paths.breaches_csv),
            str(paths.snapshot_csv),
            str(paths.framework_comparison_csv),
            str(thresholds_path),
            str(v1_thresholds_path),
            str(v1_summary_path),
            str(report_path),
        ],
    )
    summary = build_monitoring_summary(
        thresholds=thresholds,
        portfolio_returns_path=Path(portfolio_returns_path),
        forecasts_path=Path(forecasts_path),
        history=history,
        snapshot=snapshot,
        breaches=breaches,
        findings=findings,
        remediation=remediation,
        volatility_calibration=calibration,
        framework_comparison=framework_comparison,
        v1_thresholds_path=Path(v1_thresholds_path),
        v1_summary_path=Path(v1_summary_path),
    )

    history.to_csv(paths.history_csv, index=False)
    snapshot.to_csv(paths.snapshot_csv, index=False)
    breaches.to_csv(paths.breaches_csv, index=False)
    framework_comparison.to_csv(paths.framework_comparison_csv, index=False)
    remediation.to_csv(paths.remediation_log_csv, index=False)
    summary["artifact_hashes"] = {
        "monitoring_history_csv": sha256_file(paths.history_csv),
        "monitoring_snapshot_csv": sha256_file(paths.snapshot_csv),
        "monitoring_breaches_csv": sha256_file(paths.breaches_csv),
        "monitoring_framework_comparison_csv": sha256_file(paths.framework_comparison_csv),
        "remediation_log_csv": sha256_file(paths.remediation_log_csv),
    }
    paths.summary_json.write_text(_json_dumps(summary), encoding="utf-8")
    paths.report_md.write_text(
        render_monitoring_report(
            summary=summary,
            snapshot=snapshot,
            breaches=breaches,
            remediation=remediation,
            thresholds=thresholds,
            framework_comparison=framework_comparison,
        ),
        encoding="utf-8",
    )
    return paths


def build_monitoring_history(
    *,
    forecasts: pd.DataFrame,
    volatility: pd.Series,
    regimes: pd.Series,
    thresholds: MonitoringThresholds,
    data_quality_status: str,
    open_findings: list[str],
) -> pd.DataFrame:
    """Build long-form monitoring history for MR-001 confidence levels."""

    table = forecasts.copy()
    table["date"] = pd.to_datetime(table["date"])
    rows = []
    pivot_var = table.pivot_table(
        index=["date", "confidence_level"],
        columns="model_id",
        values="var",
        aggfunc="first",
    )
    pivot_es = table.pivot_table(
        index=["date", "confidence_level"],
        columns="model_id",
        values="es",
        aggfunc="first",
    )
    realized = table[table["model_id"].eq("MR-001")].set_index(["date", "confidence_level"])[
        "realized_loss"
    ]

    for confidence_level in (0.95, 0.99):
        index = pivot_var.xs(confidence_level, level="confidence_level").index.sort_values()
        mr001_var = pivot_var.xs(confidence_level, level="confidence_level").loc[index, "MR-001"]
        mr001_es = pivot_es.xs(confidence_level, level="confidence_level").loc[index, "MR-001"]
        losses = realized.xs(confidence_level, level="confidence_level").loc[index]
        exceptions = (losses > mr001_var).astype(int)
        rolling_125 = calculate_rolling_exception_rate(exceptions, thresholds.exception_short_window)
        rolling_250 = calculate_rolling_exception_rate(exceptions, thresholds.exception_long_window)
        p_values = calculate_rolling_p_values(
            exceptions,
            confidence_level=confidence_level,
            window=thresholds.statistical_window,
            min_exception_count_for_dependence_test=thresholds.min_exception_count_for_dependence_test,
        )
        recent = calculate_recent_exception_counts(exceptions)
        level_var = pivot_var.xs(confidence_level, level="confidence_level").loc[index]
        divergences = {
            model_id: calculate_challenger_divergence(mr001_var, level_var[model_id])
            for model_id in ("MR-002", "MR-003", "MR-004")
        }

        for monitoring_date in index:
            date_key = pd.Timestamp(monitoring_date)
            date_text = date_key.strftime("%Y-%m-%d")
            div_values = {model_id: divergences[model_id].loc[date_key] for model_id in divergences}
            max_divergence = _max_or_nan(list(div_values.values()))
            exception_rate_status = assign_exception_rate_status(
                rolling_250.loc[date_key],
                confidence_level=confidence_level,
                amber_multiplier=thresholds.exception_rate_amber_multiplier,
                red_multiplier=thresholds.exception_rate_red_multiplier,
            )
            kupiec_status = p_values.loc[date_key, "kupiec_status"] or assign_p_value_status(
                p_values.loc[date_key, "kupiec_p_value_250"],
                red_p_value=thresholds.statistical_red_p_value,
                amber_p_value=thresholds.statistical_amber_p_value,
            )
            cc_status = p_values.loc[date_key, "conditional_coverage_status"] or assign_p_value_status(
                p_values.loc[date_key, "conditional_coverage_p_value_250"],
                red_p_value=thresholds.statistical_red_p_value,
                amber_p_value=thresholds.statistical_amber_p_value,
            )
            cluster_status = assign_cluster_status(
                recent.loc[date_key, "exceptions_last_10d"],
                amber_exception_count=thresholds.cluster_amber_exception_count,
                red_exception_count=thresholds.cluster_red_exception_count,
            )
            challenger_status = assign_challenger_divergence_status(
                max_divergence,
                amber_threshold=thresholds.challenger_amber_relative_difference,
                red_threshold=thresholds.challenger_red_relative_difference,
            )
            challenger_review_required = challenger_status in {AMBER, RED}
            far_tail_performance_watch = assign_far_tail_performance_watch(
                exception_rate_status=exception_rate_status,
                kupiec_status=kupiec_status,
                challenger_divergence_status=challenger_status,
            )
            dependence_watch_status = assign_dependence_watch_status(
                conditional_coverage_status=cc_status,
                cluster_status=cluster_status,
            )
            volatility_regime = str(regimes.reindex(index).loc[date_key])
            high_vol_tail_escalation = bool(
                volatility_regime == "HIGH_VOL"
                and far_tail_performance_watch in {AMBER, RED}
            )
            overall = aggregate_overall_status_v1_1(
                data_quality_status=data_quality_status,
                far_tail_performance_watch=far_tail_performance_watch,
                dependence_watch_status=dependence_watch_status,
                exception_rate_status=exception_rate_status,
                kupiec_status=kupiec_status,
                challenger_review_required=challenger_review_required,
                high_vol_tail_escalation=high_vol_tail_escalation,
            )
            rows.append(
                {
                    "date": date_text,
                    "confidence_level": float(confidence_level),
                    "mr001_var": float(mr001_var.loc[date_key]),
                    "mr001_es": float(mr001_es.loc[date_key]),
                    "realized_loss": float(losses.loc[date_key]),
                    "is_exception": bool(exceptions.loc[date_key]),
                    "rolling_exception_rate_125": _safe_float(rolling_125.loc[date_key]),
                    "rolling_exception_rate_250": _safe_float(rolling_250.loc[date_key]),
                    "kupiec_p_value_250": _safe_float(p_values.loc[date_key, "kupiec_p_value_250"]),
                    "conditional_coverage_p_value_250": _safe_float(
                        p_values.loc[date_key, "conditional_coverage_p_value_250"]
                    ),
                    "exceptions_last_5d": int(recent.loc[date_key, "exceptions_last_5d"]),
                    "exceptions_last_10d": int(recent.loc[date_key, "exceptions_last_10d"]),
                    "days_since_last_exception": _safe_float(
                        recent.loc[date_key, "days_since_last_exception"]
                    ),
                    "mr002_var": float(level_var.loc[date_key, "MR-002"]),
                    "mr003_var": float(level_var.loc[date_key, "MR-003"]),
                    "mr004_var": float(level_var.loc[date_key, "MR-004"]),
                    "mr002_divergence": _safe_float(div_values["MR-002"]),
                    "mr003_divergence": _safe_float(div_values["MR-003"]),
                    "mr004_divergence": _safe_float(div_values["MR-004"]),
                    "max_challenger_divergence": _safe_float(max_divergence),
                    "volatility_60d": _safe_float(volatility.reindex(index).loc[date_key]),
                    "volatility_regime": volatility_regime,
                    "high_vol_tail_escalation": high_vol_tail_escalation,
                    "data_quality_status": data_quality_status,
                    "exception_rate_status": exception_rate_status,
                    "kupiec_status": kupiec_status,
                    "conditional_coverage_status": cc_status,
                    "cluster_status": cluster_status,
                    "challenger_divergence_status": challenger_status,
                    "challenger_review_required": challenger_review_required,
                    "far_tail_performance_watch": far_tail_performance_watch,
                    "dependence_watch_status": dependence_watch_status,
                    "tail_watch_status": far_tail_performance_watch,
                    "overall_status": overall,
                    "open_findings": ";".join(open_findings),
                    "snapshot_is_live": False,
                }
            )
    return pd.DataFrame.from_records(rows).sort_values(["date", "confidence_level"])


def build_monitoring_snapshot(history: pd.DataFrame, *, findings: pd.DataFrame) -> pd.DataFrame:
    """Return the latest frozen-data monitoring rows."""

    final_date = history["date"].max()
    snapshot = history[history["date"].eq(final_date)].copy()
    snapshot = snapshot.rename(columns={"date": "as_of_date"})
    snapshot["snapshot_scope"] = "historical frozen-data snapshot, not live/current market-risk status"
    snapshot["open_findings"] = ";".join(findings.loc[findings["status"].eq("OPEN"), "finding_id"])
    return snapshot.sort_values("confidence_level").reset_index(drop=True)


def build_breach_log(history: pd.DataFrame, *, thresholds: MonitoringThresholds) -> pd.DataFrame:
    """Create one row per AMBER/RED monitoring escalation."""

    metric_map = {
        "exception_rate_status": ("rolling_exception_rate_250", "exception_rate_threshold", "FAR_TAIL_PERFORMANCE"),
        "kupiec_status": ("kupiec_p_value_250", "statistical_p_value_threshold", "FAR_TAIL_PERFORMANCE"),
        "far_tail_performance_watch": (
            "far_tail_performance_watch",
            "far_tail_performance_watch_rule",
            "FAR_TAIL_PERFORMANCE",
        ),
        "conditional_coverage_status": (
            "conditional_coverage_p_value_250",
            "statistical_p_value_threshold",
            "TEMPORAL_DEPENDENCE",
        ),
        "cluster_status": ("exceptions_last_10d", "cluster_exception_count_threshold", "TEMPORAL_DEPENDENCE"),
        "dependence_watch_status": ("dependence_watch_status", "dependence_watch_rule", "TEMPORAL_DEPENDENCE"),
        "overall_status": ("overall_status", "overall_precedence_rule", "OVERALL"),
    }
    rows = []
    for record in history.to_dict(orient="records"):
        if record["data_quality_status"] in {RED, "BLOCK"}:
            rows.append(
                _breach_row(
                    row_number=len(rows) + 1,
                    record=record,
                    metric="data_quality",
                    observed_value=record["data_quality_status"],
                    threshold="Blocking Phase 6 data-quality failure forces RED/BLOCKED.",
                    status=RED,
                    driver_type="DATA_QUALITY",
                    finding_id="DQ",
                    escalation_action="RED: block risk-output use until data-quality issue is remediated.",
                )
            )
        if record["challenger_review_required"]:
            rows.append(
                _breach_row(
                    row_number=len(rows) + 1,
                    record=record,
                    metric="challenger_review",
                    observed_value=record["challenger_divergence_status"],
                    threshold=_threshold_description(
                        metric="challenger_review",
                        confidence_level=float(record["confidence_level"]),
                        status=AMBER,
                        thresholds=thresholds,
                    ),
                    status=AMBER,
                    driver_type="CONTEXTUAL_CHALLENGER",
                    finding_id="MV-001",
                    escalation_action=(
                        "AMBER: review material challenger methodology disagreement; "
                        "not treating it as proof of standalone model-performance failure."
                    ),
                )
            )
        if record["high_vol_tail_escalation"]:
            rows.append(
                _breach_row(
                    row_number=len(rows) + 1,
                    record=record,
                    metric="high_vol_tail_escalation",
                    observed_value=record["volatility_regime"],
                    threshold="HIGH_VOL with far_tail_performance_watch AMBER/RED raises review priority.",
                    status=AMBER,
                    driver_type="VOLATILITY_CONTEXT",
                    finding_id="MV-001",
                    escalation_action="AMBER: prioritize tail-risk review in high-volatility context.",
                )
            )
        for status_column, (metric_column, _threshold_name, driver_type) in metric_map.items():
            status = record[status_column]
            if status not in {AMBER, RED}:
                continue
            metric = status_column.replace("_status", "")
            confidence_level = float(record["confidence_level"])
            observed_value = record.get(metric_column)
            derived_driver = (
                _overall_driver_type(record) if metric == "overall" else driver_type
            )
            rows.append(
                {
                    "breach_id": f"BR-{len(rows) + 1:05d}",
                    "date": record["date"],
                    "confidence_level": confidence_level,
                    "metric": metric,
                    "observed_value": observed_value,
                    "threshold": _threshold_description(
                        metric=metric,
                        confidence_level=confidence_level,
                        status=status,
                        thresholds=thresholds,
                    ),
                    "status": status,
                    "driver_type": derived_driver,
                    "finding_id": _finding_for_metric(metric, confidence_level),
                    "escalation_action": _escalation_action(metric, confidence_level, status),
                    "resolved_in_sample": _resolved_after(history, record["date"], confidence_level, status_column),
                    "notes": (
                        "Historical replay breach; breach resolution is not equivalent to closing "
                        "the linked model finding."
                    ),
                }
            )
    return pd.DataFrame.from_records(rows)


def _breach_row(
    *,
    row_number: int,
    record: dict[str, object],
    metric: str,
    observed_value: object,
    threshold: str,
    status: str,
    driver_type: str,
    finding_id: str,
    escalation_action: str,
) -> dict[str, object]:
    return {
        "breach_id": f"BR-{row_number:05d}",
        "date": record["date"],
        "confidence_level": float(record["confidence_level"]),
        "metric": metric,
        "observed_value": observed_value,
        "threshold": threshold,
        "status": status,
        "driver_type": driver_type,
        "finding_id": finding_id,
        "escalation_action": escalation_action,
        "resolved_in_sample": False,
        "notes": (
            "Historical replay event; event resolution is not equivalent to closing "
            "the linked model finding."
        ),
    }


def build_remediation_log(
    *,
    effective_date: str,
    evidence_paths: list[str],
) -> pd.DataFrame:
    """Create Phase 7 remediation actions without closing findings."""

    opened = date.fromisoformat(effective_date)
    target = opened + timedelta(days=14)
    evidence = ";".join(evidence_paths)
    rows = [
        {
            "remediation_id": "RM-001",
            "finding_id": "MV-001",
            "action": (
                "Implement 99% far-tail monitoring, challenger-divergence monitoring, "
                "high-volatility escalation context, and restrict standalone interpretation "
                "of MR-001 99% risk where monitoring identifies material disagreement."
            ),
            "owner_role": "Model Owner / Developer",
            "status": "IMPLEMENTED_PENDING_VALIDATION",
            "target_date": target.isoformat(),
            "completion_date": "",
            "evidence": evidence,
        },
        {
            "remediation_id": "RM-002",
            "finding_id": "MV-002",
            "action": (
                "Implement rolling exception-rate monitoring, recent cluster monitoring, "
                "conditional-coverage monitoring, and escalation for clustered exceptions."
            ),
            "owner_role": "Independent Validation",
            "status": "IMPLEMENTED_PENDING_VALIDATION",
            "target_date": target.isoformat(),
            "completion_date": "",
            "evidence": evidence,
        },
    ]
    return pd.DataFrame.from_records(rows, columns=REMEDIATION_COLUMNS)


def build_framework_comparison(*, v1_history: pd.DataFrame, v1_1_history: pd.DataFrame) -> pd.DataFrame:
    """Compare v1.0 and v1.1 overall-status alert patterns."""

    rows = []
    for version, history in [("1.0", v1_history), ("1.1", v1_1_history)]:
        for confidence_level, group in history.groupby("confidence_level"):
            ordered = group.sort_values("date")
            counts = ordered["overall_status"].value_counts()
            red_flags = ordered["overall_status"].eq(RED).tolist()
            rows.append(
                {
                    "framework_version": version,
                    "confidence_level": float(confidence_level),
                    "green_count": int(counts.get(GREEN, 0)),
                    "amber_count": int(counts.get(AMBER, 0)),
                    "red_count": int(counts.get(RED, 0)),
                    "insufficient_data_count": int(counts.get(INSUFFICIENT_DATA, 0)),
                    "observation_count": int(len(ordered)),
                    "red_fraction": float(counts.get(RED, 0) / len(ordered)) if len(ordered) else 0.0,
                    "longest_continuous_red_streak": _longest_true_streak(red_flags),
                    "red_episode_count": _episode_count(red_flags),
                }
            )
    return pd.DataFrame.from_records(rows).sort_values(["confidence_level", "framework_version"])


def build_monitoring_summary(
    *,
    thresholds: MonitoringThresholds,
    portfolio_returns_path: Path,
    forecasts_path: Path,
    history: pd.DataFrame,
    snapshot: pd.DataFrame,
    breaches: pd.DataFrame,
    findings: pd.DataFrame,
    remediation: pd.DataFrame,
    volatility_calibration: object,
    framework_comparison: pd.DataFrame,
    v1_thresholds_path: Path,
    v1_summary_path: Path,
) -> dict[str, Any]:
    """Build monitoring summary JSON."""

    status_counts = {
        f"{confidence_level:.2f}": group["overall_status"].value_counts().to_dict()
        for confidence_level, group in history.groupby("confidence_level")
    }
    breach_counts = breaches["metric"].value_counts().to_dict() if not breaches.empty else {}
    return {
        "phase": 7,
        "threshold_version": thresholds.threshold_version,
        "effective_date": thresholds.effective_date,
        "project_disclaimer": thresholds.project_disclaimer,
        "framework_version_review": {
            "previous_version": "1.0",
            "active_version": thresholds.threshold_version,
            "v1_thresholds_hash": sha256_file(v1_thresholds_path),
            "v1_summary_hash": sha256_file(v1_summary_path),
            "numeric_threshold_change": False,
            "rationale": (
                "Alert-saturation review preserved numerical thresholds and changed only "
                "metric roles and aggregation semantics."
            ),
        },
        "input_data_hash": sha256_file(portfolio_returns_path),
        "forecast_artifact_hash": sha256_file(forecasts_path),
        "monitoring_start": history["date"].min(),
        "monitoring_end": history["date"].max(),
        "monitoring_scope": "historical frozen-data replay, not live/current market-risk status",
        "snapshot_is_live": False,
        "volatility_calibration": asdict(volatility_calibration),
        "status_counts_by_confidence": status_counts,
        "breach_counts_by_metric": breach_counts,
        "framework_comparison": _records(framework_comparison),
        "latest_snapshot": _records(snapshot),
        "open_findings": findings[findings["status"].eq("OPEN")]["finding_id"].tolist(),
        "finding_status": findings[["finding_id", "status"]].to_dict(orient="records"),
        "remediation_status": remediation[["remediation_id", "finding_id", "status"]].to_dict(orient="records"),
        "final_validation_decision": None,
        "limitations": [
            "Historical replay on frozen validation data, not live/current monitoring.",
            "Thresholds are project-specific controls, not regulatory numerical requirements.",
            "Rolling 99% statistical monitoring has small expected exception counts over 250 observations.",
            "Conditional-coverage tests may be low power or insufficient when exceptions are sparse.",
            "Phase 6 data-quality controls are a blocking gate, not a substitute for clean market data.",
            "Public ETF proxy portfolio and no real-time feed or institutional escalation process.",
            "Findings remain open until Phase 8 closure/final-decision assessment.",
        ],
    }


def render_monitoring_report(
    *,
    summary: dict[str, Any],
    snapshot: pd.DataFrame,
    breaches: pd.DataFrame,
    remediation: pd.DataFrame,
    thresholds: MonitoringThresholds,
    framework_comparison: pd.DataFrame,
) -> str:
    """Render Phase 7 monitoring report."""

    status_counts = pd.DataFrame(summary["status_counts_by_confidence"]).fillna(0).astype(int).reset_index()
    status_counts = status_counts.rename(columns={"index": "overall_status"})
    top_breaches = _top_breaches_for_report(breaches)
    calibration = summary["volatility_calibration"]
    return f"""# Ongoing Model Monitoring Report

## 1. Purpose

Phase 7 implements a historical replay of an ongoing monitoring framework for
MR-001. Monitoring is a lifecycle control and a compensating control. It does
not erase the underlying Gaussian tail limitation or close validation findings.

## 2. Findings in Scope

- MV-001: MR-001 99% Gaussian far-tail calibration weakness, High, OPEN.
- MV-002: MR-001 95% exception clustering despite acceptable unconditional coverage, Moderate, OPEN.

## 3. Monitoring Framework

The framework monitors exception frequency, rolling Kupiec p-values, rolling
conditional-coverage p-values where data are meaningful, recent clustering,
challenger VaR divergence, causal volatility regime context, and Phase 6
data-quality gating.

## 4. Threshold Framework

Threshold version: {thresholds.threshold_version}, effective date:
{thresholds.effective_date}. All thresholds are project controls, not regulatory
numerical requirements. The 15%/25% challenger-divergence thresholds originate
in Phase 1. The 0.05 statistical significance convention originates in Phase 1.
The 0.10 p-value AMBER band and recent-cluster thresholds are Phase 7
early-warning monitoring choices.

## 4A. Monitoring Framework Version Review

Phase 7 v1.0 was deliberately conservative. Historical replay revealed alert saturation,
including long RED periods driven by challenger divergence. The
primary design issue was not the numerical challenger thresholds. The issue was
aggregation semantics: methodological disagreement was being promoted directly
into hard model failure.

Version 1.1 preserves all numeric thresholds and distinguishes model-performance
evidence, temporal-dependence evidence, methodological disagreement, volatility
context, and data-quality hard failures. Challenger divergence remains measured
with the same 15%/25% thresholds and remains prominent as review context, but a
challenger difference alone is not treated as proof that MR-001 has failed.
Version 1.0 remains preserved for auditability under
`data/artifacts/monitoring_v1_0/` and
`configs/monitoring/thresholds_v1_0.yaml`.

Version 1.1 is not a post-hoc attempt to make MR-001 pass. Actual RED
model-performance evidence remains RED.

{_markdown_table(framework_comparison)}

## 5. Causal Volatility Regime

Trailing volatility window: {calibration["rolling_window"]}. Calibration uses
the first {calibration["calibration_observations"]} valid rolling-volatility
observations, from {calibration["calibration_start"]} to
{calibration["calibration_end"]}. Fixed boundaries are LOW <=
{calibration["lower_threshold"]:.6f} and HIGH >=
{calibration["upper_threshold"]:.6f}. This is not the retrospective Phase 2/5
full-sample regime framework.

## 6. Historical Monitoring Results

{_markdown_table(status_counts)}

## 7. Major Breaches

{_markdown_table(top_breaches)}

Individual breach resolution in the historical replay is not equivalent to closing
the linked model finding, remediation, or finding closure.

## 8. Latest Frozen Snapshot

This is a historical project snapshot as of the final date in the frozen
validation dataset, not a live/current market-risk status.

{_markdown_table(snapshot[["as_of_date", "confidence_level", "overall_status", "exception_rate_status", "kupiec_status", "conditional_coverage_status", "cluster_status", "dependence_watch_status", "challenger_divergence_status", "challenger_review_required", "far_tail_performance_watch", "volatility_regime", "high_vol_tail_escalation", "open_findings"]])}

## 9. MV-001 Remediation Evidence

RM-001 implements 99% tail-watch monitoring, challenger divergence monitoring,
and high-volatility escalation context. The Gaussian far-tail model limitation
itself has not been mathematically eliminated; the control reduces the risk of
unaware reliance on MR-001 99% output.

## 10. MV-002 Remediation Evidence

RM-002 implements rolling exception-rate monitoring, recent exception-cluster
monitoring, conditional-coverage monitoring when meaningful, and escalation for
clustered exceptions.

## 11. Data Quality Gate

Phase 6 data-quality controls are integrated as a hard gate. A blocking
data-quality failure forces overall monitoring RED and prevents risk outputs
from being treated as trusted for that date.

## 12. Remediation Status

{_markdown_table(remediation)}

## 13. Limitations

- Frozen historical dataset, not live monitoring.
- Project-specific thresholds and no institutional escalation process.
- Small 99% rolling samples: 250 observations imply about 2.5 expected exceptions.
- Conditional-coverage power is limited when exceptions are sparse.
- Public ETF proxies and no real-time feed.
- Findings are not closed in Phase 7.

## 14. Phase 7 Conclusion

The monitoring controls and remediation evidence are ready for Phase 8 closure
assessment. No VALIDATED, VALIDATED_WITH_CONDITIONS, RESTRICTED_USE, or
NOT_VALIDATED decision is assigned here.
"""


def _data_quality_status(prices: pd.DataFrame, thresholds: MonitoringThresholds) -> str:
    results = run_control_suite(
        clean_prices=prices,
        candidate_prices=prices,
        stale_threshold=thresholds.stale_price_threshold,
        extreme_return_threshold=thresholds.extreme_return_threshold,
    )
    policy = summarize_policy(results)
    return RED if policy["blocking_control_triggered"] else GREEN


def _tail_watch_status(component_statuses: list[str]) -> str:
    if RED in component_statuses:
        return RED
    if AMBER in component_statuses:
        return AMBER
    if all(status == GREEN for status in component_statuses):
        return GREEN
    return INSUFFICIENT_DATA


def _longest_true_streak(flags: list[bool]) -> int:
    longest = 0
    current = 0
    for flag in flags:
        if flag:
            current += 1
            longest = max(longest, current)
        else:
            current = 0
    return longest


def _episode_count(flags: list[bool]) -> int:
    episodes = 0
    previous = False
    for flag in flags:
        if flag and not previous:
            episodes += 1
        previous = flag
    return episodes


def _threshold_description(
    *,
    metric: str,
    confidence_level: float,
    status: str,
    thresholds: MonitoringThresholds,
) -> str:
    expected = 1.0 - confidence_level
    if metric == "exception_rate":
        return (
            f"AMBER>{expected * thresholds.exception_rate_amber_multiplier:.4f}; "
            f"RED>{expected * thresholds.exception_rate_red_multiplier:.4f}"
        )
    if metric in {"kupiec", "conditional_coverage"}:
        return f"AMBER p<{thresholds.statistical_amber_p_value:.2f}; RED p<{thresholds.statistical_red_p_value:.2f}"
    if metric == "cluster":
        return (
            f"AMBER exceptions_last_10d>={thresholds.cluster_amber_exception_count}; "
            f"RED>={thresholds.cluster_red_exception_count}"
        )
    if metric == "far_tail_performance_watch":
        return (
            "RED if exception-rate or Kupiec status is RED; AMBER for AMBER performance "
            "evidence or challenger disagreement; challenger disagreement alone cannot create RED."
        )
    if metric == "dependence_watch":
        return (
            "RED if cluster is RED or conditional coverage is RED with cluster AMBER/RED; "
            "conditional coverage RED alone is AMBER."
        )
    if metric == "challenger_review":
        return (
            f"Review required when divergence status is AMBER/RED using unchanged "
            f"{thresholds.challenger_amber_relative_difference:.2f}/"
            f"{thresholds.challenger_red_relative_difference:.2f} thresholds; contextual only."
        )
    return (
        "v1.1 precedence: data-quality RED, far-tail-performance RED, temporal-dependence RED, "
        "then AMBER hard/contextual reviews; challenger alone cannot create RED."
    )


def _finding_for_metric(metric: str, confidence_level: float) -> str:
    if metric in {"dependence_watch", "cluster", "conditional_coverage"}:
        return "MV-002"
    if confidence_level == 0.99 or metric in {"far_tail_performance_watch", "challenger_review"}:
        return "MV-001"
    if metric in {"exception_rate", "kupiec"} and confidence_level == 0.95:
        return "MV-002"
    return "MV-001;MV-002"


def _escalation_action(metric: str, confidence_level: float, status: str) -> str:
    if metric == "challenger_review":
        return f"{status}: review challenger methodology disagreement without treating it as proof of failure."
    if metric == "dependence_watch" or metric in {"cluster", "conditional_coverage"}:
        return f"{status}: review MR-001 exception clustering and temporal dependence."
    if confidence_level == 0.99 or metric == "far_tail_performance_watch":
        return f"{status}: review MR-001 99% far-tail performance evidence."
    return f"{status}: review MR-001 coverage evidence."


def _overall_driver_type(record: dict[str, object]) -> str:
    if record["data_quality_status"] in {RED, "BLOCK"}:
        return "DATA_QUALITY"
    if record["far_tail_performance_watch"] == RED:
        return "FAR_TAIL_PERFORMANCE"
    if record["dependence_watch_status"] == RED:
        return "TEMPORAL_DEPENDENCE"
    if record["far_tail_performance_watch"] == AMBER:
        return "FAR_TAIL_PERFORMANCE"
    if record["dependence_watch_status"] == AMBER:
        return "TEMPORAL_DEPENDENCE"
    if record["challenger_review_required"]:
        return "CONTEXTUAL_CHALLENGER"
    if record["high_vol_tail_escalation"]:
        return "VOLATILITY_CONTEXT"
    return "INSUFFICIENT_DATA"


def _resolved_after(history: pd.DataFrame, date_text: str, confidence_level: float, status_column: str) -> bool:
    later = history[
        (history["confidence_level"].eq(confidence_level))
        & (history["date"] > date_text)
        & (history[status_column].eq(GREEN))
    ]
    return bool(not later.empty)


def _top_breaches_for_report(breaches: pd.DataFrame) -> pd.DataFrame:
    if breaches.empty:
        return pd.DataFrame(
            columns=[
                "date",
                "confidence_level",
                "metric",
                "driver_type",
                "observed_value",
                "threshold",
                "status",
                "finding_id",
            ]
        )
    preferred = breaches[breaches["status"].eq(RED)].copy()
    if preferred.empty:
        preferred = breaches.copy()
    return preferred[
        ["date", "confidence_level", "metric", "driver_type", "observed_value", "threshold", "status", "finding_id"]
    ].head(20)


def _markdown_table(table: pd.DataFrame) -> str:
    formatted = table.copy()
    for column in formatted.columns:
        if pd.api.types.is_float_dtype(formatted[column]):
            formatted[column] = formatted[column].map(lambda value: "" if pd.isna(value) else f"{value:.4f}")
    headers = [str(column) for column in formatted.columns]
    rows = []
    for record in formatted.astype(object).where(pd.notna(formatted), "").to_dict(orient="records"):
        rows.append([str(record[column]).replace("|", "\\|").replace("\n", " ") for column in formatted.columns])
    return "\n".join(
        [
            "| " + " | ".join(headers) + " |",
            "| " + " | ".join("---" for _ in headers) + " |",
            *["| " + " | ".join(row) + " |" for row in rows],
        ]
    )


def _records(table: pd.DataFrame) -> list[dict[str, Any]]:
    return [_json_clean(row) for row in table.to_dict(orient="records")]


def _json_dumps(payload: dict[str, Any]) -> str:
    return json.dumps(_json_clean(payload), indent=2, sort_keys=True) + "\n"


def _json_clean(value: Any) -> Any:
    if isinstance(value, dict):
        return {str(key): _json_clean(item) for key, item in value.items()}
    if isinstance(value, list):
        return [_json_clean(item) for item in value]
    if isinstance(value, tuple):
        return [_json_clean(item) for item in value]
    if isinstance(value, (np.integer,)):
        return int(value)
    if isinstance(value, (np.bool_,)):
        return bool(value)
    if isinstance(value, (np.floating, float)):
        return None if np.isnan(value) else float(value)
    if isinstance(value, pd.Timestamp):
        return value.strftime("%Y-%m-%d")
    return value


def _safe_float(value: object) -> float | None:
    if value is None or pd.isna(value):
        return None
    return float(value)


def _max_or_nan(values: list[object]) -> float:
    numeric = [float(value) for value in values if value is not None and not pd.isna(value)]
    return float(max(numeric)) if numeric else np.nan


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run Phase 7 monitoring replay.")
    parser.add_argument("--thresholds", default="configs/monitoring/thresholds.yaml")
    parser.add_argument("--forecasts", default="data/artifacts/challenger_forecasts.csv")
    parser.add_argument("--portfolio-returns", default="data/artifacts/baseline_multi_asset_equal_weight_timeseries.csv")
    parser.add_argument("--prices", default="data/processed/adjusted_close.csv")
    parser.add_argument("--findings", default="governance/findings.csv")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    paths = run_monitoring_pipeline(
        thresholds_path=args.thresholds,
        forecasts_path=args.forecasts,
        portfolio_returns_path=args.portfolio_returns,
        price_path=args.prices,
        findings_path=args.findings,
    )
    print(_json_dumps({key: str(value) for key, value in paths.__dict__.items()}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
