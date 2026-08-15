from __future__ import annotations

import json
import re
import subprocess
from datetime import date
from pathlib import Path

import pandas as pd
import yaml

ROOT = Path(__file__).resolve().parents[1]
ALLOWED_DECISIONS = {"VALIDATED", "VALIDATED_WITH_CONDITIONS", "RESTRICTED_USE", "NOT_VALIDATED"}


def _json(path: str) -> dict:
    return json.loads((ROOT / path).read_text())


def test_final_validation_decision_json_exists_and_uses_allowed_label() -> None:
    decision = _json("data/artifacts/final_validation_decision.json")

    assert decision["decision"] in ALLOWED_DECISIONS
    assert decision["decision"] == "RESTRICTED_USE"
    date.fromisoformat(decision["decision_date"])
    assert decision["open_findings"] == ["MV-001", "MV-002"]
    assert decision["closed_findings"] == []


def test_final_report_readme_and_executive_summary_match_decision_json() -> None:
    decision = _json("data/artifacts/final_validation_decision.json")["decision"]
    report = (ROOT / "reports/v2_validation_report.md").read_text()
    readme = (ROOT / "README.md").read_text()
    executive = (ROOT / "reports/executive_summary.md").read_text()

    assert f"Decision: **{decision}**" in report
    assert f"Decision: **{decision}**" in readme
    assert f"Final validation decision: **{decision}**" in executive
    assert "VALIDATED:" in report
    assert "VALIDATED_WITH_CONDITIONS:" in report
    assert "RESTRICTED_USE:" in report
    assert "NOT_VALIDATED:" in report


def test_model_inventory_matches_final_decision_without_validating_challengers() -> None:
    decision = _json("data/artifacts/final_validation_decision.json")["decision"]
    inventory = pd.read_csv(ROOT / "governance/model_inventory.csv", keep_default_na=False).set_index("model_id")

    assert inventory.loc["MR-001", "validation_status"] == decision
    assert "standalone 99% far-tail interpretation prohibited" in inventory.loc["MR-001", "notes"]
    assert inventory.loc["MR-002", "validation_status"] == "not yet V2-validated"
    assert inventory.loc["MR-003", "validation_status"] == "pending V2 validation"
    assert inventory.loc["MR-004", "validation_status"] == "pending V2 validation"


def test_findings_remain_open_and_match_final_report() -> None:
    findings = pd.read_csv(ROOT / "governance/findings.csv", keep_default_na=False)
    report = (ROOT / "reports/v2_validation_report.md").read_text()

    assert findings["status"].eq("OPEN").all()
    assert findings["closed_date"].eq("").all()
    for finding_id in findings["finding_id"]:
        assert finding_id in report
        assert f"{finding_id}" in report


def test_finding_closure_assessment_distinguishes_root_cause_from_controls() -> None:
    closure = pd.read_csv(ROOT / "data/artifacts/finding_closure_assessment.csv")

    assert set(closure["finding_id"]) == {"MV-001", "MV-002"}
    assert closure["root_cause_resolved"].eq(False).all()
    assert closure["compensating_control_implemented"].eq(True).all()
    assert closure["closure_criteria_satisfied"].eq(False).all()
    assert closure["recommended_finding_status"].eq("OPEN").all()


def test_remediation_statuses_are_completed_and_match_report_and_decision() -> None:
    remediation = pd.read_csv(ROOT / "governance/remediation_log.csv", keep_default_na=False)
    decision = _json("data/artifacts/final_validation_decision.json")
    report = (ROOT / "reports/v2_validation_report.md").read_text()

    assert remediation["status"].eq("COMPLETED").all()
    assert remediation["completion_date"].eq(decision["decision_date"]).all()
    assert {row["status"] for row in decision["remediation_status"]} == {"COMPLETED"}
    assert "COMPLETED" in report


