"""Pipeline for generating rolling VaR/ES artifacts."""

from __future__ import annotations

import argparse
import json
from dataclasses import dataclass
from pathlib import Path

import pandas as pd

from market_risk_toolkit.risk.config import RiskConfig, load_risk_config
from market_risk_toolkit.risk.io import load_portfolio_returns
from market_risk_toolkit.risk.metrics import compute_rolling_risk_metrics
from market_risk_toolkit.risk.plotting import save_risk_comparison_plot


@dataclass(frozen=True)
class RiskArtifactPaths:
    """Paths written during a rolling risk run."""

    risk_table_path: Path
    summary_path: Path
    comparison_plot_path: Path


@dataclass(frozen=True)
class RiskPipelineResult:
    """In-memory and on-disk results of the risk pipeline."""

    config: RiskConfig
    returns: pd.Series
    risk_table: pd.DataFrame
    summary: pd.DataFrame
    artifacts: RiskArtifactPaths


def run_risk_pipeline(config: RiskConfig) -> RiskPipelineResult:
    """Build rolling VaR/ES metrics and write artifacts."""

    normalized_config = config.normalized()
    returns = load_portfolio_returns(normalized_config.returns_path)
    risk_table = compute_rolling_risk_metrics(
        returns=returns,
        window=normalized_config.window,
        confidence_levels=normalized_config.confidence_levels,
    )
    summary = summarize_risk_metrics(
        risk_table=risk_table,
        portfolio_name=normalized_config.portfolio_name,
        window=normalized_config.window,
        confidence_levels=normalized_config.confidence_levels,
    )
    artifacts = _write_artifacts(
        risk_table=risk_table,
        summary=summary,
        config=normalized_config,
    )
    return RiskPipelineResult(
        config=normalized_config,
        returns=returns,
        risk_table=risk_table,
        summary=summary,
        artifacts=artifacts,
    )


def summarize_risk_metrics(
    risk_table: pd.DataFrame,
    portfolio_name: str,
    window: int,
    confidence_levels: tuple[float, ...],
) -> pd.DataFrame:
    """Summarize average and latest risk metrics across confidence levels."""

    records: list[dict[str, float | str | int]] = []
    latest_row = risk_table.iloc[-1]
    for level in confidence_levels:
        suffix = str(int(round(level * 100)))
        records.append(
            {
                "portfolio_name": portfolio_name,
                "window": window,
                "confidence_level": level,
                "mean_historical_var": float(risk_table[f"historical_var_{suffix}"].mean()),
                "mean_parametric_var": float(risk_table[f"parametric_var_{suffix}"].mean()),
                "mean_historical_es": float(risk_table[f"historical_es_{suffix}"].mean()),
                "mean_parametric_es": float(risk_table[f"parametric_es_{suffix}"].mean()),
                "latest_historical_var": float(latest_row[f"historical_var_{suffix}"]),
                "latest_parametric_var": float(latest_row[f"parametric_var_{suffix}"]),
                "latest_historical_es": float(latest_row[f"historical_es_{suffix}"]),
                "latest_parametric_es": float(latest_row[f"parametric_es_{suffix}"]),
            }
        )
    return pd.DataFrame.from_records(records)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Generate rolling VaR and ES metrics.")
    parser.add_argument(
        "--config",
        default="configs/risk_engine.yaml",
        help="Path to the rolling risk YAML config.",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    config = load_risk_config(args.config)
    result = run_risk_pipeline(config)
    print(
        json.dumps(
            {
                "portfolio_name": result.config.portfolio_name,
                "risk_table_path": str(result.artifacts.risk_table_path),
                "summary_path": str(result.artifacts.summary_path),
                "comparison_plot_path": str(result.artifacts.comparison_plot_path),
                "summary": result.summary.to_dict(orient="records"),
            },
            indent=2,
            default=_json_default,
        )
    )
    return 0


def _write_artifacts(
    risk_table: pd.DataFrame,
    summary: pd.DataFrame,
    config: RiskConfig,
) -> RiskArtifactPaths:
    config.output_dir.mkdir(parents=True, exist_ok=True)
    config.figure_dir.mkdir(parents=True, exist_ok=True)

    risk_table_path = config.output_dir / f"{config.portfolio_name}_rolling_var_es.csv"
    summary_path = config.output_dir / f"{config.portfolio_name}_risk_summary.csv"
    comparison_plot_path = config.figure_dir / f"{config.portfolio_name}_var_es_comparison.png"

    risk_table.reset_index().to_csv(risk_table_path, index=False)
    summary.to_csv(summary_path, index=False)
    save_risk_comparison_plot(
        risk_table=risk_table,
        portfolio_name=config.portfolio_name,
        confidence_level=max(config.confidence_levels),
        destination=comparison_plot_path,
    )
    return RiskArtifactPaths(
        risk_table_path=risk_table_path,
        summary_path=summary_path,
        comparison_plot_path=comparison_plot_path,
    )


def _json_default(value: object) -> object:
    if isinstance(value, pd.Timestamp):
        return value.isoformat()
    return value


if __name__ == "__main__":
    raise SystemExit(main())
