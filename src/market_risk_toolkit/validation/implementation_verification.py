"""Phase 3 implementation verification orchestration."""

from __future__ import annotations

import argparse
import ast
import hashlib
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Callable

import numpy as np
import pandas as pd
import yaml

from market_risk_toolkit.risk import metrics as developer_metrics
from market_risk_toolkit.risk.config import load_risk_config
from market_risk_toolkit.risk.io import load_portfolio_returns
from market_risk_toolkit.validation.independent.gaussian_reference import (
    gaussian_expected_shortfall,
    gaussian_var,
)
from market_risk_toolkit.validation.independent.historical_reference import (
    historical_expected_shortfall,
    historical_var,
)

COMPARISON_COLUMNS = [
    "case_id",
    "case_type",
    "date_or_fixture",
    "model",
    "metric",
    "confidence_level",
    "developer_value",
    "validator_value",
    "absolute_difference",
    "relative_difference",
    "tolerance",
    "match",
]
FORBIDDEN_IMPORT_PREFIXES = (
    "market_risk_toolkit.risk.metrics",
    "market_risk_toolkit.risk",
)


@dataclass(frozen=True)
class VerificationCase:
    """A deterministic return window used for implementation verification."""

    case_id: str
    case_type: str
    date_or_fixture: str
    returns: pd.Series


@dataclass(frozen=True)
class ImplementationVerificationPaths:
    """Paths written during implementation verification."""

    comparison_csv: Path
    summary_json: Path
    report_md: Path


def run_implementation_verification(
    *,
    risk_config_path: str | Path = "configs/risk_engine.yaml",
    validation_plan_path: str | Path = "configs/validation/validation_plan.yaml",
    output_dir: str | Path = "data/artifacts",
    report_path: str | Path = "reports/sections/implementation_verification.md",
    frozen_window_count: int = 50,
) -> ImplementationVerificationPaths:
    """Run all Phase 3 verification cases and write artifacts."""

    risk_config = load_risk_config(risk_config_path)
    validation_plan = _load_yaml(validation_plan_path)
    tolerance = float(
        validation_plan["thresholds"]["implementation_verification"]["numeric_abs_tolerance"]
    )
    required_match_fraction = float(
        validation_plan["thresholds"]["implementation_verification"]["required_match_fraction"]
    )
    confidence_levels = risk_config.confidence_levels

    frozen_returns = load_portfolio_returns(risk_config.returns_path)
    cases = (
        build_hand_checkable_cases()
        + build_synthetic_cases()
        + build_frozen_portfolio_window_cases(
            frozen_returns,
            window=risk_config.window,
            count=frozen_window_count,
        )
    )
    comparison = compare_implementations(cases, confidence_levels, tolerance)
    forbidden_import_check = check_independent_imports()
    summary = build_verification_summary(
        comparison,
        validation_plan=validation_plan,
        risk_config=risk_config,
        input_data_hash=sha256_file(risk_config.returns_path),
        tolerance=tolerance,
        required_match_fraction=required_match_fraction,
        forbidden_import_check=forbidden_import_check,
    )

    output = Path(output_dir)
    report = Path(report_path)
    output.mkdir(parents=True, exist_ok=True)
    report.parent.mkdir(parents=True, exist_ok=True)
    paths = ImplementationVerificationPaths(
        comparison_csv=output / "implementation_verification.csv",
        summary_json=output / "implementation_verification_summary.json",
        report_md=report,
    )
    comparison.to_csv(paths.comparison_csv, index=False)
    paths.summary_json.write_text(_json_dumps(summary), encoding="utf-8")
    paths.report_md.write_text(_render_report(summary), encoding="utf-8")
    return paths


