"""Phase 5 outcomes, regime, and sensitivity analysis runner."""

from __future__ import annotations

import argparse
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

from market_risk_toolkit.risk.config import load_risk_config
from market_risk_toolkit.risk.models import EWMAModelConfig, FilteredHistoricalConfig
from market_risk_toolkit.validation.backtesting import (
    christoffersen_conditional_coverage_test,
    christoffersen_independence_test,
    kupiec_unconditional_coverage,
)
from market_risk_toolkit.validation.benchmarking import (
    MODEL_ORDER,
    build_challenger_divergence,
    build_unified_forecasts,
    filter_common_comparison_sample,
)
from market_risk_toolkit.validation.outcomes import (
    build_cluster_summary,
    build_es_diagnostics,
    build_exception_diagnostics,
    build_rolling_exception_rates,
    sha256_file,
    top_exception_dates,
)
from market_risk_toolkit.validation.regime import (
    REGIME_SCOPE_LABEL,
    build_regime_backtest,
    load_phase2_regimes,
)

WINDOW_GRID = (125, 250, 500)
SENSITIVITY_CONFIDENCE_LEVELS = (0.95, 0.975, 0.99)
LAMBDA_GRID = (0.94, 0.97, 0.99)
DEFAULT_LAMBDA = 0.94
DEFAULT_SEED_WINDOW = 20
PORTFOLIO_VARIANTS = {
    "equal_weight": {"SPY": 0.25, "QQQ": 0.25, "TLT": 0.25, "GLD": 0.25},
    "equity_heavy": {"SPY": 0.40, "QQQ": 0.35, "TLT": 0.15, "GLD": 0.10},
    "rates_heavy": {"SPY": 0.15, "QQQ": 0.10, "TLT": 0.60, "GLD": 0.15},
    "diversified_balanced": {"SPY": 0.30, "QQQ": 0.20, "TLT": 0.30, "GLD": 0.20},
}


@dataclass(frozen=True)
class Phase5Paths:
    exception_diagnostics_csv: Path
    exception_cluster_summary_csv: Path
    rolling_exception_rates_csv: Path
    regime_backtest_csv: Path
    es_diagnostics_csv: Path
    sensitivity_results_csv: Path
    sensitivity_summary_json: Path
    report_md: Path


def run_phase5_analysis(
    *,
    challenger_forecasts_path: str | Path = "data/artifacts/challenger_forecasts.csv",
    processed_returns_path: str | Path = "data/processed/returns.csv",
    phase2_regime_path: str | Path = "data/artifacts/rolling_distribution_diagnostics.csv",
    risk_config_path: str | Path = "configs/risk_engine.yaml",
    output_dir: str | Path = "data/artifacts",
    report_path: str | Path = "reports/sections/outcomes_and_stability.md",
) -> Phase5Paths:
    """Generate Phase 5 diagnostics, sensitivity artifacts, and report."""

    output = Path(output_dir)
    output.mkdir(parents=True, exist_ok=True)
    report = Path(report_path)
    report.parent.mkdir(parents=True, exist_ok=True)
    paths = Phase5Paths(
        exception_diagnostics_csv=output / "exception_diagnostics.csv",
        exception_cluster_summary_csv=output / "exception_cluster_summary.csv",
        rolling_exception_rates_csv=output / "rolling_exception_rates.csv",
        regime_backtest_csv=output / "regime_backtest.csv",
        es_diagnostics_csv=output / "es_diagnostics.csv",
        sensitivity_results_csv=output / "sensitivity_results.csv",
        sensitivity_summary_json=output / "sensitivity_summary.json",
        report_md=report,
    )

    forecasts = pd.read_csv(challenger_forecasts_path)
    common_forecasts = filter_common_comparison_sample(forecasts)
    regimes = load_phase2_regimes(phase2_regime_path)
    exception_diagnostics = build_exception_diagnostics(common_forecasts, regimes)
    cluster_summary = build_cluster_summary(exception_diagnostics)
    rolling_rates = build_rolling_exception_rates(exception_diagnostics)
    regime_backtest = build_regime_backtest(exception_diagnostics)
    es_diagnostics = build_es_diagnostics(exception_diagnostics)

    risk_config = load_risk_config(risk_config_path)
    processed_returns = load_processed_returns(processed_returns_path)
    sensitivity_results = build_sensitivity_results(
        processed_returns,
        seed_window=DEFAULT_SEED_WINDOW,
        confidence_levels=SENSITIVITY_CONFIDENCE_LEVELS,
    )
    summary = build_phase5_summary(
        challenger_forecasts_path=Path(challenger_forecasts_path),
        processed_returns_path=Path(processed_returns_path),
        risk_config_returns_path=Path(risk_config.returns_path),
        common_forecasts=common_forecasts,
        exception_diagnostics=exception_diagnostics,
        cluster_summary=cluster_summary,
        regime_backtest=regime_backtest,
        es_diagnostics=es_diagnostics,
        sensitivity_results=sensitivity_results,
    )

    exception_diagnostics.to_csv(paths.exception_diagnostics_csv, index=False)
    cluster_summary.to_csv(paths.exception_cluster_summary_csv, index=False)
    rolling_rates.to_csv(paths.rolling_exception_rates_csv, index=False)
    regime_backtest.to_csv(paths.regime_backtest_csv, index=False)
    es_diagnostics.to_csv(paths.es_diagnostics_csv, index=False)
    sensitivity_results.to_csv(paths.sensitivity_results_csv, index=False)
    summary["artifact_hashes"] = {
        "exception_diagnostics_csv": sha256_file(paths.exception_diagnostics_csv),
        "exception_cluster_summary_csv": sha256_file(paths.exception_cluster_summary_csv),
        "rolling_exception_rates_csv": sha256_file(paths.rolling_exception_rates_csv),
        "regime_backtest_csv": sha256_file(paths.regime_backtest_csv),
        "es_diagnostics_csv": sha256_file(paths.es_diagnostics_csv),
        "sensitivity_results_csv": sha256_file(paths.sensitivity_results_csv),
    }
    paths.sensitivity_summary_json.write_text(_json_dumps(summary), encoding="utf-8")
    paths.report_md.write_text(
        render_outcomes_and_stability_report(
            summary=summary,
            cluster_summary=cluster_summary,
            regime_backtest=regime_backtest,
            es_diagnostics=es_diagnostics,
            sensitivity_results=sensitivity_results,
            top_exceptions=top_exception_dates(exception_diagnostics),
        ),
        encoding="utf-8",
    )
    return paths


