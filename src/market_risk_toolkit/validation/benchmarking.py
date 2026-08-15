"""Phase 4 challenger model benchmarking."""

from __future__ import annotations

import argparse
import json
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
import yaml

from market_risk_toolkit.risk.config import load_risk_config
from market_risk_toolkit.risk.io import load_portfolio_returns
from market_risk_toolkit.risk.models import EWMAModelConfig, FilteredHistoricalConfig
from market_risk_toolkit.risk.models import ewma as ewma_model
from market_risk_toolkit.risk.models import filtered_historical as fhs_model
from market_risk_toolkit.risk.models import gaussian as gaussian_model
from market_risk_toolkit.risk.models import historical as historical_model
from market_risk_toolkit.validation.backtesting import (
    christoffersen_conditional_coverage_test,
    christoffersen_independence_test,
    kupiec_unconditional_coverage,
)

MODEL_ORDER = ["MR-001", "MR-002", "MR-003", "MR-004"]
MODEL_NAMES = {
    "MR-001": "Gaussian Parametric VaR / ES",
    "MR-002": "Historical Simulation VaR / ES",
    "MR-003": "EWMA Gaussian VaR / ES",
    "MR-004": "Filtered Historical Simulation VaR / ES",
}


@dataclass(frozen=True)
class ChallengerBenchmarkPaths:
    """Paths written by Phase 4 benchmarking."""

    forecasts_csv: Path
    comparison_csv: Path
    divergence_csv: Path
    summary_json: Path
    report_md: Path


def run_challenger_benchmarking(
    *,
    risk_config_path: str | Path = "configs/risk_engine.yaml",
    validation_plan_path: str | Path = "configs/validation/validation_plan.yaml",
    ewma_config_path: str | Path = "configs/models/ewma_var.yaml",
    fhs_config_path: str | Path = "configs/models/filtered_historical.yaml",
    output_dir: str | Path = "data/artifacts",
    report_path: str | Path = "reports/sections/challenger_benchmarking.md",
) -> ChallengerBenchmarkPaths:
    """Generate Phase 4 challenger forecasts, comparisons, and memo."""

    risk_config = load_risk_config(risk_config_path)
    validation_plan = _load_yaml(validation_plan_path)
    ewma_config = _load_ewma_config(ewma_config_path).validated()
    fhs_config = _load_fhs_config(fhs_config_path).validated()
    returns = load_portfolio_returns(risk_config.returns_path)
    confidence_levels = risk_config.confidence_levels

    forecasts = build_unified_forecasts(
        returns=returns,
        confidence_levels=confidence_levels,
        estimation_window=risk_config.window,
        ewma_config=ewma_config,
        fhs_config=fhs_config,
    )
    common_forecasts = filter_common_comparison_sample(forecasts)
    comparison = build_model_comparison(common_forecasts, confidence_levels)
    divergence = build_challenger_divergence(
        common_forecasts,
        amber_threshold=float(
            validation_plan["thresholds"]["challenger_divergence"]["amber_relative_difference"]
        ),
        red_threshold=float(
            validation_plan["thresholds"]["challenger_divergence"]["red_relative_difference"]
        ),
    )
    summary = build_challenger_summary(
        forecasts=forecasts,
        common_forecasts=common_forecasts,
        comparison=comparison,
        divergence=divergence,
        ewma_config=ewma_config,
        fhs_config=fhs_config,
        validation_plan=validation_plan,
        risk_config=risk_config,
    )

    output = Path(output_dir)
    report = Path(report_path)
    output.mkdir(parents=True, exist_ok=True)
    report.parent.mkdir(parents=True, exist_ok=True)
    paths = ChallengerBenchmarkPaths(
        forecasts_csv=output / "challenger_forecasts.csv",
        comparison_csv=output / "model_comparison.csv",
        divergence_csv=output / "challenger_divergence.csv",
        summary_json=output / "challenger_model_summary.json",
        report_md=report,
    )
    forecasts.to_csv(paths.forecasts_csv, index=False)
    comparison.to_csv(paths.comparison_csv, index=False)
    divergence.to_csv(paths.divergence_csv, index=False)
    paths.summary_json.write_text(_json_dumps(summary), encoding="utf-8")
    paths.report_md.write_text(_render_report(summary, comparison, divergence), encoding="utf-8")
    return paths


