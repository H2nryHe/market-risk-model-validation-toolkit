from __future__ import annotations

import numpy as np
import pandas as pd

from market_risk_toolkit.validation.outcomes import (
    build_cluster_summary,
    build_es_diagnostics,
    build_exception_diagnostics,
    build_rolling_exception_rates,
)


def _forecast_fixture() -> pd.DataFrame:
    dates = pd.date_range("2026-01-01", periods=8, freq="D")
    realized_loss = [0.5, 1.3, 0.2, 1.4, 1.5, 0.4, 0.3, 1.8]
    return pd.DataFrame(
        {
            "date": dates.strftime("%Y-%m-%d"),
            "model_id": "MR-TEST",
            "model_name": "Fixture VaR",
            "confidence_level": 0.95,
            "var": 1.0,
            "es": 1.4,
            "realized_loss": realized_loss,
        }
    )


def _regime_fixture() -> pd.DataFrame:
    return pd.DataFrame(
        {
            "date": pd.date_range("2026-01-01", periods=8, freq="D"),
            "volatility_regime": [
                "LOW_VOL",
                "LOW_VOL",
                "NORMAL_VOL",
                "HIGH_VOL",
                "HIGH_VOL",
                "NORMAL_VOL",
                "LOW_VOL",
                "HIGH_VOL",
            ],
        }
    )


def test_exception_amount_and_severity_ratio_formulas_are_deterministic() -> None:
    diagnostics = build_exception_diagnostics(_forecast_fixture(), _regime_fixture())

    first_exception = diagnostics[diagnostics["is_exception"]].iloc[0]
    first_non_exception = diagnostics[~diagnostics["is_exception"]].iloc[0]

    assert np.isclose(first_exception["exceedance_amount"], 0.3)
    assert np.isclose(first_exception["severity_ratio"], 1.3)
    assert first_non_exception["exceedance_amount"] == 0.0
    assert np.isnan(first_non_exception["severity_ratio"])


def test_exception_spacing_and_cluster_definition_are_hand_checkable() -> None:
    diagnostics = build_exception_diagnostics(_forecast_fixture(), _regime_fixture())
    exceptions = diagnostics[diagnostics["is_exception"]]

    assert exceptions["days_since_previous_exception"].tolist()[1:] == [2.0, 1.0, 3.0]

    summary = build_cluster_summary(diagnostics)
    row = summary.iloc[0]

    assert row["number_of_clusters"] == 1
    assert row["max_cluster_length"] == 4
    assert row["longest_consecutive_exception_run"] == 2
    assert "not a regulatory threshold" in row["cluster_definition"]


def test_trailing_rolling_exception_rate_uses_no_future_data() -> None:
    diagnostics = build_exception_diagnostics(_forecast_fixture(), _regime_fixture())
    perturbed = diagnostics.copy(deep=True)
    perturbed.loc[perturbed.index[-1], "is_exception"] = False

    base = build_rolling_exception_rates(diagnostics, windows=(3,))
    changed = build_rolling_exception_rates(perturbed, windows=(3,))

    pd.testing.assert_series_equal(
        base.loc[:5, "rolling_exception_rate_3"],
        changed.loc[:5, "rolling_exception_rate_3"],
        check_names=False,
    )
    assert base.loc[7, "rolling_exception_rate_3"] != changed.loc[7, "rolling_exception_rate_3"]


def test_regime_mapping_joins_forecast_dates() -> None:
    diagnostics = build_exception_diagnostics(_forecast_fixture(), _regime_fixture())

    assert diagnostics.loc[0, "volatility_regime"] == "LOW_VOL"
    assert diagnostics.loc[3, "volatility_regime"] == "HIGH_VOL"


def test_es_diagnostics_are_descriptive_and_deterministic() -> None:
    diagnostics = build_exception_diagnostics(_forecast_fixture(), _regime_fixture())
    es = build_es_diagnostics(diagnostics).iloc[0]

    assert es["exception_count"] == 4
    assert es["mean_forecast_es_on_exception_dates"] == 1.4
    assert es["mean_realized_loss_on_exception_dates"] == 1.5
    assert np.isclose(es["realized_loss_to_es_ratio"], 1.5 / 1.4)
    assert es["fraction_exceptions_exceeding_es"] == 0.5
    assert "not a definitive regulatory ES backtest" in es["diagnostic_scope"]