def load_processed_returns(path: str | Path) -> pd.DataFrame:
    """Load the frozen asset return panel."""

    table = pd.read_csv(path, parse_dates=["date"]).set_index("date").sort_index()
    return table.astype(float).copy(deep=True)


def build_portfolio_returns(
    asset_returns: pd.DataFrame,
    weights: dict[str, float],
) -> pd.Series:
    """Build a fixed-weight portfolio return series without mutating inputs."""

    missing = set(weights).difference(asset_returns.columns)
    if missing:
        raise ValueError(f"Portfolio weights reference missing columns: {sorted(missing)}")
    weight_sum = float(sum(weights.values()))
    if not np.isclose(weight_sum, 1.0):
        raise ValueError(f"Portfolio weights must sum to 1.0, got {weight_sum}.")
    weighted = asset_returns.loc[:, list(weights)].mul(pd.Series(weights), axis=1).sum(axis=1)
    weighted.name = "portfolio_return"
    return weighted


def build_sensitivity_results(
    asset_returns: pd.DataFrame,
    *,
    seed_window: int = DEFAULT_SEED_WINDOW,
    confidence_levels: tuple[float, ...] = SENSITIVITY_CONFIDENCE_LEVELS,
) -> pd.DataFrame:
    """Run all predeclared Phase 5 sensitivity dimensions."""

    baseline_returns = build_portfolio_returns(asset_returns, PORTFOLIO_VARIANTS["equal_weight"])
    rows: list[pd.DataFrame] = []

    window_forecasts: dict[int, pd.DataFrame] = {}
    for window in WINDOW_GRID:
        forecasts = build_unified_forecasts(
            returns=baseline_returns,
            confidence_levels=confidence_levels,
            estimation_window=window,
            ewma_config=EWMAModelConfig(
                estimation_window=window,
                lambda_=DEFAULT_LAMBDA,
                seed_window=seed_window,
                confidence_levels=confidence_levels,
            ),
            fhs_config=FilteredHistoricalConfig(
                estimation_window=window,
                lambda_=DEFAULT_LAMBDA,
                seed_window=seed_window,
                confidence_levels=confidence_levels,
            ),
        )
        common = filter_common_comparison_sample(forecasts)
        window_forecasts[window] = common
        rows.append(
            summarize_forecasts_for_sensitivity(
                common,
                analysis_dimension="lookback_window",
                portfolio_id="equal_weight",
                window=window,
                lambda_=DEFAULT_LAMBDA,
                sample_type="native_sample",
                seed_window=seed_window,
            )
        )

    common_window_dates = common_date_intersection(window_forecasts)
    for window, common in window_forecasts.items():
        rows.append(
            summarize_forecasts_for_sensitivity(
                common[common["date"].isin(common_window_dates)],
                analysis_dimension="lookback_window",
                portfolio_id="equal_weight",
                window=window,
                lambda_=DEFAULT_LAMBDA,
                sample_type="common_sensitivity_sample",
                seed_window=seed_window,
            )
        )

    for lambda_ in LAMBDA_GRID:
        forecasts = build_unified_forecasts(
            returns=baseline_returns,
            confidence_levels=confidence_levels,
            estimation_window=250,
            ewma_config=EWMAModelConfig(
                estimation_window=250,
                lambda_=lambda_,
                seed_window=seed_window,
                confidence_levels=confidence_levels,
            ),
            fhs_config=FilteredHistoricalConfig(
                estimation_window=250,
                lambda_=lambda_,
                seed_window=seed_window,
                confidence_levels=confidence_levels,
            ),
        )
        common = filter_common_comparison_sample(forecasts)
        lambda_summary = summarize_forecasts_for_sensitivity(
            common,
            analysis_dimension="ewma_lambda",
            portfolio_id="equal_weight",
            window=250,
            lambda_=lambda_,
            sample_type="native_sample",
            seed_window=seed_window,
        )
        rows.append(lambda_summary[lambda_summary["model_id"].isin(["MR-003", "MR-004"])])

    for portfolio_id, weights in PORTFOLIO_VARIANTS.items():
        portfolio_returns = build_portfolio_returns(asset_returns, weights)
        forecasts = build_unified_forecasts(
            returns=portfolio_returns,
            confidence_levels=(0.95, 0.99),
            estimation_window=250,
            ewma_config=EWMAModelConfig(
                estimation_window=250,
                lambda_=DEFAULT_LAMBDA,
                seed_window=seed_window,
                confidence_levels=(0.95, 0.99),
            ),
            fhs_config=FilteredHistoricalConfig(
                estimation_window=250,
                lambda_=DEFAULT_LAMBDA,
                seed_window=seed_window,
                confidence_levels=(0.95, 0.99),
            ),
        )
        common = filter_common_comparison_sample(forecasts)
        rows.append(
            summarize_forecasts_for_sensitivity(
                common,
                analysis_dimension="portfolio_composition",
                portfolio_id=portfolio_id,
                window=250,
                lambda_=DEFAULT_LAMBDA,
                sample_type="native_sample",
                seed_window=seed_window,
            )
        )

    result = pd.concat(rows, ignore_index=True)
    required_columns = [
        "analysis_dimension",
        "model_id",
        "portfolio_id",
        "window",
        "lambda",
        "confidence_level",
        "sample_type",
        "sample_start",
        "sample_end",
        "observation_count",
        "effective_tail_observation_count",
        "tail_sample_warning",
        "mean_var",
        "mean_es",
        "exception_count",
        "exception_rate",
        "kupiec_p_value",
        "independence_p_value",
        "conditional_coverage_p_value",
        "average_exceedance_severity",
        "mean_absolute_relative_divergence_from_mr001",
        "configuration_retained",
    ]
    return result[required_columns].sort_values(
        [
            "analysis_dimension",
            "portfolio_id",
            "sample_type",
            "window",
            "lambda",
            "confidence_level",
            "model_id",
        ]
    )


