"""Orchestration for the daily market data ingestion pipeline."""

from __future__ import annotations

import argparse
import json
from dataclasses import dataclass
from pathlib import Path

import pandas as pd

from market_risk_toolkit.data.config import DataPipelineConfig, load_config
from market_risk_toolkit.data.download import download_adjusted_close
from market_risk_toolkit.data.validation import (
    ValidationArtifacts,
    build_aligned_returns,
    validate_market_data,
)


@dataclass(frozen=True)
class DataPipelineResult:
    """References to generated in-repo data artifacts."""

    raw_prices: pd.DataFrame
    aligned_prices: pd.DataFrame
    returns: pd.DataFrame
    validation: ValidationArtifacts
    raw_prices_path: Path
    raw_metadata_path: Path
    cleaned_prices_path: Path
    returns_path: Path
    validation_summary_path: Path
    validation_flags_path: Path


def run_data_pipeline(config: DataPipelineConfig) -> DataPipelineResult:
    """Download, validate, align, and persist daily market data."""

    normalized_config = config.normalized()
    raw_prices, metadata = download_adjusted_close(
        tickers=normalized_config.tickers,
        start_date=normalized_config.start_date,
        end_date=normalized_config.end_date,
    )
    aligned_prices, returns = build_aligned_returns(raw_prices)
    validation = validate_market_data(
        raw_prices=raw_prices,
        aligned_prices=aligned_prices,
        returns=returns,
        spike_threshold=normalized_config.spike_threshold,
    )
    paths = _write_artifacts(
        raw_prices=raw_prices,
        aligned_prices=aligned_prices,
        returns=returns,
        validation=validation,
        metadata=metadata,
        config=normalized_config,
    )
    return DataPipelineResult(
        raw_prices=raw_prices,
        aligned_prices=aligned_prices,
        returns=returns,
        validation=validation,
        **paths,
    )


def parse_args() -> argparse.Namespace:
    """Parse CLI arguments for the data pipeline."""

    parser = argparse.ArgumentParser(description="Run the market data ingestion pipeline.")
    parser.add_argument(
        "--config",
        default="configs/data_pipeline.yaml",
        help="Path to the YAML config file.",
    )
    parser.add_argument("--start-date", dest="start_date", help="Override the config start date.")
    parser.add_argument("--end-date", dest="end_date", help="Override the config end date.")
    parser.add_argument(
        "--spike-threshold",
        dest="spike_threshold",
        type=float,
        help="Override the suspicious return threshold.",
    )
    return parser.parse_args()


def main() -> int:
    """CLI entry point for `python -m market_risk_toolkit.data`."""

    args = parse_args()
    config = load_config(args.config)
    if args.start_date:
        config = DataPipelineConfig(**{**config.__dict__, "start_date": args.start_date}).normalized()
    if args.end_date:
        config = DataPipelineConfig(**{**config.__dict__, "end_date": args.end_date}).normalized()
    if args.spike_threshold is not None:
        config = DataPipelineConfig(
            **{**config.__dict__, "spike_threshold": args.spike_threshold}
        ).normalized()

    result = run_data_pipeline(config)
    print(
        json.dumps(
            {
                "tickers": list(config.tickers),
                "raw_prices_path": str(result.raw_prices_path),
                "returns_path": str(result.returns_path),
                "validation_summary_path": str(result.validation_summary_path),
                "return_observation_count": int(result.returns.shape[0]),
                "suspicious_return_count": result.validation.summary["suspicious_return_count"],
            },
            indent=2,
        )
    )
    return 0


def _write_artifacts(
    raw_prices: pd.DataFrame,
    aligned_prices: pd.DataFrame,
    returns: pd.DataFrame,
    validation: ValidationArtifacts,
    metadata: dict[str, object],
    config: DataPipelineConfig,
) -> dict[str, Path]:
    for directory in (config.raw_dir, config.processed_dir, config.artifact_dir):
        directory.mkdir(parents=True, exist_ok=True)

    raw_prices_path = config.raw_dir / config.raw_prices_filename
    raw_metadata_path = config.raw_dir / config.raw_metadata_filename
    cleaned_prices_path = config.processed_dir / config.cleaned_prices_filename
    returns_path = config.processed_dir / config.returns_filename
    validation_summary_path = config.artifact_dir / config.validation_summary_filename
    validation_flags_path = config.artifact_dir / config.validation_flags_filename

    raw_prices.to_csv(raw_prices_path, index=True)
    aligned_prices.to_csv(cleaned_prices_path, index=True)
    returns.to_csv(returns_path, index=True)

    summary_payload = {
        **validation.summary,
        "tickers": list(config.tickers),
        "source": config.source,
        "raw_prices_path": str(raw_prices_path),
        "cleaned_prices_path": str(cleaned_prices_path),
        "returns_path": str(returns_path),
    }
    with raw_metadata_path.open("w", encoding="utf-8") as handle:
        json.dump(metadata, handle, indent=2)
    with validation_summary_path.open("w", encoding="utf-8") as handle:
        json.dump(summary_payload, handle, indent=2)

    if validation.flags.empty:
        validation.flags.to_csv(validation_flags_path, index=False)
    else:
        validation.flags.assign(
            date=lambda frame: frame["date"].astype("string")
        ).to_csv(validation_flags_path, index=False)

    return {
        "raw_prices_path": raw_prices_path,
        "raw_metadata_path": raw_metadata_path,
        "cleaned_prices_path": cleaned_prices_path,
        "returns_path": returns_path,
        "validation_summary_path": validation_summary_path,
        "validation_flags_path": validation_flags_path,
    }


if __name__ == "__main__":
    raise SystemExit(main())
