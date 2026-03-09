from pathlib import Path

import pandas as pd

from market_risk_toolkit.portfolio.config import PortfolioConfig
from market_risk_toolkit.portfolio.pipeline import run_portfolio_pipeline


def test_run_portfolio_pipeline_writes_summary_timeseries_weights_and_figure(tmp_path) -> None:
    returns = pd.DataFrame(
        {
            "date": pd.to_datetime(["2024-01-02", "2024-01-03", "2024-01-04"]),
            "SPY": [0.01, -0.01, 0.02],
            "QQQ": [0.00, 0.01, 0.03],
            "TLT": [0.00, 0.00, 0.01],
            "GLD": [0.01, 0.00, 0.00],
        }
    )
    returns_path = tmp_path / "returns.csv"
    returns.to_csv(returns_path, index=False)

    config = PortfolioConfig(
        name="integration_portfolio",
        description="Integration test portfolio",
        strategy="equal_weight",
        tickers=("SPY", "QQQ", "TLT", "GLD"),
        returns_path=returns_path,
        output_dir=tmp_path / "artifacts",
        figure_dir=tmp_path / "figures",
    )

    result = run_portfolio_pipeline(config)

    assert result.artifacts.summary_path.exists()
    assert result.artifacts.timeseries_path.exists()
    assert result.artifacts.weights_path.exists()
    assert result.artifacts.figure_path.exists()
    assert result.artifacts.figure_path.suffix == ".png"

    summary = pd.read_csv(result.artifacts.summary_path)
    timeseries = pd.read_csv(result.artifacts.timeseries_path)
    weights = pd.read_csv(result.artifacts.weights_path)

    assert summary.loc[0, "portfolio_name"] == "integration_portfolio"
    assert list(timeseries.columns) == ["date", "portfolio_return", "cumulative_return", "nav"]
    assert set(weights["ticker"]) == {"SPY", "QQQ", "TLT", "GLD"}
    assert Path(result.artifacts.figure_path).stat().st_size > 0
