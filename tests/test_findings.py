from __future__ import annotations

import json
import subprocess
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
)

ROOT = Path(__file__).resolve().parents[1]


def _phase6_inputs() -> dict:
    challenger_summary = json.loads((ROOT / "data/artifacts/challenger_model_summary.json").read_text())
    release_metrics = json.loads((ROOT / "data/artifacts/release_metrics.json").read_text())
    data_quality = json.loads((ROOT / "data/artifacts/data_quality_summary.json").read_text())
    return {
        "conceptual_summary": json.loads((ROOT / "data/artifacts/conceptual_soundness_summary.json").read_text()),
        "implementation_summary": json.loads(
            (ROOT / "data/artifacts/implementation_verification_summary.json").read_text()
        ),
        "model_comparison": pd.read_csv(ROOT / "data/artifacts/model_comparison.csv"),
        "challenger_divergence": pd.DataFrame(challenger_summary["divergence_records"]),
        "cluster_summary": pd.DataFrame(
            [
                {
                    "model_id": "MR-001",
                    "confidence_level": 0.95,
                    "max_cluster_length": release_metrics["mr001_95"]["max_cluster_length"],
                }
            ]
        ),
        "regime_backtest": pd.DataFrame(
            [
                {
                    "model_id": "MR-001",
                    "confidence_level": 0.99,
                    "volatility_regime": "HIGH_VOL",
                    "exception_rate": release_metrics["mr001_99"]["high_vol_exception_rate"],
                    "high_vol_exception_concentration_ratio": release_metrics["mr001_99"][
                        "high_vol_concentration_ratio"
                    ],
                }
            ]
        ),
        "es_diagnostics": pd.DataFrame(
            [
                {
                    "model_id": "MR-001",
                    "confidence_level": 0.99,
                    "realized_loss_to_es_ratio": release_metrics["mr001_99"]["realized_loss_to_es_ratio"],
                }
            ]
        ),
        "control_results": pd.DataFrame(
            {
                "scenario_id": [row["scenario_id"] for row in data_quality["scenario_results"]],
                "expected_control_detected": [row["detected"] for row in data_quality["scenario_results"]],
                "blocking_control_triggered": [row["blocked"] for row in data_quality["scenario_results"]],
            }
        ),
        "risk_impact": pd.DataFrame(
            {
                "scenario_id": list(data_quality["material_impact_summary"]),
                "material_var_impact": list(data_quality["material_impact_summary"].values()),
            }
        ),
    }


def _is_ignored(path: str) -> bool:
    result = subprocess.run(["git", "check-ignore", path], cwd=ROOT, capture_output=True, text=True)
    return result.returncode == 0


def test_findings_csv_uses_required_schema_and_unique_ids() -> None:
    findings = pd.read_csv(ROOT / "governance/findings.csv")

    assert list(findings.columns) == FINDINGS_SCHEMA
    assert findings["finding_id"].is_unique
    assert set(findings["finding_id"]) == {"MV-001", "MV-002"}


def test_finding_evidence_paths_exist() -> None:
    findings = pd.read_csv(ROOT / "governance/findings.csv")

    for artifacts in findings["evidence_artifact"]:
        for artifact in str(artifacts).split(";"):
            assert (ROOT / artifact).exists() or _is_ignored(artifact)


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
    assert list(first.columns) == FINDINGS_SCHEMA
    assert set(first["finding_id"]) == {"MV-001", "MV-002"}


def test_no_final_model_validation_decision_is_assigned() -> None:
    summary = json.loads((ROOT / "data/artifacts/data_quality_summary.json").read_text())
    report = (ROOT / "reports/sections/data_quality_and_findings.md").read_text().lower()

    assert summary["final_validation_decision"] is None
    assert "no final phase 8 validation decision is assigned" in report
