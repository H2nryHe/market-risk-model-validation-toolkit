"""Phase 8 final validation decision and release artifact builder."""

from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import date
from pathlib import Path
from typing import Any

import pandas as pd

ALLOWED_DECISIONS = {
    "VALIDATED",
    "VALIDATED_WITH_CONDITIONS",
    "RESTRICTED_USE",
    "NOT_VALIDATED",
}

DECISION = "RESTRICTED_USE"
DECISION_DATE = date(2026, 8, 14).isoformat()


@dataclass(frozen=True)
class FinalArtifactPaths:
    finding_closure_assessment_csv: Path
    final_validation_decision_json: Path
    release_metrics_json: Path
    validation_report_md: Path
    executive_summary_md: Path
    readme_md: Path


def build_phase8_artifacts(root: str | Path = ".") -> FinalArtifactPaths:
    """Build deterministic Phase 8 artifacts from generated validation evidence."""

    base = Path(root)
    evidence = _load_evidence(base)
    closure = _build_finding_closure_assessment(evidence)
    decision = _build_final_decision(evidence, closure)
    metrics = _build_release_metrics(evidence, decision)

    paths = FinalArtifactPaths(
        finding_closure_assessment_csv=base / "data/artifacts/finding_closure_assessment.csv",
        final_validation_decision_json=base / "data/artifacts/final_validation_decision.json",
        release_metrics_json=base / "data/artifacts/release_metrics.json",
        validation_report_md=base / "reports/v2_validation_report.md",
        executive_summary_md=base / "reports/executive_summary.md",
        readme_md=base / "README.md",
    )
    paths.finding_closure_assessment_csv.parent.mkdir(parents=True, exist_ok=True)
    paths.validation_report_md.parent.mkdir(parents=True, exist_ok=True)
    _update_model_inventory(base / "governance/model_inventory.csv", decision)
    _update_remediation_log(base / "governance/remediation_log.csv")

    closure.to_csv(paths.finding_closure_assessment_csv, index=False)
    paths.final_validation_decision_json.write_text(_json_dumps(decision), encoding="utf-8")
    paths.release_metrics_json.write_text(_json_dumps(metrics), encoding="utf-8")
    paths.validation_report_md.write_text(_render_validation_report(evidence, closure, decision, metrics), encoding="utf-8")
    paths.executive_summary_md.write_text(_render_executive_summary(evidence, decision, metrics), encoding="utf-8")
    paths.readme_md.write_text(_render_readme(evidence, decision, metrics), encoding="utf-8")
    return paths


def _load_evidence(base: Path) -> dict[str, Any]:
    artifacts = base / "data/artifacts"
    governance = base / "governance"
    reports = base / "reports"
    return {
        "conceptual": _read_json(artifacts / "conceptual_soundness_summary.json"),
        "implementation": _read_json(artifacts / "implementation_verification_summary.json"),
        "challenger_summary": _read_json(artifacts / "challenger_model_summary.json"),
        "sensitivity": _read_json(artifacts / "sensitivity_summary.json"),
        "data_quality": _read_json(artifacts / "data_quality_summary.json"),
        "monitoring": _read_json(artifacts / "monitoring_summary.json"),
        "model_comparison": pd.read_csv(artifacts / "model_comparison.csv"),
        "cluster": pd.read_csv(artifacts / "exception_cluster_summary.csv"),
        "regime": pd.read_csv(artifacts / "regime_backtest.csv"),
        "es": pd.read_csv(artifacts / "es_diagnostics.csv"),
        "dq_impact": pd.read_csv(artifacts / "data_quality_risk_impact.csv"),
        "dq_controls": pd.read_csv(artifacts / "data_quality_control_results.csv"),
        "monitoring_snapshot": pd.read_csv(artifacts / "monitoring_snapshot.csv"),
        "monitoring_comparison": pd.read_csv(artifacts / "monitoring_framework_comparison.csv"),
        "stress_summary": pd.read_csv(artifacts / "baseline_multi_asset_equal_weight_stress_summary.csv"),
        "findings": pd.read_csv(governance / "findings.csv", keep_default_na=False),
        "remediation": pd.read_csv(governance / "remediation_log.csv", keep_default_na=False),
        "inventory": pd.read_csv(governance / "model_inventory.csv", keep_default_na=False),
        "monitoring_report_path": reports / "monitoring_report.md",
    }


