from __future__ import annotations

import csv
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]
INVENTORY_PATH = ROOT / "governance" / "model_inventory.csv"
RATING_PATH = ROOT / "governance" / "model_risk_rating.yaml"
PLAN_PATH = ROOT / "configs" / "validation" / "validation_plan.yaml"

REQUIRED_INVENTORY_COLUMNS = [
    "model_id",
    "model_name",
    "model_version",
    "model_type",
    "purpose",
    "intended_use",
    "owner_role",
    "validator_role",
    "status",
    "materiality",
    "methodology",
    "portfolio_scope",
    "risk_horizon",
    "confidence_levels",
    "data_source",
    "key_assumptions",
    "key_limitations",
    "validation_status",
    "last_validation_date",
    "next_review_date",
    "notes",
]

REQUIRED_SCOPE_AREAS = {
    "data_assessment",
    "conceptual_soundness",
    "implementation_verification",
    "benchmark_comparison",
    "outcomes_analysis",
    "sensitivity_stability",
    "stress_testing",
    "data_quality_impact",
    "ongoing_monitoring_design",
}

EXPECTED_DECISIONS = {
    "VALIDATED",
    "VALIDATED_WITH_CONDITIONS",
    "RESTRICTED_USE",
    "NOT_VALIDATED",
}

EXPECTED_SEVERITIES = {"Low", "Moderate", "High", "Critical"}


def load_inventory() -> dict[str, dict[str, str]]:
    assert INVENTORY_PATH.exists()
    with INVENTORY_PATH.open(newline="") as file:
        rows = list(csv.DictReader(file))
    assert rows
    return {row["model_id"]: row for row in rows}


def load_yaml(path: Path) -> dict:
    assert path.exists()
    with path.open() as file:
        return yaml.safe_load(file)


def test_model_inventory_schema_and_unique_ids() -> None:
    with INVENTORY_PATH.open(newline="") as file:
        reader = csv.DictReader(file)
        assert reader.fieldnames == REQUIRED_INVENTORY_COLUMNS
        rows = list(reader)

    model_ids = [row["model_id"] for row in rows]
    assert len(model_ids) == len(set(model_ids))
    assert {"MR-001", "MR-002", "MR-003", "MR-004"}.issubset(model_ids)


def test_mr001_is_primary_implemented_with_restricted_final_validation_status() -> None:
    row = load_inventory()["MR-001"]
    status = row["status"].lower()
    notes = row["notes"].lower()

    assert row["model_type"] == "primary_model_under_validation"
    assert "implemented" in status
    assert "active" in status
    assert "under v2 validation" in status
    assert row["materiality"] == "High"
    assert row["validation_status"] == "RESTRICTED_USE"
    assert row["last_validation_date"]
    assert row["next_review_date"]
    assert "standalone 99% far-tail interpretation prohibited" in notes
    assert "mv-001/mv-002 remain open" in notes


def test_mr002_is_implemented_benchmark_challenger_not_validated() -> None:
    row = load_inventory()["MR-002"]
    status = row["status"].lower()
    combined = " ".join([row["model_type"], row["intended_use"], row["notes"]]).lower()

    assert "implemented" in status
    assert "benchmark" in combined
    assert "challenger" in combined
    assert row["validation_status"].lower() == "not yet v2-validated"
    assert "approved" not in row["validation_status"].lower()


def test_mr003_and_mr004_are_implemented_challengers_pending_validation() -> None:
    inventory = load_inventory()
    for model_id in ("MR-003", "MR-004"):
        row = inventory[model_id]
        status = row["status"].lower()
        validation_status = row["validation_status"].lower()

        assert row["model_type"] == "implemented_challenger"
        assert "implemented challenger" in status
        assert "pending validation" in status
        assert validation_status == "pending v2 validation"
        assert "validated" not in validation_status
        assert validation_status != "approved"


def test_model_risk_rating_is_project_specific_high_materiality() -> None:
    rating = load_yaml(RATING_PATH)
    text = str(rating).lower()

    assert rating["model_id"] == "MR-001"
    assert rating["overall_materiality"]["rating"] == "High"
    assert "educational" in rating["framework_type"]
    assert "project" in rating["framework_type"]
    assert "not federal reserve prescribed" in text
    assert "not occ prescribed" in text
    assert "not fdic prescribed" in text
    assert "not a real bank policy" in text
    assert "not a real institutional approval authority" in text


def test_validation_plan_scope_and_thresholds_are_parseable() -> None:
    plan = load_yaml(PLAN_PATH)
    thresholds = plan["thresholds"]

    assert plan["model_id"] == "MR-001"
    assert plan["validation_type"] == "initial_v2_validation"
    assert plan["final_validation_decision"] is None
    assert REQUIRED_SCOPE_AREAS == set(plan["scope"])
    assert float(thresholds["statistical_significance_level"]) == 0.05
    assert thresholds["implementation_verification"]["numeric_abs_tolerance"] > 0
    required_match_fraction = thresholds["implementation_verification"]["required_match_fraction"]
    assert 0 <= required_match_fraction <= 1
    assert (
        thresholds["challenger_divergence"]["amber_relative_difference"]
        < thresholds["challenger_divergence"]["red_relative_difference"]
    )
    assert "project" in thresholds["threshold_type"]
    assert "not numerical requirements" in thresholds["regulatory_disclaimer"].lower()


def test_decision_and_severity_labels_are_exact() -> None:
    plan = load_yaml(PLAN_PATH)

    assert set(plan["decision_framework"]["allowed_final_decisions"]) == EXPECTED_DECISIONS
    assert set(plan["severity_framework"]) == EXPECTED_SEVERITIES
    assert plan["decision_framework"]["no_decision_assigned_in_phase_1"] is True


def test_no_phase_one_substantive_findings_created() -> None:
    findings_path = ROOT / "governance" / "findings.csv"
    if not findings_path.exists():
        return

    with findings_path.open(newline="") as file:
        rows = list(csv.DictReader(file))

    assert rows
    assert {row["status"] for row in rows} == {"OPEN"}
    assert all(row["finding_id"].startswith(("MV-", "DQ-")) for row in rows)