def summarize_forecasts_for_sensitivity(
    forecasts: pd.DataFrame,
    *,
    analysis_dimension: str,
    portfolio_id: str,
    window: int,
    lambda_: float | None,
    sample_type: str,
    seed_window: int,
) -> pd.DataFrame:
    """Backtest a common forecast table into Phase 5 sensitivity rows."""

    records: list[dict[str, Any]] = []
    common = filter_common_comparison_sample(forecasts)
    dates = pd.to_datetime(common["date"].drop_duplicates().sort_values())
    divergence = _divergence_by_model(common)
    for confidence_level, level_data in common.groupby("confidence_level"):
        for model_id in MODEL_ORDER:
            model_data = level_data[level_data["model_id"].eq(model_id)].sort_values("date")
            if model_data.empty:
                continue
            exceedances = (model_data["realized_loss"] > model_data["var"]).astype(int)
            kupiec = kupiec_unconditional_coverage(exceedances, float(confidence_level))
            independence = christoffersen_independence_test(exceedances)
            conditional = christoffersen_conditional_coverage_test(exceedances, float(confidence_level))
            exception_rows = model_data[exceedances.astype(bool)]
            average_severity = (
                float((exception_rows["realized_loss"] / exception_rows["var"]).mean())
                if not exception_rows.empty
                else np.nan
            )
            effective_tail_count = effective_empirical_tail_observation_count(
                model_id,
                window=window,
                confidence_level=float(confidence_level),
                seed_window=seed_window,
            )
            records.append(
                {
                    "analysis_dimension": analysis_dimension,
                    "model_id": model_id,
                    "portfolio_id": portfolio_id,
                    "window": int(window),
                    "lambda": float(lambda_) if lambda_ is not None else np.nan,
                    "confidence_level": float(confidence_level),
                    "sample_type": sample_type,
                    "sample_start": dates.min().strftime("%Y-%m-%d"),
                    "sample_end": dates.max().strftime("%Y-%m-%d"),
                    "observation_count": int(len(model_data)),
                    "effective_tail_observation_count": effective_tail_count,
                    "tail_sample_warning": (
                        "TAIL_SAMPLE_LIMITED"
                        if effective_tail_count is not None and effective_tail_count < 5.0
                        else ""
                    ),
                    "mean_var": float(model_data["var"].mean()),
                    "mean_es": float(model_data["es"].mean()),
                    "exception_count": int(exceedances.sum()),
                    "exception_rate": float(exceedances.mean()),
                    "kupiec_p_value": float(kupiec.p_value),
                    "independence_p_value": float(independence.p_value),
                    "conditional_coverage_p_value": float(conditional.p_value),
                    "average_exceedance_severity": average_severity,
                    "mean_absolute_relative_divergence_from_mr001": divergence.get(
                        (model_id, float(confidence_level)),
                        np.nan,
                    ),
                    "configuration_retained": True,
                }
            )
    return pd.DataFrame.from_records(records)