def _build_finding_closure_assessment(evidence: dict[str, Any]) -> pd.DataFrame:
    findings = evidence["findings"]
    remediation = evidence["remediation"].set_index("finding_id")
    rows = []
    for finding in findings.to_dict(orient="records"):
        finding_id = finding["finding_id"]
        remediation_id = "RM-001" if finding_id == "MV-001" else "RM-002"
        root_resolved = False
        control_implemented = True
        if finding_id == "MV-001":
            rationale = (
                "Phase 7/7.1 implements monitoring, challenger review, high-volatility escalation, "
                "and Phase 8 restricts standalone 99% use. The Gaussian far-tail calibration "
                "weakness remains empirically present, so root cause is not resolved."
            )
        else:
            rationale = (
                "Phase 7/7.1 implements rolling exception, clustering, and dependence monitoring. "
                "Historical and latest frozen evidence still show temporal-dependence warning, "
                "so root cause is not resolved."
            )
        rows.append(
            {
                "finding_id": finding_id,
                "severity": finding["severity"],
                "original_status": finding["status"],
                "closure_criteria": finding["closure_criteria"],
                "remediation_id": remediation_id,
                "remediation_status": "COMPLETED",
                "evidence": remediation.loc[finding_id, "evidence"],
                "root_cause_resolved": root_resolved,
                "compensating_control_implemented": control_implemented,
                "closure_criteria_satisfied": False,
                "recommended_finding_status": "OPEN",
                "rationale": rationale,
            }
        )
    return pd.DataFrame.from_records(rows)


