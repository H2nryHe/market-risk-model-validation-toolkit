from __future__ import annotations

from pathlib import Path

import pandas as pd

from market_risk_toolkit.monitoring.pipeline import REMEDIATION_COLUMNS

ROOT = Path(__file__).resolve().parents[1]


def test_remediation_log_schema_ids_and_statuses() -> None:
    remediation = pd.read_csv(ROOT / "governance/remediation_log.csv", keep_default_na=False)

    assert list(remediation.columns) == REMEDIATION_COLUMNS
    assert set(remediation["remediation_id"]) == {"RM-001", "RM-002"}
    assert set(remediation["finding_id"]) == {"MV-001", "MV-002"}
    assert remediation["status"].eq("COMPLETED").all()
    assert remediation["completion_date"].eq("2026-08-14").all()


def test_remediation_actions_link_mv001_tail_watch_and_mv002_clustering_controls() -> None:
    remediation = pd.read_csv(ROOT / "governance/remediation_log.csv", keep_default_na=False)
    actions = remediation.set_index("finding_id")["action"].str.lower()

    assert "99% far-tail monitoring" in actions["MV-001"]
    assert "challenger-divergence" in actions["MV-001"]
    assert "rolling exception-rate monitoring" in actions["MV-002"]
    assert "conditional-coverage monitoring" in actions["MV-002"]


def test_remediation_target_dates_are_phase7_effective_date_plus_fourteen_days() -> None:
    remediation = pd.read_csv(ROOT / "governance/remediation_log.csv", keep_default_na=False)

    assert remediation["target_date"].eq("2026-08-28").all()


def test_remediation_evidence_paths_exist() -> None:
    remediation = pd.read_csv(ROOT / "governance/remediation_log.csv", keep_default_na=False)

    for evidence in remediation["evidence"]:
        for artifact in evidence.split(";"):
            assert (ROOT / artifact).exists()


def test_phase7_does_not_close_model_validation_findings() -> None:
    findings = pd.read_csv(ROOT / "governance/findings.csv", keep_default_na=False)

    assert findings["status"].eq("OPEN").all()
    assert findings["closed_date"].eq("").all()
    assert set(findings["finding_id"]) == {"MV-001", "MV-002"}