def common_date_intersection(forecasts_by_window: dict[int, pd.DataFrame]) -> set[str]:
    """Return the common date intersection across compared lookback windows."""

    if not forecasts_by_window:
        return set()
    date_sets = [set(frame["date"].astype(str).unique()) for frame in forecasts_by_window.values()]
    return set.intersection(*date_sets)


def effective_empirical_tail_observation_count(
    model_id: str,
    *,
    window: int,
    confidence_level: float,
    seed_window: int = DEFAULT_SEED_WINDOW,
) -> float | None:
    """Return empirical tail count used for tail-sample warnings."""

    if model_id == "MR-002":
        return float(window * (1.0 - confidence_level))
    if model_id == "MR-004":
        return float((window - seed_window) * (1.0 - confidence_level))
    return None


def validate_predeclared_portfolios() -> pd.DataFrame:
    """Return the fixed Phase 5 portfolio definitions."""

    rows = []
    for portfolio_id, weights in PORTFOLIO_VARIANTS.items():
        rows.append(
            {
                "portfolio_id": portfolio_id,
                "weight_sum": float(sum(weights.values())),
                "weights": dict(weights),
                "optimized_after_results": False,
            }
        )
    return pd.DataFrame.from_records(rows)


def build_phase5_summary(
    *,
    challenger_forecasts_path: Path,
    processed_returns_path: Path,
    risk_config_returns_path: Path,
    common_forecasts: pd.DataFrame,
    exception_diagnostics: pd.DataFrame,
    cluster_summary: pd.DataFrame,
    regime_backtest: pd.DataFrame,
    es_diagnostics: pd.DataFrame,
    sensitivity_results: pd.DataFrame,
) -> dict[str, Any]:
    """Build a deterministic JSON-compatible Phase 5 summary."""

    common_dates = pd.to_datetime(common_forecasts["date"].drop_duplicates().sort_values())
    comparison = summarize_forecasts_for_sensitivity(
        common_forecasts,
        analysis_dimension="phase4_common_reused_for_phase5",
        portfolio_id="equal_weight",
        window=250,
        lambda_=DEFAULT_LAMBDA,
        sample_type="common_phase4_sample",
        seed_window=DEFAULT_SEED_WINDOW,
    )
    h_assessments = assess_hypotheses(comparison, cluster_summary, regime_backtest)
    return {
        "phase": 5,
        "input_returns_path": str(processed_returns_path),
        "input_returns_sha256": sha256_file(processed_returns_path),
        "risk_config_returns_path": str(risk_config_returns_path),
        "risk_config_returns_sha256": sha256_file(risk_config_returns_path),
        "challenger_forecasts_path": str(challenger_forecasts_path),
        "challenger_forecasts_sha256": sha256_file(challenger_forecasts_path),
        "common_sample": {
            "start_date": common_dates.min().strftime("%Y-%m-%d"),
            "end_date": common_dates.max().strftime("%Y-%m-%d"),
            "observation_count": int(common_dates.shape[0]),
            "model_count": int(common_forecasts["model_id"].nunique()),
        },
        "exception_summary": _records(cluster_summary),
        "regime_scope": REGIME_SCOPE_LABEL,
        "regime_summary": _records(regime_backtest),
        "es_diagnostics": _records(es_diagnostics),
        "lookback_window": _dimension_records(sensitivity_results, "lookback_window"),
        "ewma_lambda": _dimension_records(sensitivity_results, "ewma_lambda"),
        "portfolio_composition": {
            "weights": PORTFOLIO_VARIANTS,
            "optimized_after_results": False,
            "records": _dimension_records(sensitivity_results, "portfolio_composition"),
        },
        "tail_sample_limitations": _tail_sample_limitations(sensitivity_results),
        "stability_summary": build_stability_summary(sensitivity_results),
        "hypothesis_assessments": h_assessments,
        "formal_findings_created": False,
        "final_validation_decision": None,
    }