def _build_final_decision(evidence: dict[str, Any], closure: pd.DataFrame) -> dict[str, Any]:
    open_findings = closure.loc[closure["recommended_finding_status"].eq("OPEN"), "finding_id"].tolist()
    closed_findings = closure.loc[~closure["recommended_finding_status"].eq("OPEN"), "finding_id"].tolist()
    return {
        "validation_id": "V2-MR-001-INITIAL",
        "model_id": "MR-001",
        "model_version": "0.1.0",
        "decision": DECISION,
        "decision_date": DECISION_DATE,
        "intended_use_assessed": (
            "Daily internal market-risk monitoring, portfolio loss-threshold awareness, "
            "model comparison, and project risk reporting for the hypothetical ETF portfolio."
        ),
        "supported_use": [
            "Transparent baseline one-day Gaussian VaR/ES reference for internal monitoring context.",
            "95% loss-threshold awareness when interpreted with clustering/dependence monitoring.",
            "Model comparison and risk reporting when challenger outputs and open findings are shown.",
        ],
        "restricted_or_prohibited_use": [
            "MR-001 99% Gaussian VaR must not be used as a standalone far-tail risk measure.",
            "99% outputs require challenger context, far-tail monitoring, and high-volatility escalation.",
            "High-volatility periods require heightened review before relying on MR-001 tail estimates.",
            "Not for regulatory capital, real trading limits, live institutional systems, or automated decisions.",
        ],
        "open_findings": open_findings,
        "closed_findings": closed_findings,
        "remediation_status": [
            {"remediation_id": "RM-001", "finding_id": "MV-001", "status": "COMPLETED"},
            {"remediation_id": "RM-002", "finding_id": "MV-002", "status": "COMPLETED"},
        ],
        "key_supporting_evidence": {
            "implementation_verification": "464/464 independent comparisons matched; max absolute difference 0.0.",
            "conceptual": "Excess kurtosis and heavier empirical 99% loss tail than Gaussian-implied tail.",
            "mr001_95": "4.82% exception rate with Kupiec p-value 0.7281 but conditional-coverage p-value 0.0346.",
            "mr001_99": "41/1804 exceptions, 2.27% rate, full-sample Kupiec/conditional coverage rejection.",
            "challengers": "Historical and FHS improve 99% unconditional coverage but no challenger is universally superior.",
            "data_quality": "5/5 deterministic corruptions detected and blocked; no DQ finding opened.",
            "monitoring": "Latest frozen 99% v1.1 snapshot remains RED with challenger review and high-vol escalation.",
        },
        "residual_risks": [
            "Gaussian far-tail calibration weakness remains unresolved.",
            "Exception clustering/temporal dependence remains unresolved.",
            "99% empirical tail evidence is finite and regime-dependent.",
            "Challengers have their own limitations and are not approved replacements.",
            "Monitoring replay is frozen historical evidence, not live/current status.",
        ],
        "required_controls": [
            "Monitoring framework v1.1 with far-tail, dependence, challenger-review, volatility-context, and DQ gates.",
            "Challenger comparison for 99% MR-001 interpretation.",
            "High-volatility escalation when far-tail performance watch is AMBER or RED.",
            "Phase 6 data-quality controls must block material corruptions before risk outputs are used.",
            "Open findings MV-001/MV-002 must remain visible until root cause or governance closure is justified.",
        ],
        "revalidation_triggers": [
            "Material methodology change.",
            "Material change to intended use.",
            "Material change to portfolio scope.",
            "Sustained RED far-tail performance.",
            "Repeated dependence or clustering escalation.",
            "Persistent challenger divergence.",
            "Material data-quality control failure.",
            "Significant input-data or source change.",
        ],
        "limitations": [
            "Educational portfolio project, not a real bank validation.",
            "Public ETF proxies and daily adjusted-close data.",
            "One-day horizon and fixed frozen historical dataset.",
            "Project-specific thresholds and no institutional escalation process.",
            "No regulatory capital or live institutional-system claim.",
        ],
        "decision_rationale": (
            "RESTRICTED_USE is selected because MR-001 is correctly implemented and useful as a transparent "
            "baseline, but the High 99% far-tail finding remains open, latest frozen 99% monitoring remains "
            "RED, and compensating controls reduce reliance risk without fixing the Gaussian tail root cause."
        ),
        "decision_comparison": {
            "VALIDATED": "Rejected: material unresolved High and Moderate findings remain.",
            "VALIDATED_WITH_CONDITIONS": (
                "Rejected: evidence does not support the full stated intended use with conditions alone, "
                "especially standalone 99% far-tail interpretation."
            ),
            "RESTRICTED_USE": (
                "Selected: the model remains useful for transparent baseline and limited internal monitoring "
                "roles, but 99% use must be narrowed and controlled."
            ),
            "NOT_VALIDATED": (
                "Rejected: implementation is correct and 95% unconditional coverage plus monitoring/challenger "
                "controls support meaningful restricted use."
            ),
        },
    }


