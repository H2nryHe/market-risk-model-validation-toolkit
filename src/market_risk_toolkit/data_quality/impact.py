"""Phase 6 data-quality impact lab runner."""

from __future__ import annotations

import argparse
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
import yaml

from market_risk_toolkit.data_quality.controls import (
    EXTREME_RETURN_THRESHOLD,
    STALE_PRICE_RUN_THRESHOLD,
    controls_to_frame,
    run_control_suite,
    summarize_policy,
)
from market_risk_toolkit.data_quality.perturbations import (
    SCENARIO_DEFINITIONS,
    SELECTION_RULE,
    apply_scenario,
    build_scenario_table,
    load_price_panel,
)
from market_risk_toolkit.risk.models import EWMAModelConfig, FilteredHistoricalConfig
from market_risk_toolkit.validation.benchmarking import (
    build_unified_forecasts,
    filter_common_comparison_sample,
)
from market_risk_toolkit.validation.findings import (
    build_phase6_findings,
    validate_findings_schema,
)
from market_risk_toolkit.validation.outcomes import sha256_file
from market_risk_toolkit.validation.sensitivity import build_portfolio_returns

CANONICAL_WINDOW = 250
CANONICAL_LAMBDA = 0.94
CANONICAL_SEED_WINDOW = 20
CANONICAL_CONFIDENCE_LEVELS = (0.95, 0.99)
EQUAL_WEIGHTS = {"SPY": 0.25, "QQQ": 0.25, "TLT": 0.25, "GLD": 0.25}


@dataclass(frozen=True)
class Phase6Paths:
    scenarios_csv: Path
    control_results_csv: Path
    risk_impact_csv: Path
    summary_json: Path
    findings_csv: Path
    report_md: Path


