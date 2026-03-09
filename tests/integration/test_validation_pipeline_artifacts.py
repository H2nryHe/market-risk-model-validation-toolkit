import pandas as pd

from market_risk_toolkit.validation.config import ValidationConfig
from market_risk_toolkit.validation.pipeline import run_validation_pipeline


def test_run_validation_pipeline_writes_summary_plot_and_interpretation(tmp_path) -> None:
    risk_table = pd.DataFrame(
        {
            "date": pd.date_range("2024-01-01", periods=40, freq="D"),
            "portfolio_return": [(-0.03 if idx in {10, 11, 25} else 0.002 * ((idx % 5) - 2)) for idx in range(40)],
            "historical_var_95": [0.015] * 40,
            "parametric_var_95": [0.013] * 40,
            "historical_es_95": [0.020] * 40,
            "parametric_es_95": [0.018] * 40,
            "historical_var_99": [0.025] * 40,
            "parametric_var_99": [0.022] * 40,
            "historical_es_99": [0.030] * 40,
            "parametric_es_99": [0.027] * 40,
        }
    )
    risk_table_path = tmp_path / "risk_table.csv"
    risk_table.to_csv(risk_table_path, index=False)

    config = ValidationConfig(
        portfolio_name="integration_validation",
        risk_table_path=risk_table_path,
        output_dir=tmp_path / "artifacts",
        figure_dir=tmp_path / "figures",
        confidence_levels=(0.95, 0.99),
    )
    result = run_validation_pipeline(config)

    assert result.artifacts.exceedance_table_path.exists()
    assert result.artifacts.summary_path.exists()
    assert result.artifacts.interpretation_path.exists()
    assert result.artifacts.exceedance_plot_path.exists()

    summary = pd.read_csv(result.artifacts.summary_path)
    exceedances = pd.read_csv(result.artifacts.exceedance_table_path)

    assert len(summary) == 4
    assert "historical_exceedance_95" in exceedances.columns
    assert "christoffersen_cc_p_value" in summary.columns
