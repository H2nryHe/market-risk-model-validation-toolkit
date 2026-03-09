import json

import pandas as pd

from market_risk_toolkit.data.config import DataPipelineConfig
from market_risk_toolkit.data.pipeline import run_data_pipeline


def test_run_data_pipeline_writes_expected_artifacts(monkeypatch, tmp_path) -> None:
    raw_prices = pd.DataFrame(
        {
            "SPY": [100.0, 101.0, 99.0],
            "QQQ": [200.0, 198.0, 202.0],
            "TLT": [90.0, 91.0, 92.0],
            "GLD": [180.0, 181.0, 182.0],
        },
        index=pd.to_datetime(["2024-01-02", "2024-01-03", "2024-01-04"]),
    )
    metadata = {
        "source": "yfinance",
        "downloaded_at_utc": "2026-03-09T00:00:00+00:00",
        "tickers": ["SPY", "QQQ", "TLT", "GLD"],
        "start_date": "2024-01-01",
        "end_date": None,
        "rows": 3,
        "columns": 4,
    }

    def fake_download_adjusted_close(*args, **kwargs):
        return raw_prices, metadata

    monkeypatch.setattr(
        "market_risk_toolkit.data.pipeline.download_adjusted_close",
        fake_download_adjusted_close,
    )

    config = DataPipelineConfig(
        tickers=("SPY", "QQQ", "TLT", "GLD"),
        start_date="2024-01-01",
        raw_dir=tmp_path / "raw",
        processed_dir=tmp_path / "processed",
        artifact_dir=tmp_path / "artifacts",
    )
    result = run_data_pipeline(config)

    assert result.raw_prices_path.exists()
    assert result.cleaned_prices_path.exists()
    assert result.returns_path.exists()
    assert result.validation_summary_path.exists()
    assert result.validation_flags_path.exists()

    with result.validation_summary_path.open("r", encoding="utf-8") as handle:
        summary = json.load(handle)

    assert summary["ticker_count"] == 4
    assert summary["return_observation_count"] == 2
    assert summary["source"] == "yfinance"
