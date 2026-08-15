"""Formal Phase 6 validation findings."""

from __future__ import annotations

from datetime import date, timedelta
from pathlib import Path

import pandas as pd

FINDINGS_SCHEMA = [
    "finding_id",
    "model_id",
    "category",
    "title",
    "description",
    "evidence_artifact",
    "severity",
    "status",
    "recommendation",
    "owner_role",
    "target_date",
    "closure_criteria",
    "opened_date",
    "closed_date",
]
ALLOWED_SEVERITIES = {"Low", "Moderate", "High", "Critical"}


def build_phase6_findings(
    *,
    conceptual_summary: dict,
    implementation_summary: dict,
    model_comparison: pd.DataFrame,
    challenger_divergence: pd.DataFrame,
    cluster_summary: pd.DataFrame,
    regime_backtest: pd.DataFrame,
    es_diagnostics: pd.DataFrame,
    control_results: pd.DataFrame,
    risk_impact: pd.DataFrame,
    opened_date: date | None = None,
) -> pd.DataFrame:
    """Build evidence-supported Phase 6 formal findings."""

    opened = opened_date or date.today()
    target = opened + timedelta(days=120)
    rows: list[dict[str, str]] = []

    if supports_mv001(
        conceptual_summary=conceptual_summary,
        implementation_summary=implementation_summary,
        model_comparison=model_comparison,
        challenger_divergence=challenger_divergence,
        regime_backtest=regime_backtest,
        es_diagnostics=es_diagnostics,
    ):
        rows.append(
            {
                "finding_id": "MV-001",
                "model_id": "MR-001",
                "category": "Model Performance / Tail Calibration",
                "title": "Gaussian 99% VaR understates far-tail loss frequency and severity",
                "description": (
                    "Phase 2 conceptual diagnostics show heavy tails relative to a fitted "
                    "Gaussian distribution; Phase 3 rules out an implementation mismatch; "
                    "Phase 4 and Phase 5 show MR-001 99% exception frequency, regime "
                    "concentration, challenger divergence, and ES shortfall evidence that "
                    "are material for the project intended use."
                ),
                "evidence_artifact": (
                    "data/artifacts/conceptual_soundness_summary.json;"
                    "data/artifacts/implementation_verification_summary.json;"
                    "data/artifacts/model_comparison.csv;"
                    "data/artifacts/challenger_divergence.csv;"
                    "data/artifacts/regime_backtest.csv;"
                    "data/artifacts/es_diagnostics.csv"
                ),
                "severity": "High",
                "status": "OPEN",
                "recommendation": (
                    "Do not rely on standalone MR-001 99% Gaussian VaR as the sole far-tail "
                    "risk measure; require challenger comparison, high-volatility escalation, "
                    "and methodology enhancement evaluation before broader intended use."
                ),
                "owner_role": "Model Owner / Developer",
                "target_date": target.isoformat(),
                "closure_criteria": (
                    "Implement approved project monitoring controls for MR-001 99% tail "
                    "weakness; document challenger divergence thresholds; show frozen-sample "
                    "monitoring/report generation; and explicitly restrict standalone "
                    "interpretation of MR-001 99% where applicable."
                ),
                "opened_date": opened.isoformat(),
                "closed_date": "",
            }
        )

    if supports_mv002(model_comparison=model_comparison, cluster_summary=cluster_summary):
        rows.append(
            {
                "finding_id": "MV-002",
                "model_id": "MR-001",
                "category": "Outcomes Analysis / Temporal Dependence",
                "title": "VaR exceptions cluster despite acceptable 95% unconditional coverage",
                "description": (
                    "MR-001 95% unconditional coverage is close to nominal, but Phase 4 "
                    "independence and conditional-coverage tests reject at the 5% project "
                    "level and Phase 5 cluster diagnostics show extended exception grouping."
                ),
                "evidence_artifact": (
                    "data/artifacts/model_comparison.csv;"
                    "data/artifacts/exception_cluster_summary.csv;"
                    "data/artifacts/regime_backtest.csv"
                ),
                "severity": "Moderate",
                "status": "OPEN",
                "recommendation": (
                    "Add rolling exception-rate and clustering monitoring, define escalation "
                    "for clustered exceptions, and review challenger behavior during clustered "
                    "or high-volatility periods."
                ),
                "owner_role": "Independent Validation",
                "target_date": target.isoformat(),
                "closure_criteria": (
                    "Implement rolling exception and clustering monitoring; document "
                    "escalation triggers; and include clustered-exception evidence in the "
                    "ongoing monitoring report."
                ),
                "opened_date": opened.isoformat(),
                "closed_date": "",
            }
        )

    if supports_dq001(control_results=control_results, risk_impact=risk_impact):
        rows.append(
            {
                "finding_id": "DQ-001",
                "model_id": "Market Data Process",
                "category": "Data Quality / Market Data Controls",
                "title": "Market-data control gap permits material VaR distortion",
                "description": (
                    "At least one deterministic injected market-data defect caused material "
                    "VaR distortion and was not detected or blocked by the Phase 6 controls."
                ),
                "evidence_artifact": (
                    "data/artifacts/data_quality_control_results.csv;"
                    "data/artifacts/data_quality_risk_impact.csv"
                ),
                "severity": "High",
                "status": "OPEN",
                "recommendation": "Implement blocking controls before downstream risk calculation.",
                "owner_role": "Model Risk Governance",
                "target_date": target.isoformat(),
                "closure_criteria": (
                    "Demonstrate that deterministic material data-quality defects are detected "
                    "and blocked before risk calculation on the frozen validation sample."
                ),
                "opened_date": opened.isoformat(),
                "closed_date": "",
            }
        )

    return pd.DataFrame.from_records(rows, columns=FINDINGS_SCHEMA)