def build_unified_forecasts(
    *,
    returns: pd.Series,
    confidence_levels: tuple[float, ...],
    estimation_window: int,
    ewma_config: EWMAModelConfig,
    fhs_config: FilteredHistoricalConfig,
) -> pd.DataFrame:
    """Build a unified long-form forecast table for MR-001 through MR-004."""

    clean = returns.dropna().astype(float).copy()
    records: list[dict[str, Any]] = []
    for end in range(estimation_window, len(clean)):
        forecast_date = pd.Timestamp(clean.index[end])
        window_returns = clean.iloc[end - estimation_window : end].copy()
        realized_return = float(clean.iloc[end])
        realized_loss = -realized_return
        for confidence_level in confidence_levels:
            forecasts = [
                gaussian_model.forecast(
                    window_returns,
                    date=forecast_date,
                    confidence_level=confidence_level,
                    estimation_window=estimation_window,
                ),
                historical_model.forecast(
                    window_returns,
                    date=forecast_date,
                    confidence_level=confidence_level,
                    estimation_window=estimation_window,
                ),
                ewma_model.forecast(
                    window_returns,
                    date=forecast_date,
                    confidence_level=confidence_level,
                    config=ewma_config,
                ),
                fhs_model.forecast(
                    window_returns,
                    date=forecast_date,
                    confidence_level=confidence_level,
                    config=fhs_config,
                ),
            ]
            for forecast in forecasts:
                row = asdict(forecast)
                row["date"] = forecast.date.strftime("%Y-%m-%d")
                row["realized_return"] = realized_return
                row["realized_loss"] = realized_loss
                row.update(_flatten_method_parameters(forecast.method_parameters))
                row.pop("method_parameters")
                records.append(row)
    return pd.DataFrame.from_records(records).sort_values(
        ["date", "confidence_level", "model_id"]
    )


def filter_common_comparison_sample(forecasts: pd.DataFrame) -> pd.DataFrame:
    """Keep only date/confidence pairs where all four models have forecasts."""

    counts = forecasts.groupby(["date", "confidence_level"])["model_id"].nunique()
    valid_pairs = counts[counts == len(MODEL_ORDER)].index
    common = forecasts.set_index(["date", "confidence_level"]).loc[valid_pairs].reset_index()
    return common.sort_values(["date", "confidence_level", "model_id"])


def build_model_comparison(
    common_forecasts: pd.DataFrame,
    confidence_levels: tuple[float, ...],
) -> pd.DataFrame:
    """Backtest all models on the common comparison sample."""

    records: list[dict[str, Any]] = []
    for confidence_level in confidence_levels:
        level_data = common_forecasts[common_forecasts["confidence_level"] == confidence_level]
        for model_id in MODEL_ORDER:
            model_data = level_data[level_data["model_id"] == model_id].sort_values("date")
            exceedances = (model_data["realized_loss"] > model_data["var"]).astype(int)
            kupiec = kupiec_unconditional_coverage(exceedances, confidence_level)
            independence = christoffersen_independence_test(exceedances)
            conditional = christoffersen_conditional_coverage_test(exceedances, confidence_level)
            exception_count = int(exceedances.sum())
            observation_count = int(len(model_data))
            exception_rows = model_data.loc[exceedances.astype(bool)]
            severity = np.nan
            excess_loss = np.nan
            if not exception_rows.empty:
                usable = exception_rows[exception_rows["var"].abs() > 1.0e-12]
                if not usable.empty:
                    severity = float((usable["realized_loss"] / usable["var"]).mean())
                    excess_loss = float((usable["realized_loss"] - usable["var"]).mean())
            records.append(
                {
                    "model_id": model_id,
                    "model_name": MODEL_NAMES[model_id],
                    "confidence_level": float(confidence_level),
                    "observation_count": observation_count,
                    "mean_var": float(model_data["var"].mean()),
                    "mean_es": float(model_data["es"].mean()),
                    "expected_exception_rate": float(1.0 - confidence_level),
                    "exception_count": exception_count,
                    "exception_rate": float(exception_count / observation_count),
                    "kupiec_lr": float(kupiec.statistic),
                    "kupiec_p_value": float(kupiec.p_value),
                    "christoffersen_independence_lr": float(independence.statistic),
                    "christoffersen_independence_p_value": float(independence.p_value),
                    "christoffersen_cc_lr": float(conditional.statistic),
                    "christoffersen_cc_p_value": float(conditional.p_value),
                    "average_exceedance_severity": severity,
                    "average_exceedance_loss_minus_var": excess_loss,
                    "common_comparison_sample": True,
                }
            )
    return pd.DataFrame.from_records(records)


