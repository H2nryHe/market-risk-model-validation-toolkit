"""Independent validation reference calculations."""

from market_risk_toolkit.validation.independent.gaussian_reference import (
    gaussian_expected_shortfall,
    gaussian_var,
)
from market_risk_toolkit.validation.independent.historical_reference import (
    historical_expected_shortfall,
    historical_var,
)

__all__ = [
    "gaussian_expected_shortfall",
    "gaussian_var",
    "historical_expected_shortfall",
    "historical_var",
]