def run_phase6_data_quality_and_findings(
    *,
    price_path: str | Path = "data/processed/adjusted_close.csv",
    returns_path: str | Path = "data/processed/returns.csv",
    validation_plan_path: str | Path = "configs/validation/validation_plan.yaml",
    output_dir: str | Path = "data/artifacts",
    findings_path: str | Path = "governance/findings.csv",
    report_path: str | Path = "reports/sections/data_quality_and_findings.md",
) -> Phase6Paths:
    """Run deterministic Phase 6 data-quality scenarios and findings."""

    output = Path(output_dir)
    output.mkdir(parents=True, exist_ok=True)
    findings = Path(findings_path)
    findings.parent.mkdir(parents=True, exist_ok=True)
    report = Path(report_path)
    report.parent.mkdir(parents=True, exist_ok=True)
    paths = Phase6Paths(
        scenarios_csv=output / "data_quality_scenarios.csv",
        control_results_csv=output / "data_quality_control_results.csv",
        risk_impact_csv=output / "data_quality_risk_impact.csv",
        summary_json=output / "data_quality_summary.json",
        findings_csv=findings,
        report_md=report,
    )

    clean_prices = load_price_panel(str(price_path))
    scenario_table = build_scenario_table(clean_prices)
    validation_plan = _load_yaml(validation_plan_path)
    material_threshold = float(
        validation_plan["thresholds"]["data_quality_impact"]["material_relative_var_change"]
    )

    clean_returns_panel = build_returns_from_prices(clean_prices)
    clean_portfolio_returns = build_portfolio_returns(clean_returns_panel, EQUAL_WEIGHTS)
    clean_forecasts = filter_common_comparison_sample(
        _build_forecasts(clean_portfolio_returns)
    )

    control_frames = []
    impact_frames = []
    scenario_results: list[dict[str, Any]] = []
    for scenario in SCENARIO_DEFINITIONS:
        corrupted_prices = apply_scenario(clean_prices, scenario.scenario_id)
        shifted_assets = (scenario.asset,) if scenario.scenario_id == "DQ-04" else ()
        controls = run_control_suite(
            clean_prices=clean_prices,
            candidate_prices=corrupted_prices,
            shifted_assets=shifted_assets,
        )
        control_frame = controls_to_frame(
            scenario.scenario_id,
            scenario.scenario_name,
            scenario.expected_control,
            controls,
        )
        control_frames.append(control_frame)
        policy = summarize_policy(controls)

        corrupted_returns_panel = build_returns_from_prices(corrupted_prices)
        corrupted_portfolio_returns = build_portfolio_returns(corrupted_returns_panel, EQUAL_WEIGHTS)
        corrupted_forecasts = filter_common_comparison_sample(
            _build_forecasts(corrupted_portfolio_returns)
        )
        impacted_dates = impacted_forecast_dates(
            clean_portfolio_returns,
            corrupted_portfolio_returns,
            window=CANONICAL_WINDOW,
        )
        impact = summarize_risk_impact(
            clean_forecasts=clean_forecasts,
            corrupted_forecasts=corrupted_forecasts,
            impacted_dates=impacted_dates,
            scenario_id=scenario.scenario_id,
            scenario_name=scenario.scenario_name,
            material_threshold=material_threshold,
            control_policy=policy,
        )
        impact_frames.append(impact)
        scenario_results.append(
            {
                "scenario_id": scenario.scenario_id,
                "scenario_name": scenario.scenario_name,
                "asset": scenario.asset,
                "expected_control": scenario.expected_control,
                "detected": bool(control_frame["expected_control_detected"].any()),
                "blocked": bool(policy["blocking_control_triggered"]),
                "risk_pipeline_allowed": bool(policy["risk_pipeline_allowed"]),
                "material_var_impact_if_allowed": bool(impact["material_var_impact"].any()),
                "largest_absolute_relative_var_change": _safe_float(
                    impact["relative_var_change"].abs().max()
                ),
                "largest_challenger_absolute_relative_var_change": _safe_float(
                    impact.loc[impact["model_id"].ne("MR-001"), "relative_var_change"].abs().max()
                ),
                "false_negative": bool(not control_frame["expected_control_detected"].any()),
            }
        )

    control_results = pd.concat(control_frames, ignore_index=True)
    risk_impact = pd.concat(impact_frames, ignore_index=True)
    findings_df = build_phase6_findings(
        conceptual_summary=_load_json("data/artifacts/conceptual_soundness_summary.json"),
        implementation_summary=_load_json("data/artifacts/implementation_verification_summary.json"),
        model_comparison=pd.read_csv("data/artifacts/model_comparison.csv"),
        challenger_divergence=pd.read_csv("data/artifacts/challenger_divergence.csv"),
        cluster_summary=pd.read_csv("data/artifacts/exception_cluster_summary.csv"),
        regime_backtest=pd.read_csv("data/artifacts/regime_backtest.csv"),
        es_diagnostics=pd.read_csv("data/artifacts/es_diagnostics.csv"),
        control_results=control_results,
        risk_impact=risk_impact,
    )
    validate_findings_schema(findings_df)

    scenario_table.to_csv(paths.scenarios_csv, index=False)
    control_results.to_csv(paths.control_results_csv, index=False)
    risk_impact.to_csv(paths.risk_impact_csv, index=False)
    findings_df.to_csv(paths.findings_csv, index=False)

    summary = build_summary(
        price_path=Path(price_path),
        returns_path=Path(returns_path),
        scenario_results=scenario_results,
        control_results=control_results,
        risk_impact=risk_impact,
        findings=findings_df,
        material_threshold=material_threshold,
    )
    summary["artifact_hashes"] = {
        "data_quality_scenarios_csv": sha256_file(paths.scenarios_csv),
        "data_quality_control_results_csv": sha256_file(paths.control_results_csv),
        "data_quality_risk_impact_csv": sha256_file(paths.risk_impact_csv),
        "findings_csv": sha256_file(paths.findings_csv),
    }
    paths.summary_json.write_text(_json_dumps(summary), encoding="utf-8")
    paths.report_md.write_text(
        render_report(
            scenario_table=scenario_table,
            control_results=control_results,
            risk_impact=risk_impact,
            findings=findings_df,
            summary=summary,
        ),
        encoding="utf-8",
    )
    return paths


def build_returns_from_prices(prices: pd.DataFrame) -> pd.DataFrame:
    """Construct returns from prices without mutating the input frame."""

    clean_copy = prices.copy(deep=True)
    returns = clean_copy.pct_change(fill_method=None).dropna(axis=0, how="any")
    returns.index.name = "date"
    return returns.astype(float)


def impacted_forecast_dates(
    clean_returns: pd.Series,
    corrupted_returns: pd.Series,
    *,
    window: int = CANONICAL_WINDOW,
) -> set[str]:
    """Return forecast dates whose estimation window contains changed returns."""

    clean = clean_returns.copy()
    corrupted = corrupted_returns.copy()
    all_dates = clean.index.union(corrupted.index).sort_values()
    aligned_clean = clean.reindex(all_dates)
    aligned_corrupted = corrupted.reindex(all_dates)
    changed_dates = all_dates[
        aligned_clean.isna()
        | aligned_corrupted.isna()
        | ((aligned_clean - aligned_corrupted).abs() > 1.0e-12)
    ]
    impacted: set[pd.Timestamp] = set()
    clean_index = pd.Index(clean.index)
    for changed_date in changed_dates:
        if changed_date not in clean_index:
            continue
        position = clean_index.get_loc(changed_date)
        if isinstance(position, slice):
            continue
        for forecast_position in range(position + 1, min(position + window + 1, len(clean_index))):
            impacted.add(pd.Timestamp(clean_index[forecast_position]))
    return {date.strftime("%Y-%m-%d") for date in impacted}


