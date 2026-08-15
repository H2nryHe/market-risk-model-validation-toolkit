from __future__ import annotations

import json
from datetime import date
from pathlib import Path

import pandas as pd

from market_risk_toolkit.validation.findings import (
    ALLOWED_SEVERITIES,
    FINDINGS_SCHEMA,
    build_phase6_findings,
    supports_dq001,
    supports_mv001,
    supports_mv002,
    validate_findings_schema,
)

ROOT = Path(__file__).resolve().parents[1]


def _phase6_inputs() -> dict:
    return {
        "conceptual_summary": json.loads((ROOT / "data/artifacts/conceptual_soundness_summary.json").read_text()),
        "implementation_summary": json.loads(
            (ROOT / "data/artifacts/implementation_verification_summary.json").read_text()
        ),
        "model_comparison": pd.read_csv(ROOT / "data/artifacts/model_comparison.csv"),
        "challenger_divergence": pd.read_csv(ROOT / "data/artifacts/challenger_divergence.csv"),
        "cluster_summary": pd.read_csv(ROOT / "data/artifacts/exception_cluster_summary.csv"),
        "regime_backtest": pd.read_csv(ROOT / "data/artifacts/regime_backtest.csv"),
        "es_diagnostics": pd.read_csv(ROOT / "data/artifacts/es_diagnostics.csv"),
        "control_results": pd.read_csv(ROOT / "data/artifacts/data_quality_control_results.csv"),
        "risk_impact": pd.read_csv(ROOT / "data/artifacts/data_quality_risk_impact.csv"),
    }


def test_findings_csv_uses_required_schema_and_unique_ids() -> None:
    findings = pd.read_csv(ROOT / "governance/findings.csv")

    assert list(findings.columns) == FINDINGS_SCHEMA
    assert findings["finding_id"].is_unique
    assert set(findings["finding_id"]) == {"MV-001", "MV-002"}


def test_finding_evidence_paths_exist() -> None:
    findings = pd.read_csv(ROOT / "governance/findings.csv")

    for artifacts in findings["evidence_artifact"]:
        for artifact in str(artifacts).split(";"):
            assert (ROOT / artifact).exists()


def test_finding_severity_status_recommendation_and_closure_constraints() -> None:
    findings = pd.read_csv(ROOT / "governance/findings.csv", keep_default_na=False)

    assert set(findings["severity"]).issubset(ALLOWED_SEVERITIES)
    assert findings["status"].eq("OPEN").all()
    assert findings["closed_date"].eq("").all()
    assert findings["recommendation"].str.len().gt(0).all()
    assert findings["closure_criteria"].str.len().gt(0).all()


def test_mv001_is_created_only_when_required_evidence_is_satisfied() -> None:
    inputs = _phase6_inputs()

    assert supports_mv001(
        conceptual_summary=inputs["conceptual_summary"],
        implementation_summary=inputs["implementation_summary"],
        model_comparison=inputs["model_comparison"],
        challenger_divergence=inputs["challenger_divergence"],
        regime_backtest=inputs["regime_backtest"],
        es_diagnostics=inputs["es_diagnostics"],
    )

    weakened = inputs["model_comparison"].copy()
    weakened.loc[
        weakened["model_id"].eq("MR-001") & weakened["confidence_level"].eq(0.99),
        "kupiec_p_value",
    ] = 0.50
    assert not supports_mv001(
        conceptual_summary=inputs["conceptual_summary"],
        implementation_summary=inputs["implementation_summary"],
        model_comparison=weakened,
        challenger_divergence=inputs["challenger_divergence"],
        regime_backtest=inputs["regime_backtest"],
        es_diagnostics=inputs["es_diagnostics"],
    )


def test_mv002_is_created_only_when_required_evidence_is_satisfied() -> None:
    inputs = _phase6_inputs()

    assert supports_mv002(
        model_comparison=inputs["model_comparison"],
        cluster_summary=inputs["cluster_summary"],
    )

    weakened = inputs["model_comparison"].copy()
    weakened.loc[
        weakened["model_id"].eq("MR-001") & weakened["confidence_level"].eq(0.95),
        "christoffersen_cc_p_value",
    ] = 0.50
    assert not supports_mv002(model_comparison=weakened, cluster_summary=inputs["cluster_summary"])


def test_dq001_is_not_created_when_material_scenarios_are_detected_and_blocked() -> None:
    inputs = _phase6_inputs()

    assert not supports_dq001(
        control_results=inputs["control_results"],
        risk_impact=inputs["risk_impact"],
    )


def test_build_phase6_findings_is_deterministic_for_fixed_opened_date() -> None:
    inputs = _phase6_inputs()
    first = build_phase6_findings(**inputs, opened_date=date(2026, 8, 14))
    second = build_phase6_findings(**inputs, opened_date=date(2026, 8, 14))

    pd.testing.assert_frame_equal(first, second)
    validate_findings_schema(first)


def test_no_final_model_validation_decision_is_assigned() -> None:
    summary = json.loads((ROOT / "data/artifacts/data_quality_summary.json").read_text())
    report = (ROOT / "reports/sections/data_quality_and_findings.md").read_text().lower()

    assert summary["final_validation_decision"] is None
    assert "no final phase 8 validation decision is assigned" in report