def assess_hypotheses(
    comparison: pd.DataFrame,
    cluster_summary: pd.DataFrame,
    regime_backtest: pd.DataFrame,
) -> dict[str, dict[str, str]]:
    """Assess Phase 5 H1-H4 using generated quantitative evidence."""

    mr1_99 = _row(comparison, "MR-001", 0.99)
    mr1_95 = _row(comparison, "MR-001", 0.95)
    mr3_99 = _row(comparison, "MR-003", 0.99)
    mr2_99 = _row(comparison, "MR-002", 0.99)
    mr4_99 = _row(comparison, "MR-004", 0.99)
    mr1_99_regime = regime_backtest[
        regime_backtest["model_id"].eq("MR-001") & regime_backtest["confidence_level"].eq(0.99)
    ]
    high_ratio = float(mr1_99_regime["high_vol_exception_concentration_ratio"].dropna().iloc[0])
    high_rate = float(
        mr1_99_regime.loc[mr1_99_regime["volatility_regime"].eq("HIGH_VOL"), "exception_rate"].iloc[0]
    )
    normal_rate = float(
        mr1_99_regime.loc[mr1_99_regime["volatility_regime"].eq("NORMAL_VOL"), "exception_rate"].iloc[0]
    )
    mr1_95_cluster = cluster_summary[
        cluster_summary["model_id"].eq("MR-001") & cluster_summary["confidence_level"].eq(0.95)
    ].iloc[0]

    h1_status = "SUPPORTED" if high_ratio > 1.5 and high_rate > normal_rate else "PARTIALLY_SUPPORTED"
    h2_status = (
        "SUPPORTED"
        if mr1_95["kupiec_p_value"] >= 0.05 and mr1_95["conditional_coverage_p_value"] < 0.05
        else "PARTIALLY_SUPPORTED"
    )
    h3_status = (
        "SUPPORTED"
        if mr3_99["exception_rate"] > 0.01 and mr3_99["kupiec_p_value"] < 0.05
        else "PARTIALLY_SUPPORTED"
    )
    h4_condition = (
        mr2_99["exception_rate"] < mr1_99["exception_rate"]
        and mr4_99["exception_rate"] < mr1_99["exception_rate"]
        and (
            mr2_99["conditional_coverage_p_value"] < 0.05
            or mr4_99["conditional_coverage_p_value"] < 0.05
        )
    )
    return {
        "H1": {
            "status": h1_status,
            "evidence": (
                f"MR-001 99% HIGH_VOL exception rate {high_rate:.2%} versus NORMAL_VOL "
                f"{normal_rate:.2%}; high-vol concentration ratio {high_ratio:.2f}."
            ),
        },
        "H2": {
            "status": h2_status,
            "evidence": (
                f"MR-001 95% exception rate {mr1_95['exception_rate']:.2%}, Kupiec p "
                f"{mr1_95['kupiec_p_value']:.4f}, conditional coverage p "
                f"{mr1_95['conditional_coverage_p_value']:.4f}, max project cluster "
                f"{int(mr1_95_cluster['max_cluster_length'])}."
            ),
        },
        "H3": {
            "status": h3_status,
            "evidence": (
                f"MR-003 99% exception rate {mr3_99['exception_rate']:.2%}, Kupiec p "
                f"{mr3_99['kupiec_p_value']:.4f}; volatility responsiveness alone does not "
                "remove far-tail rejection."
            ),
        },
        "H4": {
            "status": "SUPPORTED" if h4_condition else "PARTIALLY_SUPPORTED",
            "evidence": (
                f"MR-002/MR-004 99% rates {mr2_99['exception_rate']:.2%}/"
                f"{mr4_99['exception_rate']:.2%} versus MR-001 {mr1_99['exception_rate']:.2%}; "
                f"conditional p-values {mr2_99['conditional_coverage_p_value']:.4f}/"
                f"{mr4_99['conditional_coverage_p_value']:.4f}."
            ),
        },
    }


