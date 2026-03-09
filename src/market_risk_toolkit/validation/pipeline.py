"""Pipeline for VaR backtesting and model validation artifacts."""

from __future__ import annotations

import argparse
import json
from dataclasses import dataclass
from pathlib import Path

import pandas as pd

from market_risk_toolkit.validation.backtesting import (
    build_exceedance_table,
    summarize_backtests,
)
from market_risk_toolkit.validation.config import ValidationConfig, load_validation_config
from market_risk_toolkit.validation.io import load_risk_table
from market_risk_toolkit.validation.plotting import save_exceedance_plot


@dataclass(frozen=True)
class ValidationArtifactPaths:
    """Paths written during a validation run."""

    exceedance_table_path: Path
    summary_path: Path
    interpretation_path: Path
    exceedance_plot_path: Path


@dataclass(frozen=True)
class ValidationPipelineResult:
    """In-memory and on-disk outputs of the validation pipeline."""

    config: ValidationConfig
    exceedance_table: pd.DataFrame
    summary: pd.DataFrame
    artifacts: ValidationArtifactPaths


def run_validation_pipeline(config: ValidationConfig) -> ValidationPipelineResult:
    """Load rolling risk outputs and produce backtesting artifacts."""

    normalized_config = config.normalized()
    risk_table = load_risk_table(normalized_config.risk_table_path)
    exceedance_table = build_exceedance_table(
        risk_table=risk_table,
        confidence_levels=normalized_config.confidence_levels,
    )
    summary = summarize_backtests(
        exceedance_table=exceedance_table,
        confidence_levels=normalized_config.confidence_levels,
    )
    artifacts = _write_artifacts(
        exceedance_table=exceedance_table,
        summary=summary,
        config=normalized_config,
    )
    return ValidationPipelineResult(
        config=normalized_config,
        exceedance_table=exceedance_table,
        summary=summary,
        artifacts=artifacts,
    )


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run VaR backtesting and validation.")
    parser.add_argument(
        "--config",
        default="configs/validation_engine.yaml",
        help="Path to the validation YAML config.",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    config = load_validation_config(args.config)
    result = run_validation_pipeline(config)
    print(
        json.dumps(
            {
                "portfolio_name": result.config.portfolio_name,
                "summary_path": str(result.artifacts.summary_path),
                "exceedance_table_path": str(result.artifacts.exceedance_table_path),
                "interpretation_path": str(result.artifacts.interpretation_path),
                "exceedance_plot_path": str(result.artifacts.exceedance_plot_path),
                "summary": result.summary.to_dict(orient="records"),
            },
            indent=2,
            default=_json_default,
        )
    )
    return 0


def _write_artifacts(
    exceedance_table: pd.DataFrame,
    summary: pd.DataFrame,
    config: ValidationConfig,
) -> ValidationArtifactPaths:
    config.output_dir.mkdir(parents=True, exist_ok=True)
    config.figure_dir.mkdir(parents=True, exist_ok=True)

    exceedance_table_path = config.output_dir / f"{config.portfolio_name}_backtest_exceedances.csv"
    summary_path = config.output_dir / f"{config.portfolio_name}_backtest_summary.csv"
    interpretation_path = config.output_dir / f"{config.portfolio_name}_validation_interpretation.md"
    exceedance_plot_path = config.figure_dir / f"{config.portfolio_name}_exceedance_plot.png"

    exceedance_table.reset_index().to_csv(exceedance_table_path, index=False)
    summary.to_csv(summary_path, index=False)
    interpretation_path.write_text(_build_interpretation_markdown(config.portfolio_name, summary), encoding="utf-8")
    save_exceedance_plot(
        exceedance_table=exceedance_table,
        portfolio_name=config.portfolio_name,
        confidence_level=max(config.confidence_levels),
        destination=exceedance_plot_path,
    )
    return ValidationArtifactPaths(
        exceedance_table_path=exceedance_table_path,
        summary_path=summary_path,
        interpretation_path=interpretation_path,
        exceedance_plot_path=exceedance_plot_path,
    )


def _build_interpretation_markdown(portfolio_name: str, summary: pd.DataFrame) -> str:
    lines = [
        f"# {portfolio_name} VaR Backtesting Interpretation",
        "",
        "This memo-style summary compares realized losses to historical and parametric VaR forecasts.",
        "",
    ]
    for row in summary.itertuples(index=False):
        suffix = int(round(row.confidence_level * 100))
        lines.append(f"## {row.model.capitalize()} VaR {suffix}%")
        lines.append(
            f"- Exceptions: {row.exception_count} out of {row.observation_count} observations "
            f"({row.exception_rate:.2%} vs expected {row.expected_exception_rate:.2%})"
        )
        lines.append(
            f"- Kupiec p-value: {row.kupiec_p_value:.4f}; "
            f"Christoffersen conditional coverage p-value: {row.christoffersen_cc_p_value:.4f}"
        )
        lines.append(f"- Interpretation: {row.interpretation}")
        lines.append("")
    return "\n".join(lines).strip() + "\n"


def _json_default(value: object) -> object:
    if isinstance(value, pd.Timestamp):
        return value.isoformat()
    return value


if __name__ == "__main__":
    raise SystemExit(main())