def test_release_metrics_match_source_artifacts() -> None:
    metrics = _json("data/artifacts/release_metrics.json")
    implementation = _json("data/artifacts/implementation_verification_summary.json")
    comparison = pd.read_csv(ROOT / "data/artifacts/model_comparison.csv")
    data_quality = _json("data/artifacts/data_quality_summary.json")
    scenario_results = pd.DataFrame(data_quality["scenario_results"])

    mr001_99 = comparison[
        comparison["model_id"].eq("MR-001") & comparison["confidence_level"].eq(0.99)
    ].iloc[0]
    assert metrics["implementation_verification"]["comparisons"] == implementation["comparison_count"] == 464
    assert metrics["implementation_verification"]["match_fraction"] == implementation["match_fraction"] == 1.0
    assert metrics["mr001_99"]["exception_count"] == int(mr001_99["exception_count"]) == 41
    assert metrics["mr001_99"]["observation_count"] == int(mr001_99["observation_count"]) == 1804
    assert metrics["data_quality"]["detected"] == int(scenario_results["detected"].sum()) == 5
    assert metrics["data_quality"]["blocked"] == int(scenario_results["blocked"].sum()) == 5
    assert metrics["data_quality"]["false_negatives"] == int(scenario_results["false_negative"].sum()) == 0


def test_no_data_quality_finding_is_invented() -> None:
    findings = pd.read_csv(ROOT / "governance/findings.csv", keep_default_na=False)

    assert set(findings["finding_id"]) == {"MV-001", "MV-002"}
    assert not findings["finding_id"].str.startswith("DQ").any()


def test_monitoring_latest_date_is_frozen_not_current() -> None:
    metrics = _json("data/artifacts/release_metrics.json")
    snapshot = pd.read_csv(ROOT / "data/artifacts/monitoring_snapshot.csv")
    readme = (ROOT / "README.md").read_text().lower()

    assert metrics["monitoring_latest"]["as_of_date"] == snapshot["as_of_date"].max()
    assert "historical frozen-data evidence" in readme
    assert "not live/current status" in readme


def test_private_local_files_are_ignored_and_untracked() -> None:
    ignored = subprocess.run(
        ["git", "check-ignore", "PROJECT_V2_SPEC.md", "PROJECT_SPEC.md", "V2_STATUS.md", "local_v2_baseline"],
        cwd=ROOT,
        check=True,
        capture_output=True,
        text=True,
    )
    tracked = subprocess.run(
        ["git", "ls-files", "PROJECT_V2_SPEC.md", "PROJECT_SPEC.md", "V2_STATUS.md", "local_v2_baseline"],
        cwd=ROOT,
        check=True,
        capture_output=True,
        text=True,
    )

    assert "PROJECT_V2_SPEC.md" in ignored.stdout
    assert "V2_STATUS.md" in ignored.stdout
    assert tracked.stdout == ""


def test_no_unsupported_regulatory_or_live_institutional_claims_in_release_docs() -> None:
    risky = re.compile(
        r"regulatory compliant|fed compliant|occ compliant|production bank|"
        r"regulatory capital model|approved by",
        re.IGNORECASE,
    )
    text = "\n".join(
        (ROOT / path).read_text()
        for path in [
            "README.md",
            "reports/v2_validation_report.md",
            "reports/executive_summary.md",
            "reports/monitoring_report.md",
        ]
    )

    assert not risky.search(text)


def test_report_and_readme_link_to_existing_artifacts() -> None:
    for path in [
        "reports/executive_summary.md",
        "reports/v2_validation_report.md",
        "reports/monitoring_report.md",
        "governance/model_inventory.csv",
        "governance/findings.csv",
        "governance/remediation_log.csv",
        "data/artifacts/final_validation_decision.json",
        "data/artifacts/release_metrics.json",
    ]:
        assert (ROOT / path).exists()


def test_ci_remains_deterministic_and_does_not_require_market_data_refresh() -> None:
    ci = (ROOT / ".github/workflows/ci.yml").read_text().lower()

    assert "pytest -q" in ci
    assert "yfinance" not in ci
    assert "market_risk_toolkit.data" not in ci


def test_validation_plan_allowed_decisions_include_final_decision() -> None:
    plan = yaml.safe_load((ROOT / "configs/validation/validation_plan.yaml").read_text())
    decision = _json("data/artifacts/final_validation_decision.json")["decision"]

    assert set(plan["decision_framework"]["allowed_final_decisions"]) == ALLOWED_DECISIONS
    assert decision in plan["decision_framework"]["allowed_final_decisions"]