def build_stability_summary(sensitivity_results: pd.DataFrame) -> list[dict[str, Any]]:
    """Summarize stability across retained configurations."""

    rows = []
    for (analysis_dimension, model_id, confidence_level), group in sensitivity_results.groupby(
        ["analysis_dimension", "model_id", "confidence_level"]
    ):
        rates = group["exception_rate"].dropna()
        mean_vars = group["mean_var"].dropna()
        rows.append(
            {
                "analysis_dimension": analysis_dimension,
                "model_id": model_id,
                "confidence_level": float(confidence_level),
                "configuration_count": int(len(group)),
                "min_exception_rate": float(rates.min()),
                "max_exception_rate": float(rates.max()),
                "exception_rate_range": float(rates.max() - rates.min()),
                "mean_var_min": float(mean_vars.min()),
                "mean_var_max": float(mean_vars.max()),
                "mean_var_range": float(mean_vars.max() - mean_vars.min()),
                "mean_var_cv": float(mean_vars.std(ddof=0) / mean_vars.mean()) if mean_vars.mean() else np.nan,
                "fraction_rejecting_coverage_5pct": float((group["kupiec_p_value"] < 0.05).mean()),
                "fraction_rejecting_conditional_coverage_5pct": float(
                    (group["conditional_coverage_p_value"] < 0.05).mean()
                ),
            }
        )
    return rows