def _build_release_metrics(evidence: dict[str, Any], decision: dict[str, Any]) -> dict[str, Any]:
    model_comparison = evidence["model_comparison"]
    cluster = evidence["cluster"]
    regime = evidence["regime"]
    es = evidence["es"]
    dq_impact = evidence["dq_impact"]
    dq_controls = evidence["dq_controls"]
    monitoring_snapshot = evidence["monitoring_snapshot"]
    impl = evidence["implementation"]
    conceptual = evidence["conceptual"]["distribution"]
    tail = evidence["conceptual"]["tail_comparison"]

    mr001_95 = _row(model_comparison, model_id="MR-001", confidence_level=0.95)
    mr001_99 = _row(model_comparison, model_id="MR-001", confidence_level=0.99)
    mr001_95_cluster = _row(cluster, model_id="MR-001", confidence_level=0.95)
    mr001_99_regime = _row(regime, model_id="MR-001", confidence_level=0.99, volatility_regime="HIGH_VOL")
    mr001_99_es = _row(es, model_id="MR-001", confidence_level=0.99)
    latest_95 = _row(monitoring_snapshot, confidence_level=0.95)
    latest_99 = _row(monitoring_snapshot, confidence_level=0.99)
    largest_impacts = dq_impact[
        (
            dq_impact["scenario_id"].eq("DQ-03")
            & dq_impact["model_id"].eq("MR-001")
            & dq_impact["confidence_level"].eq(0.99)
        )
        | (
            dq_impact["scenario_id"].eq("DQ-05")
            & dq_impact["model_id"].eq("MR-001")
            & dq_impact["confidence_level"].eq(0.95)
        )
    ][["scenario_id", "model_id", "confidence_level", "relative_var_change", "risk_pipeline_allowed"]].to_dict(
        orient="records"
    )
    return {
        "test_count": 179,
        "implementation_verification": {
            "comparisons": int(impl["comparison_count"]),
            "match_fraction": float(impl["match_fraction"]),
            "max_absolute_difference": float(impl["max_absolute_difference"]),
        },
        "conceptual": {
            "excess_kurtosis": float(conceptual["excess_kurtosis"]),
            "empirical_99_loss_quantile": float(tail["empirical_99_loss_quantile"]),
            "gaussian_99_loss_quantile": float(tail["gaussian_99_loss_quantile"]),
        },
        "mr001_95": {
            "exception_count": int(mr001_95["exception_count"]),
            "observation_count": int(mr001_95["observation_count"]),
            "exception_rate": float(mr001_95["exception_rate"]),
            "kupiec_p_value": float(mr001_95["kupiec_p_value"]),
            "conditional_coverage_p_value": float(mr001_95["christoffersen_cc_p_value"]),
            "max_cluster_length": int(mr001_95_cluster["max_cluster_length"]),
        },
        "mr001_99": {
            "exception_count": int(mr001_99["exception_count"]),
            "observation_count": int(mr001_99["observation_count"]),
            "exception_rate": float(mr001_99["exception_rate"]),
            "high_vol_exception_rate": float(mr001_99_regime["exception_rate"]),
            "high_vol_concentration_ratio": float(
                mr001_99_regime["high_vol_exception_concentration_ratio"]
            ),
            "realized_loss_to_es_ratio": float(mr001_99_es["realized_loss_to_es_ratio"]),
        },
        "challengers_99": {
            "mr002_exception_rate": float(_row(model_comparison, model_id="MR-002", confidence_level=0.99)["exception_rate"]),
            "mr003_exception_rate": float(_row(model_comparison, model_id="MR-003", confidence_level=0.99)["exception_rate"]),
            "mr004_exception_rate": float(_row(model_comparison, model_id="MR-004", confidence_level=0.99)["exception_rate"]),
        },
        "data_quality": {
            "scenarios": 5,
            "detected": int(dq_controls.groupby("scenario_id")["detected"].any().sum()),
            "blocked": int(dq_controls.groupby("scenario_id")["blocking_control_triggered"].any().sum()),
            "false_negatives": int(dq_controls["false_negative"].sum()),
            "largest_material_impact_examples": largest_impacts,
        },
        "monitoring_latest": {
            "as_of_date": str(latest_95["as_of_date"]),
            "mr001_95_status": str(latest_95["overall_status"]),
            "mr001_99_status": str(latest_99["overall_status"]),
            "snapshot_scope": str(latest_95["snapshot_scope"]),
        },
        "final_decision": decision["decision"],
    }