def build_hand_checkable_cases() -> list[VerificationCase]:
    """Create deterministic small fixtures for manual inspection."""

    fixtures = {
        "symmetric_returns": [-0.02, -0.01, 0.0, 0.01, 0.02],
        "constant_ish_returns": [0.001, 0.001, 0.001, 0.001, 0.001],
        "negatively_skewed_returns": [-0.08, -0.03, -0.01, 0.0, 0.005, 0.008, 0.01],
        "one_extreme_loss": [-0.20, -0.01, -0.005, 0.0, 0.004, 0.006, 0.009],
        "mixed_with_nan": [-0.03, np.nan, -0.01, 0.0, 0.01, 0.02],
    }
    return [
        VerificationCase(
            case_id=f"hand_{idx:02d}",
            case_type="hand_fixture",
            date_or_fixture=name,
            returns=pd.Series(values, name="portfolio_return", dtype=float),
        )
        for idx, (name, values) in enumerate(fixtures.items(), start=1)
    ]


def build_synthetic_cases() -> list[VerificationCase]:
    """Create fixed-seed synthetic windows."""

    rng = np.random.default_rng(20260814)
    cases = {
        "fixed_seed_gaussian": rng.normal(0.0002, 0.01, size=500),
        "fixed_seed_heavy_tailed": rng.standard_t(df=4, size=500) * 0.01,
        "fixed_seed_negative_skew": -(rng.exponential(scale=0.008, size=500) - 0.008),
    }
    return [
        VerificationCase(
            case_id=f"synthetic_{idx:02d}",
            case_type="synthetic",
            date_or_fixture=name,
            returns=pd.Series(values, name="portfolio_return", dtype=float),
        )
        for idx, (name, values) in enumerate(cases.items(), start=1)
    ]


def build_frozen_portfolio_window_cases(
    returns: pd.Series,
    *,
    window: int = 250,
    count: int = 50,
) -> list[VerificationCase]:
    """Select evenly spaced frozen portfolio windows without cherry-picking."""

    clean = returns.dropna().astype(float).copy()
    if len(clean) < window:
        raise ValueError("Frozen portfolio return series is shorter than the verification window.")
    end_positions = np.linspace(window, len(clean), num=count, dtype=int)
    unique_positions = list(dict.fromkeys(int(position) for position in end_positions))
    cases = []
    for idx, end_position in enumerate(unique_positions, start=1):
        window_returns = clean.iloc[end_position - window : end_position].copy()
        window_end = clean.index[end_position - 1].strftime("%Y-%m-%d")
        cases.append(
            VerificationCase(
                case_id=f"frozen_window_{idx:02d}",
                case_type="frozen_portfolio_window",
                date_or_fixture=window_end,
                returns=window_returns,
            )
        )
    return cases


def compare_implementations(
    cases: list[VerificationCase],
    confidence_levels: tuple[float, ...],
    tolerance: float,
) -> pd.DataFrame:
    """Compare developer and independent reference calculations."""

    calculators: dict[tuple[str, str], tuple[Callable[[pd.Series, float], float], Callable]] = {
        ("gaussian", "var"): (developer_metrics.parametric_var, gaussian_var),
        ("gaussian", "es"): (developer_metrics.parametric_es, gaussian_expected_shortfall),
        ("historical", "var"): (developer_metrics.historical_var, historical_var),
        ("historical", "es"): (developer_metrics.historical_es, historical_expected_shortfall),
    }
    rows = []
    for case in cases:
        original = case.returns.copy(deep=True)
        for confidence_level in confidence_levels:
            for (model, metric), (developer_fn, validator_fn) in calculators.items():
                developer_value = float(developer_fn(case.returns, confidence_level))
                validator_value = float(validator_fn(case.returns.to_numpy(), confidence_level))
                absolute_difference = abs(developer_value - validator_value)
                rows.append(
                    {
                        "case_id": case.case_id,
                        "case_type": case.case_type,
                        "date_or_fixture": case.date_or_fixture,
                        "model": model,
                        "metric": metric,
                        "confidence_level": float(confidence_level),
                        "developer_value": developer_value,
                        "validator_value": validator_value,
                        "absolute_difference": absolute_difference,
                        "relative_difference": _relative_difference(
                            developer_value,
                            validator_value,
                        ),
                        "tolerance": tolerance,
                        "match": bool(absolute_difference <= tolerance),
                    }
                )
        pd.testing.assert_series_equal(case.returns, original)
    return pd.DataFrame(rows, columns=COMPARISON_COLUMNS)


