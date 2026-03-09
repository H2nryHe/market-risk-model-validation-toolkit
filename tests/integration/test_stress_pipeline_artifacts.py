import pandas as pd

from market_risk_toolkit.stress.config import StressConfig
from market_risk_toolkit.stress.pipeline import run_stress_pipeline


def test_run_stress_pipeline_writes_tables_markdown_and_plot(tmp_path) -> None:
    portfolio_config_path = tmp_path / "portfolio.yaml"
    portfolio_config_path.write_text(
        "\n".join(
            [
                "name: integration_stress_portfolio",
                "description: Integration stress test portfolio",
                "strategy: custom_weight",
                "tickers:",
                "  - SPY",
                "  - QQQ",
                "  - TLT",
                "weights:",
                "  SPY: 0.4",
                "  QQQ: 0.35",
                "  TLT: 0.25",
            ]
        )
        + "\n",
        encoding="utf-8",
    )
    scenarios_path = tmp_path / "scenarios.yaml"
    scenarios_path.write_text(
        "\n".join(
            [
                "scenarios:",
                "  - name: equity_selloff",
                "    description: Equity drawdown",
                "    shocks:",
                "      SPY: -0.08",
                "      QQQ: -0.10",
                "      TLT: 0.02",
                "  - name: rates_shock",
                "    description: Duration shock",
                "    shocks:",
                "      TLT: -0.05",
            ]
        )
        + "\n",
        encoding="utf-8",
    )

    config = StressConfig(
        portfolio_name="integration_stress",
        portfolio_config_path=portfolio_config_path,
        scenarios_path=scenarios_path,
        output_dir=tmp_path / "artifacts",
        figure_dir=tmp_path / "figures",
        notional=1.0,
    )
    result = run_stress_pipeline(config)

    assert result.artifacts.scenario_summary_path.exists()
    assert result.artifacts.contribution_table_path.exists()
    assert result.artifacts.weights_path.exists()
    assert result.artifacts.markdown_summary_path.exists()
    assert result.artifacts.figure_path.exists()

    summary = pd.read_csv(result.artifacts.scenario_summary_path)
    contributions = pd.read_csv(result.artifacts.contribution_table_path)

    assert len(summary) == 2
    assert set(summary["scenario_name"]) == {"equity_selloff", "rates_shock"}
    assert "contribution" in contributions.columns