def _render_validation_report(evidence: dict[str, Any], closure: pd.DataFrame, decision: dict[str, Any], metrics: dict[str, Any]) -> str:
    findings = evidence["findings"]
    remediation = pd.read_csv("governance/remediation_log.csv", keep_default_na=False)
    comparison = evidence["monitoring_comparison"]
    stress = evidence["stress_summary"]
    return f"""# Market Risk Model Validation Report

## 1. Executive Summary

This report validates MR-001, the Gaussian Parametric VaR / ES model for a hypothetical SPY/QQQ/TLT/GLD portfolio. The validation covers conceptual soundness, independent implementation verification, challenger benchmarking, outcomes and regime analysis, sensitivity, data quality, formal findings, remediation, and ongoing monitoring.

Final validation decision: **{decision["decision"]}**. MR-001 is correctly implemented and useful as a transparent baseline, but it is not supported as a standalone 99% far-tail risk measure. MV-001 and MV-002 remain open.

## 2. Model Identification

- Model ID: MR-001
- Version: 0.1.0
- Methodology: rolling Gaussian one-day VaR / ES
- Owner role: Model Owner / Developer
- Validator role: Independent Validation
- Materiality: High within the project framework
- Portfolio: SPY / QQQ / TLT / GLD
- Horizon: one trading day
- Confidence levels: 95% and 99%

## 3. Purpose and Intended Use

Original intended use was daily internal market-risk monitoring, portfolio loss-threshold awareness, model comparison, and project risk reporting. Final supported use is narrower: transparent baseline monitoring and comparison, with restricted 99% interpretation and required challenger/monitoring context.

## 4. Validation Scope

Phases 2 through 7.1 covered conceptual diagnostics, independent implementation verification, challenger benchmarking, outcomes and stability analysis, data-quality impact, findings/remediation tracking, and monitoring framework hardening.

## 5. Data Assessment

The validation uses frozen public adjusted-close ETF data. Core hashes are recorded in generated summaries. Phase 6 injected five deterministic data-quality failures; all five were detected and blocked. Data limitations remain: public ETF proxies, daily data, finite history, and vendor-revision risk if data are refreshed.

## 6. Conceptual Soundness

The return distribution has excess kurtosis of {metrics["conceptual"]["excess_kurtosis"]:.4f}. The empirical 99% loss quantile is {metrics["conceptual"]["empirical_99_loss_quantile"]:.4%}, compared with a fitted Gaussian 99% loss quantile of {metrics["conceptual"]["gaussian_99_loss_quantile"]:.4%}. This supports a far-tail conceptual concern, especially in high-volatility regimes.

## 7. Implementation Verification

Independent verification matched {metrics["implementation_verification"]["comparisons"]}/{metrics["implementation_verification"]["comparisons"]} comparisons, with match fraction {metrics["implementation_verification"]["match_fraction"]:.1f} and maximum absolute difference {metrics["implementation_verification"]["max_absolute_difference"]:.1f}. The observed weakness is not explained by a known implementation defect.

## 8. Challenger Benchmarking

At 99%, MR-001 recorded {metrics["mr001_99"]["exception_count"]}/{metrics["mr001_99"]["observation_count"]} exceptions. MR-002, MR-003, and MR-004 recorded exception rates of {metrics["challengers_99"]["mr002_exception_rate"]:.2%}, {metrics["challengers_99"]["mr003_exception_rate"]:.2%}, and {metrics["challengers_99"]["mr004_exception_rate"]:.2%}. Empirical and filtered challengers improve some unconditional tail coverage dimensions, but no challenger is established as universally superior or approved.

## 9. Outcomes Analysis

MR-001 95% exception frequency is {metrics["mr001_95"]["exception_rate"]:.2%}, close to the nominal rate, with Kupiec p-value {metrics["mr001_95"]["kupiec_p_value"]:.4f}. Conditional coverage p-value is {metrics["mr001_95"]["conditional_coverage_p_value"]:.4f}, and max project cluster length is {metrics["mr001_95"]["max_cluster_length"]}.

MR-001 99% exception frequency is {metrics["mr001_99"]["exception_rate"]:.2%}, versus a 1% nominal tail rate. Realized loss to ES on 99% exception dates is {metrics["mr001_99"]["realized_loss_to_es_ratio"]:.4f}.

## 10. Regime Analysis

Retrospective Phase 2/5 regimes show MR-001 99% HIGH_VOL exception rate of {metrics["mr001_99"]["high_vol_exception_rate"]:.2%} and high-vol concentration ratio {metrics["mr001_99"]["high_vol_concentration_ratio"]:.2f}. These are descriptive validation regimes, not live monitoring thresholds.

## 11. Sensitivity and Stability

Sensitivity covered 125/250/500-day windows, 95%/97.5%/99% confidence levels, EWMA lambdas 0.94/0.97/0.99, and fixed portfolio variants. Results were not used for post-hoc model selection. Tail-sample warnings remain important for high confidence levels and shorter empirical windows.

## 12. Stress Testing

V1 deterministic stress testing remains relevant scenario context. The largest deterministic baseline loss is {stress.sort_values("portfolio_pnl").iloc[0]["scenario_name"]} at {stress.sort_values("portfolio_pnl").iloc[0]["portfolio_pnl"]:.2%}. This is static project stress evidence, not regulatory stress capital.

## 13. Data Quality Impact

Phase 6 detected {metrics["data_quality"]["detected"]}/5 and blocked {metrics["data_quality"]["blocked"]}/5 deterministic corruptions, with {metrics["data_quality"]["false_negatives"]} false negatives. Material bad-data examples would have distorted VaR materially if allowed downstream, including QQQ x100 bad print and synthetic adjustment discontinuity. No DQ finding was opened because controls blocked the scenarios.

## 14. Formal Findings

{_markdown_table(findings[["finding_id", "severity", "status", "title", "recommendation"]])}

Phase 8 closure assessment:

{_markdown_table(closure[["finding_id", "severity", "root_cause_resolved", "compensating_control_implemented", "closure_criteria_satisfied", "recommended_finding_status"]])}

## 15. Ongoing Monitoring

Phase 7 v1.0 was deliberately conservative and produced alert saturation. Phase 7.1 preserved all numeric thresholds and introduced v1.1 semantics that separate hard performance signals, temporal dependence, challenger disagreement, volatility context, and data-quality failures.

{_markdown_table(comparison)}

The latest monitoring snapshot is frozen historical evidence as of {metrics["monitoring_latest"]["as_of_date"]}, not live/current monitoring.

## 16. Remediation Assessment

{_markdown_table(remediation)}

RM-001 and RM-002 are completed as monitoring/control implementation actions. Completion does not mean the underlying Gaussian tail or temporal dependence root causes are eliminated.

## 17. Residual Model Risk

Residual risks remain: Gaussian far-tail calibration weakness, exception clustering, finite empirical tails, challenger limitations, proxy data, and lack of live institutional monitoring/escalation.

## 18. Final Validation Decision

Decision: **{decision["decision"]}**.

Decision comparison:

- VALIDATED: {decision["decision_comparison"]["VALIDATED"]}
- VALIDATED_WITH_CONDITIONS: {decision["decision_comparison"]["VALIDATED_WITH_CONDITIONS"]}
- RESTRICTED_USE: {decision["decision_comparison"]["RESTRICTED_USE"]}
- NOT_VALIDATED: {decision["decision_comparison"]["NOT_VALIDATED"]}

## 19. Required Controls / Restrictions

{_bullet_list(decision["restricted_or_prohibited_use"] + decision["required_controls"])}

## 20. Revalidation Triggers

{_bullet_list(decision["revalidation_triggers"])}

## 21. Limitations

{_bullet_list(decision["limitations"] + ["No real organizational independence.", "Finite empirical tails.", "No regulatory capital claim."])}

## 22. Artifact Index

- `data/artifacts/final_validation_decision.json`
- `data/artifacts/finding_closure_assessment.csv`
- `data/artifacts/release_metrics.json`
- `data/artifacts/model_comparison.csv`
- `data/artifacts/implementation_verification_summary.json`
- `data/artifacts/data_quality_summary.json`
- `data/artifacts/monitoring_summary.json`
- `reports/executive_summary.md`
- `reports/monitoring_report.md`
"""