def build_challenger_divergence(
    common_forecasts: pd.DataFrame,
    *,
    amber_threshold: float,
    red_threshold: float,
) -> pd.DataFrame:
    """Aggregate challenger VaR divergence relative to MR-001."""

    rows: list[dict[str, Any]] = []
    for confidence_level, level_data in common_forecasts.groupby("confidence_level"):
        pivot = level_data.pivot(index="date", columns="model_id", values="var")
        baseline = pivot["MR-001"]
        for model_id in ("MR-002", "MR-003", "MR-004"):
            denominator = baseline.where(baseline.abs() > 1.0e-12)
            relative = (pivot[model_id] - baseline) / denominator
            absolute_relative = relative.abs().dropna()
            rows.append(
                {
                    "model_id": model_id,
                    "model_name": MODEL_NAMES[model_id],
                    "confidence_level": float(confidence_level),
                    "baseline_model_id": "MR-001",
                    "observation_count": int(absolute_relative.shape[0]),
                    "mean_absolute_relative_divergence": float(absolute_relative.mean()),
                    "median_absolute_relative_divergence": float(absolute_relative.median()),
                    "fraction_above_amber_threshold": float((absolute_relative > amber_threshold).mean()),
                    "fraction_above_red_threshold": float((absolute_relative > red_threshold).mean()),
                    "amber_threshold": amber_threshold,
                    "red_threshold": red_threshold,
                    "threshold_interpretation": "project methodology-divergence indicators, not regulatory limits",
                }
            )
    return pd.DataFrame.from_records(rows)


