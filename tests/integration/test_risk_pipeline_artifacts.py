import pandas as pd

from market_risk_toolkit.risk.config import RiskConfig
from market_risk_toolkit.risk.pipeline import run_risk_pipeline


def test_run_risk_pipeline_writes_table_summary_and_plot(tmp_path) -> None:
    returns = pd.DataFrame(
        {
            "date": pd.date_range("2024-01-01", periods=260, freq="D"),
            "portfolio_return": [0.001 * ((index % 7) - 3) for index in range(260)],
            "cumulative_return": 0.0,
            "nav": 1.0,
        }
    )
    returns_path = tmp_path / "portfolio_timeseries.csv"
    returns.to_csv(returns_path, index=False)

    config = RiskConfig(
        portfolio_name="integration_risk",
        returns_path=returns_path,
        output_dir=tmp_path / "artifacts",
        figure_dir=tmp_path / "figures",
        window=20,
        confidence_levels=(0.95, 0.99),
    )
    result = run_risk_pipeline(config)

    assert result.artifacts.risk_table_path.exists()
    assert result.artifacts.summary_path.exists()
    assert result.artifacts.comparison_plot_path.exists()

    risk_table = pd.read_csv(result.artifacts.risk_table_path)
    summary = pd.read_csv(result.artifacts.summary_path)

    assert "historical_var_95" in risk_table.columns
    assert "parametric_es_99" in risk_table.columns
    assert set(summary["confidence_level"]) == {0.95, 0.99}