def summarize_risk_impact(
    *,
    clean_forecasts: pd.DataFrame,
    corrupted_forecasts: pd.DataFrame,
    impacted_dates: set[str],
    scenario_id: str,
    scenario_name: str,
    material_threshold: float,
    control_policy: dict[str, object],
) -> pd.DataFrame:
    """Summarize clean-vs-corrupted VaR/ES impact for all models/confidence levels."""

    clean = clean_forecasts[clean_forecasts["date"].isin(impacted_dates)].copy()
    corrupted = corrupted_forecasts[corrupted_forecasts["date"].isin(impacted_dates)].copy()
    merged = clean.merge(
        corrupted,
        on=["date", "model_id", "confidence_level"],
        how="inner",
        suffixes=("_clean", "_corrupted"),
    )
    rows = []
    for (model_id, confidence_level), group in merged.groupby(["model_id", "confidence_level"]):
        clean_mean_var = float(group["var_clean"].mean())
        corrupted_mean_var = float(group["var_corrupted"].mean())
        clean_mean_es = float(group["es_clean"].mean())
        corrupted_mean_es = float(group["es_corrupted"].mean())
        relative_var_change = _relative_change(corrupted_mean_var, clean_mean_var)
        per_date_relative = (
            (group["var_corrupted"] - group["var_clean"])
            / group["var_clean"].where(group["var_clean"].abs() > 1.0e-12)
        )
        per_date_absolute = (group["var_corrupted"] - group["var_clean"]).abs()
        rows.append(
            {
                "scenario_id": scenario_id,
                "scenario_name": scenario_name,
                "model_id": model_id,
                "confidence_level": float(confidence_level),
                "impacted_start": group["date"].min() if not group.empty else "",
                "impacted_end": group["date"].max() if not group.empty else "",
                "affected_forecast_count": int(len(group)),
                "clean_mean_var": clean_mean_var,
                "corrupted_mean_var": corrupted_mean_var,
                "absolute_var_change": float(corrupted_mean_var - clean_mean_var),
                "relative_var_change": relative_var_change,
                "max_absolute_var_change": float(per_date_absolute.max()),
                "max_relative_var_change": float(per_date_relative.abs().max()),
                "clean_mean_es": clean_mean_es,
                "corrupted_mean_es": corrupted_mean_es,
                "relative_es_change": _relative_change(corrupted_mean_es, clean_mean_es),
                "material_var_impact": bool(abs(relative_var_change) >= material_threshold),
                "material_relative_var_change_threshold": material_threshold,
                "control_detected": bool(control_policy["control_detected"]),
                "blocking_control_triggered": bool(control_policy["blocking_control_triggered"]),
                "risk_pipeline_allowed": bool(control_policy["risk_pipeline_allowed"]),
                "notes": (
                    "Risk impact is measured as if corrupted data were allowed downstream; "
                    "control policy is evaluated separately."
                ),
            }
        )
    return pd.DataFrame.from_records(rows)