def build_verification_summary(
    comparison: pd.DataFrame,
    *,
    validation_plan: dict,
    risk_config: object,
    input_data_hash: str,
    tolerance: float,
    required_match_fraction: float,
    forbidden_import_check: dict,
) -> dict:
    """Summarize implementation verification output."""

    match_count = int(comparison["match"].sum())
    comparison_count = int(len(comparison))
    mismatch_count = comparison_count - match_count
    return {
        "validation_id": validation_plan["validation_id"],
        "model_id": validation_plan["model_id"],
        "developer_module": "market_risk_toolkit.risk.metrics",
        "reference_modules": [
            "market_risk_toolkit.validation.independent.gaussian_reference",
            "market_risk_toolkit.validation.independent.historical_reference",
        ],
        "forbidden_import_check": forbidden_import_check,
        "case_count": int(comparison["case_id"].nunique()),
        "comparison_count": comparison_count,
        "match_count": match_count,
        "mismatch_count": mismatch_count,
        "match_fraction": float(match_count / comparison_count if comparison_count else 0.0),
        "required_match_fraction": required_match_fraction,
        "max_absolute_difference": float(comparison["absolute_difference"].max()),
        "mean_absolute_difference": float(comparison["absolute_difference"].mean()),
        "by_model": _group_summary(comparison, "model"),
        "by_metric": _group_summary(comparison, "metric"),
        "by_confidence_level": _group_summary(comparison, "confidence_level"),
        "input_data_path": str(risk_config.returns_path),
        "input_data_hash": input_data_hash,
        "tolerance": tolerance,
        "limitations": [
            "Verification tests implementation consistency with stated formulas, not model conceptual soundness.",
            "Historical quantiles use NumPy/Pandas linear interpolation convention.",
            "Frozen portfolio windows are deterministic and evenly spaced, not exhaustive.",
            "No final validation decision is assigned in Phase 3.",
        ],
        "implementation_conclusion": (
            "Implementation verification passed within the predeclared numerical tolerance."
            if mismatch_count == 0 and match_count / comparison_count >= required_match_fraction
            else "Implementation discrepancies were identified and require investigation."
        ),
        "final_validation_decision": None,
    }


def check_independent_imports() -> dict:
    """Verify independent reference modules do not import developer risk modules."""

    source_files = sorted(Path("src/market_risk_toolkit/validation/independent").glob("*.py"))
    violations: list[str] = []
    for path in source_files:
        tree = ast.parse(path.read_text(encoding="utf-8"))
        for node in ast.walk(tree):
            imported_path = None
            if isinstance(node, ast.Import):
                for alias in node.names:
                    imported_path = alias.name
                    if _is_forbidden_import(imported_path):
                        violations.append(f"{path}:{imported_path}")
            elif isinstance(node, ast.ImportFrom):
                imported_path = node.module or ""
                if _is_forbidden_import(imported_path):
                    violations.append(f"{path}:{imported_path}")
    return {
        "passed": not violations,
        "forbidden_import_prefixes": list(FORBIDDEN_IMPORT_PREFIXES),
        "checked_files": [str(path) for path in source_files],
        "violations": violations,
    }