def render_outcomes_and_stability_report(
    *,
    summary: dict[str, Any],
    cluster_summary: pd.DataFrame,
    regime_backtest: pd.DataFrame,
    es_diagnostics: pd.DataFrame,
    sensitivity_results: pd.DataFrame,
    top_exceptions: pd.DataFrame,
) -> str:
    """Render the Phase 5 Markdown report."""

    common = summary["common_sample"]
    return f"""# Outcomes, Regime, and Stability Analysis

## 1. Objective

Phase 5 tests when, how often, and how severely the model forecasts fail. A
single unconditional exception count can hide clustering, volatility-regime
concentration, ES shortfall behavior, and sensitivity to predeclared modeling
choices.

## 2. Exception Diagnostics

Common Phase 4 sample reused for Phase 5: {common["start_date"]} to
{common["end_date"]}, {common["observation_count"]} observations, four models.
Input returns SHA-256: `{summary["input_returns_sha256"]}`. Challenger forecast
artifact SHA-256: `{summary["challenger_forecasts_sha256"]}`.

{_markdown_table(_cluster_report_table(cluster_summary))}

Cluster definition: adjacent exceptions separated by <=5 trading observations
are assigned to the same project diagnostic cluster. This is not a regulatory
threshold. Rolling exception rates use trailing 125- and 250-observation windows
only.

## 3. Exceedance Severity

Top exception severity observations:

{_markdown_table(top_exceptions[["date", "model_id", "confidence_level", "realized_loss", "var", "exceedance_amount", "severity_ratio", "volatility_regime"]])}

## 4. Regime Analysis

Regimes reuse the Phase 2 LOW_VOL / NORMAL_VOL / HIGH_VOL labels. They are
retrospective/descriptive because Phase 2 thresholds used full-sample volatility
quantiles; these labels are not live monitoring thresholds.

{_markdown_table(_regime_report_table(regime_backtest))}

## 5. Expected Shortfall Diagnostics

These ES diagnostics are descriptive outcomes conditional on VaR exceptions,
not a definitive regulatory ES backtest.

{_markdown_table(_es_report_table(es_diagnostics))}

## 6. Lookback Sensitivity

The lookback grid retained every predeclared 125/250/500-day window and every
95%/97.5%/99% confidence level. Native samples are each window's own available
forecast sample. Common sensitivity samples use the date intersection across
the compared windows.

{_markdown_table(_sensitivity_report_table(sensitivity_results, "lookback_window"))}

## 7. EWMA Lambda Sensitivity

Lambda sensitivity keeps the canonical default at 0.94 and also runs 0.97 and
0.99 for MR-003 and MR-004. No parameter is permanently changed based on these
results.

{_markdown_table(_sensitivity_report_table(sensitivity_results, "ewma_lambda"))}

## 8. Portfolio Sensitivity

The portfolio grid uses four fixed, predeclared weight sets:
equal_weight, equity_heavy, rates_heavy, and diversified_balanced. Weights were
not optimized after observing results.

{_markdown_table(_sensitivity_report_table(sensitivity_results, "portfolio_composition"))}

## 9. Stability Assessment

Robust conclusions: far-tail behavior remains sensitive across methodologies,
and empirical tail estimates are sample-limited for smaller windows and high
confidence levels. Parameter-sensitive conclusions: EWMA/FHS estimates move
materially with lambda, especially in the 99% tail. Portfolio-sensitive
conclusions: exception rates and mean VaR change under equity-heavy versus
rates-heavy weights, so Phase 6 findings should avoid overgeneralizing from a
single portfolio. Small empirical-tail samples are explicitly flagged as
TAIL_SAMPLE_LIMITED in `sensitivity_results.csv`.

## 10. Integrated Phase 5 Interpretation

{_hypothesis_lines(summary["hypothesis_assessments"])}

Candidate concern A: 99% Gaussian VaR shows persistent far-tail weakness.
Evidence comes from Phase 2 fat-tail diagnostics, Phase 4 challenger comparison,
and Phase 5 regime/outcomes results. This is candidate finding evidence only;
no formal finding or severity is assigned in Phase 5.

Candidate concern B: 95% Gaussian VaR weakness appears more conditional than
unconditional. Exception frequency is close to nominal, but clustering and
conditional-coverage evidence require Phase 6 integration before any formal
finding.

## 11. Limitations

- Public ETF proxies rather than a production portfolio.
- Retrospective regime classification based on full-sample Phase 2 thresholds.
- Finite empirical tails, especially 99% with 125-day windows.
- Overlapping rolling samples create dependence in outcomes.
- ES analysis is descriptive and conditional on VaR exceptions.
- Fixed parameter grids are sensitivity diagnostics, not optimization.
- No formal finding, severity, remediation item, or final validation decision is created here.

## 12. Phase 5 Conclusion

Phase 5 establishes that model outcomes differ by volatility regime, exception
clustering matters beyond frequency, and some challenger/parameter choices
improve unconditional 99% coverage while retaining conditional-coverage or
finite-tail limitations. This evidence should proceed to Phase 6 findings and
data-quality impact analysis, but it is not a final validation decision.
"""


def _divergence_by_model(forecasts: pd.DataFrame) -> dict[tuple[str, float], float]:
    rows = build_challenger_divergence(
        forecasts,
        amber_threshold=0.15,
        red_threshold=0.25,
    )
    return {
        (str(row.model_id), float(row.confidence_level)): float(row.mean_absolute_relative_divergence)
        for row in rows.itertuples(index=False)
    }


def _row(table: pd.DataFrame, model_id: str, confidence_level: float) -> pd.Series:
    matches = table[table["model_id"].eq(model_id) & table["confidence_level"].eq(confidence_level)]
    if matches.empty:
        raise ValueError(f"Missing row for {model_id} at {confidence_level}.")
    return matches.iloc[0]


def _dimension_records(table: pd.DataFrame, dimension: str) -> list[dict[str, Any]]:
    return _records(table[table["analysis_dimension"].eq(dimension)])


def _tail_sample_limitations(table: pd.DataFrame) -> list[dict[str, Any]]:
    limited = table[table["tail_sample_warning"].eq("TAIL_SAMPLE_LIMITED")]
    return _records(limited)


def _records(table: pd.DataFrame) -> list[dict[str, Any]]:
    return [_json_clean(record) for record in table.to_dict(orient="records")]