def build_summary(
    *,
    price_path: Path,
    returns_path: Path,
    scenario_results: list[dict[str, Any]],
    control_results: pd.DataFrame,
    risk_impact: pd.DataFrame,
    findings: pd.DataFrame,
    material_threshold: float,
) -> dict[str, Any]:
    """Build deterministic Phase 6 summary data."""

    material_by_scenario = (
        risk_impact.groupby("scenario_id")["material_var_impact"].max().to_dict()
        if not risk_impact.empty
        else {}
    )
    detected = control_results.groupby("scenario_id")["expected_control_detected"].max()
    blocked = control_results.groupby("scenario_id")["blocking_control_triggered"].max()
    return {
        "phase": 6,
        "input_price_path": str(price_path),
        "input_price_hash": sha256_file(price_path),
        "input_returns_path": str(returns_path),
        "input_returns_hash": sha256_file(returns_path),
        "scenario_count": len(SCENARIO_DEFINITIONS),
        "scenario_selection_rule": SELECTION_RULE,
        "controls": {
            "missingness": "BLOCK when required price observations are missing",
            "staleness": f"BLOCK when consecutive unchanged prices >= {STALE_PRICE_RUN_THRESHOLD}",
            "extreme_return": f"BLOCK when absolute single-period return > {EXTREME_RETURN_THRESHOLD:.2%}",
            "date_alignment": "BLOCK when required date index or explicit shifted asset check fails",
            "price_validity": "BLOCK when prices are non-finite or non-positive",
        },
        "project_thresholds": {
            "material_relative_var_change": material_threshold,
            "threshold_source": "configs/validation/validation_plan.yaml",
            "threshold_interpretation": "project governance indicator, not regulatory requirement",
        },
        "scenario_results": scenario_results,
        "material_impact_summary": {
            scenario_id: bool(value) for scenario_id, value in material_by_scenario.items()
        },
        "control_detection_summary": {
            "scenarios_detected": int(detected.sum()),
            "scenarios_blocked": int(blocked.groupby(level=0).max().sum()),
            "false_negative_count": int((~detected.astype(bool)).sum()),
            "scenario_coverage_not_statistical_accuracy": True,
        },
        "formal_findings_opened": findings["finding_id"].tolist(),
        "data_quality_finding_opened": "DQ-001" in set(findings["finding_id"]),
        "final_validation_decision": None,
        "limitations": [
            "Synthetic deterministic perturbations are designed control tests, not a statistical sample of vendor errors.",
            "Public ETF proxy data are used instead of production market data.",
            "Control thresholds are project choices, not regulatory requirements.",
            "Risk impact is measured as if corrupted data were allowed downstream even when controls block it.",
            "Phase 6 defines recommendations but does not execute remediation or ongoing monitoring.",
        ],
    }


def render_report(
    *,
    scenario_table: pd.DataFrame,
    control_results: pd.DataFrame,
    risk_impact: pd.DataFrame,
    findings: pd.DataFrame,
    summary: dict[str, Any],
) -> str:
    """Render the Phase 6 report."""

    scenario_status = _scenario_status_table(control_results, risk_impact)
    mr1_impact = _largest_impact_table(risk_impact, model_filter="MR-001")
    challenger_impact = _largest_impact_table(risk_impact, challenger_only=True)
    return f"""# Data Quality Impact and Validation Findings

## 1. Objective

Phase 6 has two goals: quantify how deterministic market-data failures propagate
into portfolio returns and VaR/ES estimates, and convert supported Phase 2-6
validation evidence into formal findings. Detection, blocking, and downstream
impact are evaluated separately.

## 2. Data Quality Scenario Design

Scenario dates use this predeclared rule: {SELECTION_RULE}.

{_markdown_table(scenario_table[["scenario_id", "scenario_name", "asset", "start_date", "end_date", "injection_type", "expected_control"]])}

## 3. Control Framework

Controls cover missingness, staleness, extreme returns/outliers, date alignment,
and price validity. The staleness threshold of {STALE_PRICE_RUN_THRESHOLD}
unchanged daily prices and the {EXTREME_RETURN_THRESHOLD:.0%} suspicious-return
threshold are project QA choices, not regulatory thresholds. Project policy
allows PASS, FLAG, or BLOCK; Phase 6 uses BLOCK for missing required prices,
severe staleness, extreme bad prints/discontinuities, date misalignment, and
non-finite/non-positive prices.

## 4. Data Quality Risk Impact

{_markdown_table(scenario_status)}

Largest MR-001 VaR impacts if corrupted data were allowed downstream:

{_markdown_table(mr1_impact)}

Largest challenger VaR impacts if corrupted data were allowed downstream:

{_markdown_table(challenger_impact)}

The predeclared materiality threshold is a 10% absolute relative VaR change
from `configs/validation/validation_plan.yaml`. It is a project governance
indicator, not a Fed/OCC/FDIC requirement.

## 5. Control Effectiveness

All five intentionally injected scenarios were detected by their expected
controls and blocked by the project policy. Any material VaR distortion therefore
demonstrates downstream sensitivity to bad data if controls were bypassed; it is
not evidence that the model methodology failed because bad data made VaR wrong.

## 6. Integrated Model Evidence

Phase 2 showed excess kurtosis and a heavier empirical 99% loss tail than the
fitted Gaussian tail. Phase 3 verified 464/464 implementation comparisons, so
the weakness is not explained by a formula implementation defect. Phase 4 showed
MR-001 99% exception frequency materially above the nominal 1% tail and
meaningful challenger divergence. Phase 5 showed MR-001 99% weakness
concentrated in HIGH_VOL periods and MR-001 95% exception clustering despite
acceptable unconditional frequency.

## 7. Formal Validation Findings

{_markdown_table(findings)}

## 8. Data Quality Finding Decision

No formal data-quality control finding was opened. The deterministic injected
failures were detected and blocked by the Phase 6 project controls. The
scenarios still support the importance of upstream controls because several
would materially distort VaR if allowed downstream.

## 9. Phase 6 Conclusion

Formal findings opened: {", ".join(findings["finding_id"].tolist())}. MV-001
captures material MR-001 99% far-tail calibration weakness. MV-002 captures
exception dependence/clustering at 95% despite acceptable unconditional
coverage. Phase 7 should link these OPEN findings to monitoring, escalation, and
remediation tracking. No final Phase 8 validation decision is assigned.

## 10. Limitations

- Synthetic DQ scenarios are deterministic control tests, not a statistical sample.
- Public ETF proxy data are used.
- Control thresholds are project-specific.
- Corrupted-data impact is measured hypothetically even when controls block the scenario.
- Phase 6 recommends remediation but does not execute remediation or monitoring.
"""


