"""Model validation components."""

from market_risk_toolkit.validation.backtesting import (
    LikelihoodRatioTestResult,
    build_exceedance_table,
    christoffersen_conditional_coverage_test,
    christoffersen_independence_test,
    interpret_backtest_result,
    kupiec_unconditional_coverage,
    summarize_backtests,
)
from market_risk_toolkit.validation.config import ValidationConfig, load_validation_config
from market_risk_toolkit.validation.io import load_risk_table
from market_risk_toolkit.validation.pipeline import (
    ValidationArtifactPaths,
    ValidationPipelineResult,
    run_validation_pipeline,
)

__all__ = [
    "LikelihoodRatioTestResult",
    "ValidationArtifactPaths",
    "ValidationConfig",
    "ValidationPipelineResult",
    "build_exceedance_table",
    "christoffersen_conditional_coverage_test",
    "christoffersen_independence_test",
    "interpret_backtest_result",
    "kupiec_unconditional_coverage",
    "load_risk_table",
    "load_validation_config",
    "run_validation_pipeline",
    "summarize_backtests",
]