def supports_mv001(
    *,
    conceptual_summary: dict,
    implementation_summary: dict,
    model_comparison: pd.DataFrame,
    challenger_divergence: pd.DataFrame,
    regime_backtest: pd.DataFrame,
    es_diagnostics: pd.DataFrame,
) -> bool:
    """Evaluate whether MV-001 has sufficient evidence."""

    tail = conceptual_summary["tail_comparison"]
    mr1_99 = _comparison_row(model_comparison, "MR-001", 0.99)
    mr1_high = regime_backtest[
        regime_backtest["model_id"].eq("MR-001")
        & regime_backtest["confidence_level"].eq(0.99)
        & regime_backtest["volatility_regime"].eq("HIGH_VOL")
    ].iloc[0]
    mr1_es = es_diagnostics[
        es_diagnostics["model_id"].eq("MR-001") & es_diagnostics["confidence_level"].eq(0.99)
    ].iloc[0]
    divergence_99 = challenger_divergence[challenger_divergence["confidence_level"].eq(0.99)]
    return bool(
        tail["empirical_99_loss_quantile"] > tail["gaussian_99_loss_quantile"]
        and tail["frequency_beyond_gaussian_99_loss_threshold"] > 0.01
        and implementation_summary["match_fraction"] == 1.0
        and mr1_99["exception_rate"] > 0.015
        and mr1_99["kupiec_p_value"] < 0.05
        and (divergence_99["mean_absolute_relative_divergence"] > 0.15).any()
        and mr1_high["exception_rate"] > 0.01
        and mr1_high["high_vol_exception_concentration_ratio"] > 1.0
        and mr1_es["realized_loss_to_es_ratio"] > 1.0
    )


def supports_mv002(*, model_comparison: pd.DataFrame, cluster_summary: pd.DataFrame) -> bool:
    """Evaluate whether MV-002 has sufficient evidence."""

    mr1_95 = _comparison_row(model_comparison, "MR-001", 0.95)
    cluster = cluster_summary[
        cluster_summary["model_id"].eq("MR-001") & cluster_summary["confidence_level"].eq(0.95)
    ].iloc[0]
    return bool(
        abs(mr1_95["exception_rate"] - mr1_95["expected_exception_rate"]) < 0.01
        and mr1_95["kupiec_p_value"] >= 0.05
        and mr1_95["christoffersen_independence_p_value"] < 0.05
        and mr1_95["christoffersen_cc_p_value"] < 0.05
        and cluster["max_cluster_length"] >= 5
    )


def supports_dq001(*, control_results: pd.DataFrame, risk_impact: pd.DataFrame) -> bool:
    """Open a DQ finding only for a material false negative."""

    scenario_controls = control_results.groupby("scenario_id").agg(
        expected_control_detected=("expected_control_detected", "max"),
        blocking_control_triggered=("blocking_control_triggered", "max"),
    )
    material = risk_impact.groupby("scenario_id")["material_var_impact"].max()
    for scenario_id, material_impact in material.items():
        if bool(material_impact):
            controls = scenario_controls.loc[scenario_id]
            if not bool(controls["expected_control_detected"]) or not bool(
                controls["blocking_control_triggered"]
            ):
                return True
    return False


def validate_findings_schema(findings: pd.DataFrame) -> None:
    """Validate findings schema and basic governance constraints."""

    if list(findings.columns) != FINDINGS_SCHEMA:
        raise ValueError("Findings schema does not match canonical Phase 6 schema.")
    if findings["finding_id"].duplicated().any():
        raise ValueError("Finding IDs must be unique.")
    invalid = set(findings["severity"]).difference(ALLOWED_SEVERITIES)
    if invalid:
        raise ValueError(f"Invalid finding severity values: {sorted(invalid)}")
    if not findings["status"].eq("OPEN").all():
        raise ValueError("Phase 6 findings must remain OPEN.")
    if not findings["closed_date"].fillna("").eq("").all():
        raise ValueError("OPEN findings must have empty closed_date.")
    for column in ("recommendation", "closure_criteria", "evidence_artifact"):
        if findings[column].fillna("").str.strip().eq("").any():
            raise ValueError(f"Findings must have non-empty {column}.")
    for artifacts in findings["evidence_artifact"]:
        for artifact in str(artifacts).split(";"):
            if artifact and not Path(artifact).exists():
                raise ValueError(f"Finding evidence artifact does not exist: {artifact}")


def _comparison_row(table: pd.DataFrame, model_id: str, confidence_level: float) -> pd.Series:
    rows = table[table["model_id"].eq(model_id) & table["confidence_level"].eq(confidence_level)]
    if rows.empty:
        raise ValueError(f"Missing comparison row for {model_id} {confidence_level}.")
    return rows.iloc[0]
