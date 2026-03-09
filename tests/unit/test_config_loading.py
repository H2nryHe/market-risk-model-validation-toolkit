from pathlib import Path

from market_risk_toolkit.data.config import load_config as load_data_config
from market_risk_toolkit.portfolio.config import load_portfolio_config
from market_risk_toolkit.risk.config import load_risk_config
from market_risk_toolkit.stress.config import load_stress_config
from market_risk_toolkit.validation.config import load_validation_config


def test_stage_configs_load_expected_defaults() -> None:
    root = Path(__file__).resolve().parents[2]

    data_config = load_data_config(root / "configs/data_pipeline.yaml")
    portfolio_config = load_portfolio_config(root / "configs/portfolios/example_portfolio.yaml")
    risk_config = load_risk_config(root / "configs/risk_engine.yaml")
    stress_config = load_stress_config(root / "configs/stress_engine.yaml")
    validation_config = load_validation_config(root / "configs/validation_engine.yaml")

    assert data_config.tickers == ("SPY", "QQQ", "TLT", "GLD")
    assert portfolio_config.strategy == "equal_weight"
    assert risk_config.window == 250
    assert stress_config.portfolio_name == "baseline_multi_asset_custom"
    assert validation_config.portfolio_name == "baseline_multi_asset_equal_weight"
