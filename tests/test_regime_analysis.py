from __future__ import annotations

import numpy as np
import pandas as pd

from market_risk_toolkit.validation.outcomes import build_exception_diagnostics
from market_risk_toolkit.validation.regime import REGIME_SCOPE_LABEL, build_regime_backtest


def _diagnostics_fixture() -> pd.DataFrame:
    dates = pd.date_range("2026-01-01", periods=10, freq="D")
    forecasts = pd.DataFrame(
        {
            "date": dates.strftime("%Y-%m-%d"),
            "model_id": "MR-TEST",
            "model_name": "Fixture VaR",
            "confidence_level": 0.95,
            "var": 1.0,
            "es": 1.5,
            "realized_loss": [1.2, 0.2, 1.3, 0.1, 0.2, 1.4, 0.3, 1.1, 0.2, 0.1],
        }
    )
    regimes = pd.DataFrame(
        {
            "date": dates,
            "volatility_regime": [
                "HIGH_VOL",
                "HIGH_VOL",
                "NORMAL_VOL",
                "NORMAL_VOL",
                "LOW_VOL",
                "HIGH_VOL",
                "LOW_VOL",
                "HIGH_VOL",
                "NORMAL_VOL",
                "LOW_VOL",
            ],
        }
    )
    return build_exception_diagnostics(forecasts, regimes)


def test_regime_outputs_preserve_retrospective_descriptive_label() -> None:
    backtest = build_regime_backtest(_diagnostics_fixture(), min_observations_for_test=1)

    assert set(backtest["regime_scope"]) == {REGIME_SCOPE_LABEL}


def test_high_vol_concentration_ratio_is_calculated_correctly() -> None:
    backtest = build_regime_backtest(_diagnostics_fixture(), min_observations_for_test=1)
    high = backtest[backtest["volatility_regime"].eq("HIGH_VOL")].iloc[0]

    expected_exception_fraction = 3 / 4
    expected_observation_fraction = 4 / 10
    assert np.isclose(high["fraction_all_exceptions_in_high_vol"], expected_exception_fraction)
    assert np.isclose(high["fraction_observations_in_high_vol"], expected_observation_fraction)
    assert np.isclose(
        high["high_vol_exception_concentration_ratio"],
        expected_exception_fraction / expected_observation_fraction,
    )


def test_insufficient_regime_samples_are_handled_safely() -> None:
    backtest = build_regime_backtest(
        _diagnostics_fixture(),
        min_observations_for_test=100,
        min_expected_exceptions_for_test=10.0,
    )

    assert set(backtest["regime_test_status"]) == {"INSUFFICIENT_DATA"}
    assert backtest["kupiec_p_value"].isna().all()
    assert backtest["insufficient_data_reason"].notna().all()
