import math

import pandas as pd
import pytest
from scipy.stats import norm

from market_risk_toolkit.risk.metrics import (
    compute_rolling_risk_metrics,
    historical_es,
    historical_var,
    parametric_es,
    parametric_var,
)


def test_historical_var_and_es_match_empirical_tail_for_95_percent() -> None:
    returns = pd.Series(
        [-0.10, -0.05] + [0.0] * 19,
        index=pd.date_range("2024-01-01", periods=21, freq="D"),
    )

    assert historical_var(returns, 0.95) == pytest.approx(0.05)
    assert historical_es(returns, 0.95) == pytest.approx(0.075)


def test_parametric_var_and_es_match_gaussian_formula() -> None:
    returns = pd.Series(
        [-0.02, -0.01, 0.0, 0.01, 0.02],
        index=pd.date_range("2024-01-01", periods=5, freq="D"),
    )
    mean = float(returns.mean())
    volatility = float(returns.std(ddof=1))
    z_score = float(norm.ppf(1.0 - 0.95))
    expected_var = -(mean + volatility * z_score)
    expected_es = -(mean - volatility * norm.pdf(z_score) / 0.05)

    assert parametric_var(returns, 0.95) == pytest.approx(expected_var)
    assert parametric_es(returns, 0.95) == pytest.approx(expected_es)


def test_compute_rolling_risk_metrics_returns_clean_table_with_95_and_99_columns() -> None:
    returns = pd.Series(
        [-0.02, -0.01, 0.00, 0.01, 0.015, -0.005],
        index=pd.date_range("2024-01-01", periods=6, freq="D"),
        name="portfolio_return",
    )

    risk_table = compute_rolling_risk_metrics(returns, window=4, confidence_levels=(0.95, 0.99))

    assert risk_table.shape[0] == 2
    assert "historical_var_95" in risk_table.columns
    assert "historical_es_95" in risk_table.columns
    assert "parametric_var_99" in risk_table.columns
    assert "parametric_es_99" in risk_table.columns
    assert (risk_table.filter(like="_var_") >= 0.0).all().all()
    assert (risk_table.filter(like="_es_") >= 0.0).all().all()
    assert math.isclose(
        float(risk_table.iloc[-1]["portfolio_return"]),
        -0.005,
        rel_tol=0.0,
        abs_tol=1e-12,
    )