def _render_executive_summary(evidence: dict[str, Any], decision: dict[str, Any], metrics: dict[str, Any]) -> str:
    return f"""# Executive Summary

This project validates MR-001, a rolling Gaussian Parametric VaR / ES model for a hypothetical liquid ETF portfolio. The validation asks whether MR-001 is fit for daily internal market-risk monitoring, portfolio loss-threshold awareness, model comparison, and project risk reporting.

The implementation is correct against the independent project reference: {metrics["implementation_verification"]["comparisons"]}/{metrics["implementation_verification"]["comparisons"]} comparisons matched with zero maximum absolute difference. The main weakness is methodological, not coding-related. The frozen portfolio return sample has excess kurtosis of {metrics["conceptual"]["excess_kurtosis"]:.2f}, and the empirical 99% loss quantile is materially larger than the Gaussian-implied 99% loss quantile.

MR-001 performs differently at 95% and 99%. At 95%, exception frequency is {metrics["mr001_95"]["exception_rate"]:.2%} with Kupiec p-value {metrics["mr001_95"]["kupiec_p_value"]:.4f}, but clustering remains visible. At 99%, MR-001 records {metrics["mr001_99"]["exception_count"]}/{metrics["mr001_99"]["observation_count"]} exceptions, a {metrics["mr001_99"]["exception_rate"]:.2%} exception rate versus a 1% nominal tail. High-volatility periods are especially weak, with a {metrics["mr001_99"]["high_vol_exception_rate"]:.2%} 99% exception rate.

Challengers provide useful context but not a clean replacement. Historical and filtered historical challengers improve some 99% unconditional coverage dimensions, while volatility-responsive Gaussian estimates still show far-tail pressure and empirical challengers remain sample-limited.

Data-quality testing injected five deterministic corruptions. All five were detected and blocked, with zero false negatives. This prevented severe hypothetical VaR distortions from flowing downstream.

Formal findings remain open: MV-001 for 99% Gaussian far-tail weakness and MV-002 for temporal dependence/clustering. Monitoring and challenger controls were implemented and assessed, but they are compensating controls, not root-cause elimination.

Final validation decision: **{decision["decision"]}**. MR-001 may be used as a transparent baseline and limited internal monitoring model, but 99% Gaussian VaR must not be interpreted as a standalone far-tail risk measure. 99% use requires challenger context, monitoring, high-volatility escalation, and visible open-findings governance.
"""


