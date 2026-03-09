"""Data ingestion and validation components."""

from market_risk_toolkit.data.config import DataPipelineConfig, load_config
from market_risk_toolkit.data.download import download_adjusted_close
from market_risk_toolkit.data.pipeline import DataPipelineResult, run_data_pipeline
from market_risk_toolkit.data.validation import ValidationArtifacts, build_aligned_returns

__all__ = [
    "DataPipelineConfig",
    "DataPipelineResult",
    "ValidationArtifacts",
    "build_aligned_returns",
    "download_adjusted_close",
    "load_config",
    "run_data_pipeline",
]
