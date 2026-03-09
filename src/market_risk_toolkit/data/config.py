"""Configuration helpers for the market data ingestion pipeline."""

from __future__ import annotations

from dataclasses import dataclass, replace
from pathlib import Path
from typing import Any

import yaml

DEFAULT_TICKERS = ("SPY", "QQQ", "TLT", "GLD")


@dataclass(frozen=True)
class DataPipelineConfig:
    """Configuration for downloading, validating, and storing market data."""

    tickers: tuple[str, ...] = DEFAULT_TICKERS
    start_date: str = "2018-01-01"
    end_date: str | None = None
    spike_threshold: float = 0.15
    source: str = "yfinance"
    raw_dir: Path = Path("data/raw")
    processed_dir: Path = Path("data/processed")
    artifact_dir: Path = Path("data/artifacts")
    raw_prices_filename: str = "adjusted_close_raw.csv"
    raw_metadata_filename: str = "download_metadata.json"
    cleaned_prices_filename: str = "adjusted_close.csv"
    returns_filename: str = "returns.csv"
    validation_summary_filename: str = "data_validation_summary.json"
    validation_flags_filename: str = "data_validation_flags.csv"

    def normalized(self) -> "DataPipelineConfig":
        """Return a copy with canonicalized tickers and paths."""

        normalized_tickers = tuple(dict.fromkeys(ticker.upper() for ticker in self.tickers))
        return replace(
            self,
            tickers=normalized_tickers,
            raw_dir=Path(self.raw_dir),
            processed_dir=Path(self.processed_dir),
            artifact_dir=Path(self.artifact_dir),
        )


def load_config(path: str | Path) -> DataPipelineConfig:
    """Load pipeline configuration from a YAML file."""

    config_path = Path(path)
    with config_path.open("r", encoding="utf-8") as handle:
        payload: dict[str, Any] = yaml.safe_load(handle) or {}

    return DataPipelineConfig(
        tickers=tuple(payload.get("tickers", DEFAULT_TICKERS)),
        start_date=payload.get("start_date", "2018-01-01"),
        end_date=payload.get("end_date"),
        spike_threshold=float(payload.get("spike_threshold", 0.15)),
        raw_dir=Path(payload.get("raw_dir", "data/raw")),
        processed_dir=Path(payload.get("processed_dir", "data/processed")),
        artifact_dir=Path(payload.get("artifact_dir", "data/artifacts")),
    ).normalized()