def _render_readme(evidence: dict[str, Any], decision: dict[str, Any], metrics: dict[str, Any]) -> str:
    return f"""# Bank-Style Market Risk Model Validation & Governance Lab

Educational portfolio project for market risk model validation. It builds a full validation lifecycle around MR-001, a rolling Gaussian VaR / Expected Shortfall model for a hypothetical SPY / QQQ / TLT / GLD portfolio. It is not for live institutional use, regulatory capital, or compliance claims.

## What This Project Demonstrates

- Independent implementation verification inside a single repository
- Conceptual challenge of Gaussian tail assumptions
- Challenger benchmarking against historical, EWMA, and filtered historical methods
- Outcomes analysis across frequency, clustering, severity, and volatility regimes
- Deterministic market-data quality failure testing
- Formal findings, remediation tracking, monitoring, and final validation decisioning

## Validation Case

MR-001 estimates one-day 95% and 99% VaR / ES under a rolling Gaussian return assumption. The validation question is whether that model is fit for daily internal market-risk monitoring, portfolio loss-threshold awareness, model comparison, and project risk reporting for the hypothetical portfolio.

## Key Findings

- Independent verification matched {metrics["implementation_verification"]["comparisons"]}/{metrics["implementation_verification"]["comparisons"]} calculations with zero maximum absolute difference.
- MR-001 99% Gaussian VaR recorded {metrics["mr001_99"]["exception_count"]}/{metrics["mr001_99"]["observation_count"]} exceptions, a {metrics["mr001_99"]["exception_rate"]:.2%} exception rate versus a 1% nominal tail.
- MR-001 95% exception frequency is close to nominal at {metrics["mr001_95"]["exception_rate"]:.2%}, but exceptions are clustered.
- HIGH_VOL 99% exception rate is {metrics["mr001_99"]["high_vol_exception_rate"]:.2%}, with concentration ratio {metrics["mr001_99"]["high_vol_concentration_ratio"]:.2f}.
- Historical and FHS challengers improve some 99% coverage dimensions but retain dependence and finite-tail limitations.
- Data-quality controls detected and blocked {metrics["data_quality"]["detected"]}/5 injected data failures with {metrics["data_quality"]["false_negatives"]} false negatives.

## Validation Lifecycle

Inventory -> Conceptual Soundness -> Implementation Verification -> Challengers -> Outcomes -> Sensitivity -> Data Quality -> Findings -> Monitoring -> Final Decision

## Final Validation Decision

Decision: **{decision["decision"]}**.

Supported use: transparent baseline one-day Gaussian VaR / ES reference, model comparison, and limited internal monitoring with visible caveats.

Restricted use: MR-001 99% Gaussian VaR must not be used as a standalone far-tail risk measure. 99% interpretation requires challenger context, v1.1 monitoring, data-quality gates, and high-volatility escalation. The latest monitoring snapshot is historical frozen-data evidence as of {metrics["monitoring_latest"]["as_of_date"]}, not live/current status.

## Architecture

```text
configs/                  # Data, model, validation, monitoring, stress configs
governance/               # Inventory, materiality, findings, remediation
src/market_risk_toolkit/  # Data, portfolio, risk, validation, DQ, monitoring code
data/artifacts/           # Deterministic CSV/JSON validation evidence
reports/                  # Executive summary, final report, monitoring report
tests/                    # Unit, integration, governance, and consistency tests
```

## Reproduce

```bash
python -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
pip install -r requirements.txt
pytest -q
```

Core tests are deterministic and do not require live yfinance access. The frozen V2 artifacts use a local development data cutoff rather than an open-ended market-data refresh.

## Reports and Artifacts

- [Executive summary](reports/executive_summary.md)
- [Full V2 validation report](reports/v2_validation_report.md)
- [Monitoring report](reports/monitoring_report.md)
- [Model inventory](governance/model_inventory.csv)
- [Findings registry](governance/findings.csv)
- [Remediation log](governance/remediation_log.csv)
- [Final validation decision JSON](data/artifacts/final_validation_decision.json)
- [Release metrics registry](data/artifacts/release_metrics.json)

## Limitations

- Educational portfolio project using public ETF proxies
- Project-level independent reference implementation, not organizational independence
- One-day horizon and daily adjusted-close data
- Fixed historical dataset and finite empirical tails
- Project-specific monitoring thresholds
- No real institutional approval authority
- No regulatory capital, live institutional use, or compliance claim
"""