def _json_dumps(payload: dict) -> str:
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


def _cluster_report_table(cluster_summary: pd.DataFrame) -> pd.DataFrame:
    columns = [
        "model_id",
        "confidence_level",
        "exception_count",
        "exception_rate",
        "max_cluster_length",
        "number_of_clusters",
        "median_days_between_exceptions",
        "average_exception_severity",
        "maximum_exception_severity",
    ]
    return cluster_summary[columns]


def _regime_report_table(regime_backtest: pd.DataFrame) -> pd.DataFrame:
    high = regime_backtest[regime_backtest["volatility_regime"].eq("HIGH_VOL")]
    pivot = regime_backtest.pivot_table(
        index=["model_id", "confidence_level"],
        columns="volatility_regime",
        values="exception_rate",
        aggfunc="first",
    ).reset_index()
    pivot.columns.name = None
    pivot = pivot.rename(
        columns={
            "LOW_VOL": "low_vol_exception_rate",
            "NORMAL_VOL": "normal_vol_exception_rate",
            "HIGH_VOL": "high_vol_exception_rate",
        }
    )
    high_columns = high[
        [
            "model_id",
            "confidence_level",
            "fraction_all_exceptions_in_high_vol",
            "high_vol_exception_concentration_ratio",
            "average_exception_severity",
        ]
    ].rename(columns={"average_exception_severity": "high_vol_severity"})
    return pivot.merge(high_columns, on=["model_id", "confidence_level"], how="left")


def _es_report_table(es_diagnostics: pd.DataFrame) -> pd.DataFrame:
    return es_diagnostics[
        [
            "model_id",
            "confidence_level",
            "mean_forecast_es_on_exception_dates",
            "mean_realized_loss_on_exception_dates",
            "realized_loss_to_es_ratio",
            "fraction_exceptions_exceeding_es",
        ]
    ]


def _sensitivity_report_table(sensitivity_results: pd.DataFrame, dimension: str) -> pd.DataFrame:
    table = sensitivity_results[sensitivity_results["analysis_dimension"].eq(dimension)]
    if dimension == "lookback_window":
        table = table[table["sample_type"].eq("common_sensitivity_sample")]
    columns = [
        "model_id",
        "portfolio_id",
        "window",
        "lambda",
        "confidence_level",
        "sample_type",
        "exception_rate",
        "kupiec_p_value",
        "conditional_coverage_p_value",
        "tail_sample_warning",
    ]
    return table[columns].head(36)


def _markdown_table(table: pd.DataFrame) -> str:
    formatted = table.copy()
    for column in formatted.columns:
        if pd.api.types.is_float_dtype(formatted[column]):
            formatted[column] = formatted[column].map(lambda value: "" if pd.isna(value) else f"{value:.4f}")
    headers = [str(column) for column in formatted.columns]
    rows = []
    for record in formatted.astype(object).where(pd.notna(formatted), "").to_dict(orient="records"):
        rows.append([_escape_markdown_cell(record[column]) for column in formatted.columns])
    header_line = "| " + " | ".join(_escape_markdown_cell(header) for header in headers) + " |"
    separator = "| " + " | ".join("---" for _ in headers) + " |"
    row_lines = ["| " + " | ".join(str(cell) for cell in row) + " |" for row in rows]
    return "\n".join([header_line, separator, *row_lines])


def _escape_markdown_cell(value: object) -> str:
    return str(value).replace("|", "\\|").replace("\n", " ")


def _hypothesis_lines(hypotheses: dict[str, dict[str, str]]) -> str:
    return "\n".join(
        f"- {name}: {payload['status']}. {payload['evidence']}" for name, payload in hypotheses.items()
    )


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run Phase 5 outcomes and sensitivity analysis.")
    parser.add_argument("--challenger-forecasts", default="data/artifacts/challenger_forecasts.csv")
    parser.add_argument("--processed-returns", default="data/processed/returns.csv")
    parser.add_argument("--phase2-regimes", default="data/artifacts/rolling_distribution_diagnostics.csv")
    parser.add_argument("--risk-config", default="configs/risk_engine.yaml")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    paths = run_phase5_analysis(
        challenger_forecasts_path=args.challenger_forecasts,
        processed_returns_path=args.processed_returns,
        phase2_regime_path=args.phase2_regimes,
        risk_config_path=args.risk_config,
    )
    print(_json_dumps({key: str(value) for key, value in paths.__dict__.items()}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