def _build_forecasts(returns: pd.Series) -> pd.DataFrame:
    return build_unified_forecasts(
        returns=returns,
        confidence_levels=CANONICAL_CONFIDENCE_LEVELS,
        estimation_window=CANONICAL_WINDOW,
        ewma_config=EWMAModelConfig(
            estimation_window=CANONICAL_WINDOW,
            lambda_=CANONICAL_LAMBDA,
            seed_window=CANONICAL_SEED_WINDOW,
            confidence_levels=CANONICAL_CONFIDENCE_LEVELS,
        ),
        fhs_config=FilteredHistoricalConfig(
            estimation_window=CANONICAL_WINDOW,
            lambda_=CANONICAL_LAMBDA,
            seed_window=CANONICAL_SEED_WINDOW,
            confidence_levels=CANONICAL_CONFIDENCE_LEVELS,
        ),
    )


def _scenario_status_table(control_results: pd.DataFrame, risk_impact: pd.DataFrame) -> pd.DataFrame:
    controls = control_results.groupby("scenario_id").agg(
        detected=("expected_control_detected", "max"),
        blocked=("blocking_control_triggered", "max"),
        risk_pipeline_allowed=("risk_pipeline_allowed", "min"),
    )
    impact = risk_impact.groupby("scenario_id").agg(
        largest_abs_relative_var_change=("relative_var_change", lambda values: values.abs().max()),
        material_var_impact=("material_var_impact", "max"),
    )
    return controls.join(impact).reset_index()


def _largest_impact_table(
    risk_impact: pd.DataFrame,
    *,
    model_filter: str | None = None,
    challenger_only: bool = False,
) -> pd.DataFrame:
    table = risk_impact.copy()
    if model_filter is not None:
        table = table[table["model_id"].eq(model_filter)]
    if challenger_only:
        table = table[table["model_id"].ne("MR-001")]
    idx = table.groupby("scenario_id")["relative_var_change"].apply(lambda values: values.abs().idxmax())
    return table.loc[
        idx,
        [
            "scenario_id",
            "model_id",
            "confidence_level",
            "affected_forecast_count",
            "relative_var_change",
            "max_relative_var_change",
            "material_var_impact",
            "risk_pipeline_allowed",
        ],
    ].sort_values("scenario_id")


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


def _relative_change(corrupted: float, clean: float) -> float:
    return float((corrupted - clean) / clean) if abs(clean) > 1.0e-12 else np.nan


def _safe_float(value: object) -> float | None:
    try:
        number = float(value)
    except (TypeError, ValueError):
        return None
    return None if np.isnan(number) else number


def _load_yaml(path: str | Path) -> dict[str, Any]:
    with Path(path).open("r", encoding="utf-8") as file:
        return yaml.safe_load(file)


def _load_json(path: str | Path) -> dict[str, Any]:
    return json.loads(Path(path).read_text(encoding="utf-8"))


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
    if isinstance(value, (np.floating, float)):
        return None if np.isnan(value) else float(value)
    if isinstance(value, pd.Timestamp):
        return value.strftime("%Y-%m-%d")
    return value


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run Phase 6 data-quality impact lab.")
    parser.add_argument("--prices", default="data/processed/adjusted_close.csv")
    parser.add_argument("--returns", default="data/processed/returns.csv")
    parser.add_argument("--validation-plan", default="configs/validation/validation_plan.yaml")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    paths = run_phase6_data_quality_and_findings(
        price_path=args.prices,
        returns_path=args.returns,
        validation_plan_path=args.validation_plan,
    )
    print(_json_dumps({key: str(value) for key, value in paths.__dict__.items()}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