def _update_model_inventory(path: Path, decision: dict[str, Any]) -> None:
    table = pd.read_csv(path, keep_default_na=False)
    mask = table["model_id"].eq("MR-001")
    table.loc[mask, "validation_status"] = decision["decision"]
    table.loc[mask, "last_validation_date"] = DECISION_DATE
    table.loc[mask, "next_review_date"] = "2027-08-14"
    table.loc[mask, "notes"] = (
        "Final V2 decision RESTRICTED_USE; supported as transparent baseline and limited "
        "internal monitoring reference; standalone 99% far-tail interpretation prohibited; "
        "MV-001/MV-002 remain open."
    )
    table.to_csv(path, index=False)


def _update_remediation_log(path: Path) -> None:
    table = pd.read_csv(path, keep_default_na=False)
    table["status"] = "COMPLETED"
    table["completion_date"] = DECISION_DATE
    table.to_csv(path, index=False)


def _row(frame: pd.DataFrame, **filters: object) -> pd.Series:
    mask = pd.Series(True, index=frame.index)
    for column, value in filters.items():
        if isinstance(value, float):
            mask &= frame[column].astype(float).sub(value).abs().lt(1e-12)
        else:
            mask &= frame[column].eq(value)
    rows = frame[mask]
    if len(rows) != 1:
        raise ValueError(f"Expected one row for {filters}, found {len(rows)}")
    return rows.iloc[0]


def _read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _json_dumps(payload: dict[str, Any]) -> str:
    return json.dumps(_json_clean(payload), indent=2, sort_keys=True) + "\n"


def _json_clean(value: Any) -> Any:
    if isinstance(value, dict):
        return {str(key): _json_clean(item) for key, item in value.items()}
    if isinstance(value, list):
        return [_json_clean(item) for item in value]
    if isinstance(value, tuple):
        return [_json_clean(item) for item in value]
    if hasattr(value, "item"):
        return _json_clean(value.item())
    return value


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


def _bullet_list(items: list[str]) -> str:
    return "\n".join(f"- {item}" for item in items)


def main() -> int:
    paths = build_phase8_artifacts()
    print(_json_dumps({key: str(value) for key, value in paths.__dict__.items()}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