def sha256_file(path: str | Path) -> str:
    digest = hashlib.sha256()
    with Path(path).open("rb") as file:
        for chunk in iter(lambda: file.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run Phase 3 implementation verification.")
    parser.add_argument("--risk-config", default="configs/risk_engine.yaml")
    parser.add_argument("--validation-plan", default="configs/validation/validation_plan.yaml")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    paths = run_implementation_verification(
        risk_config_path=args.risk_config,
        validation_plan_path=args.validation_plan,
    )
    print(
        _json_dumps(
            {
                "comparison_csv": str(paths.comparison_csv),
                "summary_json": str(paths.summary_json),
                "report_md": str(paths.report_md),
            }
        )
    )
    return 0


def _is_forbidden_import(imported_path: str) -> bool:
    return any(
        imported_path == prefix or imported_path.startswith(f"{prefix}.")
        for prefix in FORBIDDEN_IMPORT_PREFIXES
    )


def _relative_difference(developer_value: float, validator_value: float) -> float | None:
    denominator = abs(validator_value)
    if denominator < 1.0e-12:
        return None
    return float((developer_value - validator_value) / denominator)


def _group_summary(comparison: pd.DataFrame, column: str) -> dict[str, dict[str, float | int]]:
    grouped = {}
    for key, group in comparison.groupby(column):
        grouped[str(key)] = {
            "comparison_count": int(len(group)),
            "match_count": int(group["match"].sum()),
            "mismatch_count": int((~group["match"]).sum()),
            "max_absolute_difference": float(group["absolute_difference"].max()),
            "mean_absolute_difference": float(group["absolute_difference"].mean()),
        }
    return grouped


def _load_yaml(path: str | Path) -> dict:
    with Path(path).open("r", encoding="utf-8") as file:
        return yaml.safe_load(file)


def _json_dumps(payload: dict) -> str:
    return json.dumps(payload, indent=2, sort_keys=True) + "\n"


def _render_report(summary: dict) -> str:
    mismatch_text = (
        "No mismatches exceeded the predeclared tolerance."
        if summary["mismatch_count"] == 0
        else "Mismatches were preserved in the comparison artifact and require investigation."
    )
    return f"""# Implementation Verification - MR-001

## 1. Objective

Phase 3 tests whether the existing developer implementation correctly
calculates the formulas it claims to implement. This phase separates
implementation risk from methodology risk. The Phase 2 fat-tail concern remains
a conceptual assumption issue and does not imply an implementation defect.

## 2. Independence Design

Independent reference calculations live under
`market_risk_toolkit.validation.independent`. The reference modules do not
import `market_risk_toolkit.risk.metrics` or developer risk calculation modules.
The orchestration layer compares developer outputs with independent reference
outputs. This is project-level implementation independence, not organizational
independence.

Forbidden import check passed: `{summary["forbidden_import_check"]["passed"]}`.

## 3. Formula Conventions

Gaussian VaR uses `mu + sigma * Phi^-1(1 - alpha)` as the lower-tail return
quantile and reports `max(0, -quantile)` as positive-loss VaR.

Gaussian ES uses lower-tail expected return
`mu - sigma * phi(z) / (1 - alpha)` where `z = Phi^-1(1 - alpha)`, then reports
`max(0, -tail_mean)` as positive-loss ES.

Historical VaR uses quantile probability `1 - alpha`, NumPy/Pandas linear
interpolation, and positive-loss reporting.

Historical ES includes observations at or below the historical VaR threshold,
averages those tail returns, and reports the positive loss.

All formulas drop NaN values, require at least two observations, use confidence
levels between 0 and 1, and Gaussian volatility uses sample standard deviation
with `ddof = 1`.

## 4. Test Cases

Evidence categories include hand-checkable fixtures, fixed-seed synthetic
windows, and 50 deterministic frozen portfolio windows selected evenly across
the Phase 0 local portfolio return snapshot.

## 5. Results

- Total cases: {summary["case_count"]}
- Total comparisons: {summary["comparison_count"]}
- Matches: {summary["match_count"]}
- Mismatches: {summary["mismatch_count"]}
- Match fraction: {summary["match_fraction"]:.6f}
- Required match fraction: {summary["required_match_fraction"]:.6f}
- Maximum absolute difference: {summary["max_absolute_difference"]:.12g}
- Mean absolute difference: {summary["mean_absolute_difference"]:.12g}
- Absolute tolerance: {summary["tolerance"]:.1e}

## 6. Discrepancy Analysis

{mismatch_text}

If future discrepancies appear, likely root-cause categories include formula
defect, sign convention, quantile convention, degrees-of-freedom convention,
alignment issue, numerical precision, or unknown.

## 7. Conclusion

{summary["implementation_conclusion"]} No final model validation decision is
assigned in Phase 3.
"""


if __name__ == "__main__":
    raise SystemExit(main())