def build_challenger_summary(
    *,
    forecasts: pd.DataFrame,
    common_forecasts: pd.DataFrame,
    comparison: pd.DataFrame,
    divergence: pd.DataFrame,
    ewma_config: EWMAModelConfig,
    fhs_config: FilteredHistoricalConfig,
    validation_plan: dict,
    risk_config: object,
) -> dict[str, Any]:
    native_counts = {
        model_id: int(count)
        for model_id, count in forecasts.groupby("model_id")["date"].nunique().to_dict().items()
    }
    common_dates = pd.to_datetime(common_forecasts["date"].drop_duplicates().sort_values())
    return {
        "validation_id": validation_plan["validation_id"],
        "model_id": validation_plan["model_id"],
        "phase": 4,
        "models": MODEL_NAMES,
        "native_forecast_counts_by_model": native_counts,
        "common_comparison_sample": {
            "start_date": common_dates.min().strftime("%Y-%m-%d"),
            "end_date": common_dates.max().strftime("%Y-%m-%d"),
            "observation_count": int(common_dates.shape[0]),
            "all_models_share_same_dates": bool(len(set(native_counts.values())) == 1),
        },
        "ewma_config": {
            "model_id": ewma_config.model_id,
            "estimation_window": ewma_config.estimation_window,
            "lambda": ewma_config.lambda_,
            "seed_window": ewma_config.seed_window,
            "mean_assumption": ewma_config.mean_assumption,
            "confidence_levels": list(ewma_config.confidence_levels),
        },
        "fhs_config": {
            "model_id": fhs_config.model_id,
            "estimation_window": fhs_config.estimation_window,
            "lambda": fhs_config.lambda_,
            "seed_window": fhs_config.seed_window,
            "mean_assumption": fhs_config.mean_assumption,
            "confidence_levels": list(fhs_config.confidence_levels),
            "residual_pool_size": fhs_config.estimation_window - fhs_config.seed_window,
            "tail_sample_limitation": "At 99%, about 230 residuals leave only a small far-tail sample.",
        },
        "comparison_records": comparison.to_dict(orient="records"),
        "divergence_records": divergence.to_dict(orient="records"),
        "risk_config_path": str(risk_config.returns_path),
        "final_validation_decision": None,
        "phase_4_conclusion": _phase_4_conclusion(divergence),
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run Phase 4 challenger benchmarking.")
    parser.add_argument("--risk-config", default="configs/risk_engine.yaml")
    parser.add_argument("--validation-plan", default="configs/validation/validation_plan.yaml")
    parser.add_argument("--ewma-config", default="configs/models/ewma_var.yaml")
    parser.add_argument("--fhs-config", default="configs/models/filtered_historical.yaml")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    paths = run_challenger_benchmarking(
        risk_config_path=args.risk_config,
        validation_plan_path=args.validation_plan,
        ewma_config_path=args.ewma_config,
        fhs_config_path=args.fhs_config,
    )
    print(
        _json_dumps(
            {
                "forecasts_csv": str(paths.forecasts_csv),
                "comparison_csv": str(paths.comparison_csv),
                "divergence_csv": str(paths.divergence_csv),
                "summary_json": str(paths.summary_json),
                "report_md": str(paths.report_md),
            }
        )
    )
    return 0


def _load_ewma_config(path: str | Path) -> EWMAModelConfig:
    payload = _load_yaml(path)
    return EWMAModelConfig(
        model_id=payload["model_id"],
        estimation_window=int(payload["estimation_window"]),
        lambda_=float(payload["lambda"]),
        seed_window=int(payload["seed_window"]),
        mean_assumption=payload["mean_assumption"],
        confidence_levels=tuple(float(level) for level in payload["confidence_levels"]),
    )


def _load_fhs_config(path: str | Path) -> FilteredHistoricalConfig:
    payload = _load_yaml(path)
    return FilteredHistoricalConfig(
        model_id=payload["model_id"],
        estimation_window=int(payload["estimation_window"]),
        lambda_=float(payload["lambda"]),
        seed_window=int(payload["seed_window"]),
        mean_assumption=payload["mean_assumption"],
        confidence_levels=tuple(float(level) for level in payload["confidence_levels"]),
    )


def _load_yaml(path: str | Path) -> dict:
    with Path(path).open("r", encoding="utf-8") as file:
        return yaml.safe_load(file)


def _flatten_method_parameters(parameters: dict[str, Any]) -> dict[str, Any]:
    flattened = {}
    for key, value in parameters.items():
        if key == "lambda":
            flattened["lambda"] = value
        else:
            flattened[key] = value
    return flattened


def _phase_4_conclusion(divergence: pd.DataFrame) -> str:
    if (divergence["fraction_above_red_threshold"] > 0.25).any():
        return "Challenger evidence indicates material methodology divergence."
    if (divergence["fraction_above_amber_threshold"] > 0.25).any():
        return "Challenger evidence indicates moderate methodology divergence requiring Phase 5 analysis."
    return "Challenger evidence does not indicate material divergence on average, but Phase 5 should still assess regimes and sensitivity."


def _json_dumps(payload: dict) -> str:
    return json.dumps(payload, indent=2, sort_keys=True, default=_json_default) + "\n"


def _json_default(value: object) -> object:
    if isinstance(value, (np.floating, np.integer)):
        return value.item()
    if isinstance(value, float) and np.isnan(value):
        return None
    raise TypeError(f"Object of type {type(value).__name__} is not JSON serializable")


def _render_report(summary: dict[str, Any], comparison: pd.DataFrame, divergence: pd.DataFrame) -> str:
    sample = summary["common_comparison_sample"]
    comparison_lines = "\n".join(
        (
            f"| {row.model_id} | {row.confidence_level:.2f} | {row.mean_var:.4%} | "
            f"{row.mean_es:.4%} | {int(row.exception_count)} | {row.exception_rate:.2%} | "
            f"{row.kupiec_p_value:.4f} | {row.christoffersen_independence_p_value:.4f} | "
            f"{row.christoffersen_cc_p_value:.4f} | "
            f"{'' if pd.isna(row.average_exceedance_severity) else f'{row.average_exceedance_severity:.3f}'} |"
        )
        for row in comparison.itertuples(index=False)
    )
    divergence_lines = "\n".join(
        (
            f"| {row.model_id} | {row.confidence_level:.2f} | "
            f"{row.mean_absolute_relative_divergence:.2%} | "
            f"{row.median_absolute_relative_divergence:.2%} | "
            f"{row.fraction_above_amber_threshold:.2%} | {row.fraction_above_red_threshold:.2%} |"
        )
        for row in divergence.itertuples(index=False)
    )
    return f"""# Challenger Benchmarking - MR-001

## 1. Objective

Phase 4 tests whether reasonable alternative methodologies produce materially
different VaR / ES estimates or lightweight backtesting evidence from MR-001.
It does not select a model winner or replace MR-001.

## 2. Models

- MR-001: Gaussian Parametric VaR / ES, the primary model under validation.
- MR-002: Historical Simulation VaR / ES, the existing V1 benchmark/challenger.
- MR-003: EWMA Gaussian VaR / ES, an implemented Phase 4 challenger.
- MR-004: Filtered Historical Simulation VaR / ES, an implemented Phase 4 challenger.

## 3. Challenger Methodologies

MR-003 uses a 250-day estimation window, lambda 0.94, a 20-day sample-variance
seed, and a zero-mean one-day forecasting assumption. The zero-mean assumption
is a challenger-model choice, not a universal claim about returns.

MR-004 uses the same EWMA volatility filter. Seed observations initialize
variance and are not standardized into the residual pool. Each residual uses a
volatility estimate based only on prior returns. The forecast volatility uses
returns through t-1. At 99%, about 230 residuals provide only a small far-tail
sample, so FHS 99% ES should not be treated as highly precise.

## 4. Sample Alignment

Native forecast counts by model: {summary["native_forecast_counts_by_model"]}.
The common comparison sample runs from {sample["start_date"]} to
{sample["end_date"]} with {sample["observation_count"]} observations. All four
models share the same forecast dates: {sample["all_models_share_same_dates"]}.

## 5. VaR / ES And Backtesting Comparison

Average exceedance severity is defined as realized loss divided by VaR for
exception observations only.

| Model | CL | Mean VaR | Mean ES | Exceptions | Exception Rate | Kupiec p | Indep. p | CC p | Avg Severity |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
{comparison_lines}

## 6. Divergence From MR-001

Phase 1 amber/red thresholds are project methodology-divergence indicators, not
regulatory limits or automatic failure rules.

| Challenger | CL | Mean Abs. Rel. Div. | Median Abs. Rel. Div. | Above 15% | Above 25% |
| --- | ---: | ---: | ---: | ---: | ---: |
{divergence_lines}

## 7. Interpretation

Challenger evidence should be read as methodology evidence, not model selection.
Volatility-responsive models can change estimates materially when recent
volatility differs from the rolling sample average. FHS can reveal empirical
residual-tail behavior, but the finite residual pool makes 99% tail estimates
sample-limited.

## 8. Limitations

- Public ETF proxy portfolio.
- Fixed 250-day window.
- Lambda 0.94 is predeclared and not tuned.
- Zero-mean EWMA/FHS assumption.
- Finite FHS residual tail, especially at 99%.
- Same historical sample is used across methodologies.
- Phase 4 does not perform full regime, sensitivity, or stability analysis.

## 9. Phase 4 Conclusion

{summary["phase_4_conclusion"]} No final validation decision is assigned.
"""


if __name__ == "__main__":
    raise SystemExit(main())
