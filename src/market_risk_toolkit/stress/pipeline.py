"""Pipeline for deterministic stress testing artifacts."""

from __future__ import annotations

import argparse
import json
from dataclasses import dataclass
from pathlib import Path

import pandas as pd

from market_risk_toolkit.portfolio.config import load_portfolio_config
from market_risk_toolkit.stress.config import StressConfig, load_stress_config
from market_risk_toolkit.stress.engine import StressTestResult, build_stress_test
from market_risk_toolkit.stress.io import load_scenarios, weights_to_frame
from market_risk_toolkit.stress.plotting import save_stress_bar_chart


@dataclass(frozen=True)
class StressArtifactPaths:
    """Paths written during a stress run."""

    scenario_summary_path: Path
    contribution_table_path: Path
    weights_path: Path
    markdown_summary_path: Path
    figure_path: Path


@dataclass(frozen=True)
class StressPipelineResult:
    """In-memory and on-disk outputs from stress testing."""

    config: StressConfig
    result: StressTestResult
    artifacts: StressArtifactPaths


def run_stress_pipeline(config: StressConfig) -> StressPipelineResult:
    """Run deterministic stress scenarios and write report-friendly artifacts."""

    normalized_config = config.normalized()
    portfolio_config = load_portfolio_config(normalized_config.portfolio_config_path)
    scenarios = load_scenarios(normalized_config.scenarios_path)
    result = build_stress_test(
        portfolio_config=portfolio_config,
        scenarios=scenarios,
        notional=normalized_config.notional,
    )
    artifacts = _write_artifacts(
        result=result,
        config=normalized_config,
    )
    return StressPipelineResult(config=normalized_config, result=result, artifacts=artifacts)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run deterministic portfolio stress testing.")
    parser.add_argument(
        "--config",
        default="configs/stress_engine.yaml",
        help="Path to the stress-engine YAML config.",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    config = load_stress_config(args.config)
    result = run_stress_pipeline(config)
    print(
        json.dumps(
            {
                "portfolio_name": result.config.portfolio_name,
                "scenario_summary_path": str(result.artifacts.scenario_summary_path),
                "contribution_table_path": str(result.artifacts.contribution_table_path),
                "markdown_summary_path": str(result.artifacts.markdown_summary_path),
                "figure_path": str(result.artifacts.figure_path),
                "scenario_summary": result.result.scenario_summary.to_dict(orient="records"),
            },
            indent=2,
            default=_json_default,
        )
    )
    return 0


def _write_artifacts(result: StressTestResult, config: StressConfig) -> StressArtifactPaths:
    config.output_dir.mkdir(parents=True, exist_ok=True)
    config.figure_dir.mkdir(parents=True, exist_ok=True)

    scenario_summary_path = config.output_dir / f"{config.portfolio_name}_stress_summary.csv"
    contribution_table_path = config.output_dir / f"{config.portfolio_name}_stress_contributions.csv"
    weights_path = config.output_dir / f"{config.portfolio_name}_stress_weights.csv"
    markdown_summary_path = config.output_dir / f"{config.portfolio_name}_stress_summary.md"
    figure_path = config.figure_dir / f"{config.portfolio_name}_stress_scenarios.png"

    result.scenario_summary.to_csv(scenario_summary_path, index=False)
    result.contribution_table.to_csv(contribution_table_path, index=False)
    weights_to_frame(result.weights).to_csv(weights_path, index=False)
    markdown_summary_path.write_text(
        _build_markdown_summary(config.portfolio_name, result.scenario_summary, result.contribution_table),
        encoding="utf-8",
    )
    save_stress_bar_chart(result.scenario_summary, config.portfolio_name, figure_path)

    return StressArtifactPaths(
        scenario_summary_path=scenario_summary_path,
        contribution_table_path=contribution_table_path,
        weights_path=weights_path,
        markdown_summary_path=markdown_summary_path,
        figure_path=figure_path,
    )


def _build_markdown_summary(
    portfolio_name: str,
    scenario_summary: pd.DataFrame,
    contribution_table: pd.DataFrame,
) -> str:
    lines = [
        f"# {portfolio_name} Stress Testing Summary",
        "",
        "Deterministic portfolio PnL is computed as the sum of asset weight times scenario shock.",
        "",
    ]
    for row in scenario_summary.itertuples(index=False):
        scenario_contributions = contribution_table[
            contribution_table["scenario_name"] == row.scenario_name
        ].sort_values("contribution")
        worst = scenario_contributions.head(2)
        lines.append(f"## {row.scenario_name}")
        lines.append(f"- Description: {row.scenario_description}")
        lines.append(f"- Portfolio PnL: {row.portfolio_pnl:.4f}")
        lines.append(f"- Portfolio loss: {row.portfolio_loss:.4f}")
        if not worst.empty:
            contributor_text = ", ".join(
                f"{item.ticker} ({item.contribution:.4f})" for item in worst.itertuples(index=False)
            )
            lines.append(f"- Largest negative contributors: {contributor_text}")
        lines.append("")
    return "\n".join(lines).strip() + "\n"


def _json_default(value: object) -> object:
    if isinstance(value, pd.Timestamp):
        return value.isoformat()
    return value


if __name__ == "__main__":
    raise SystemExit(main())
