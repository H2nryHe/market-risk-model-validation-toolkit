from __future__ import annotations

from pathlib import Path

from market_risk_toolkit.monitoring.thresholds import load_monitoring_thresholds

ROOT = Path(__file__).resolve().parents[1]


def test_phase7_threshold_file_loads_required_control_values() -> None:
    thresholds = load_monitoring_thresholds(ROOT / "configs/monitoring/thresholds.yaml")

    assert thresholds.threshold_version == "1.1"
    assert thresholds.exception_short_window == 125
    assert thresholds.exception_long_window == 250
    assert thresholds.statistical_window == 250
    assert thresholds.exception_rate_amber_multiplier == 1.25
    assert thresholds.exception_rate_red_multiplier == 1.50
    assert thresholds.statistical_red_p_value == 0.05
    assert thresholds.statistical_amber_p_value == 0.10
    assert thresholds.min_exception_count_for_dependence_test == 5


def test_phase7_1_archives_v1_0_threshold_configuration() -> None:
    archived = ROOT / "configs/monitoring/thresholds_v1_0.yaml"

    assert archived.exists()
    assert load_monitoring_thresholds(archived).threshold_version == "1.0"


def test_phase7_thresholds_are_identified_as_project_controls_not_regulatory_rules() -> None:
    thresholds = load_monitoring_thresholds(ROOT / "configs/monitoring/thresholds.yaml")
    disclaimer = thresholds.project_disclaimer.lower()

    assert "project-specific" in disclaimer
    assert "not regulatory" in disclaimer
    assert "not real-bank policy" in disclaimer


def test_phase7_challenger_and_cluster_thresholds_match_specification() -> None:
    thresholds = load_monitoring_thresholds(ROOT / "configs/monitoring/thresholds.yaml")

    assert thresholds.cluster_lookback_days == 10
    assert thresholds.cluster_amber_exception_count == 2
    assert thresholds.cluster_red_exception_count == 3
    assert thresholds.challenger_amber_relative_difference == 0.15
    assert thresholds.challenger_red_relative_difference == 0.25


def test_phase7_1_adds_metric_roles_without_changing_numeric_thresholds() -> None:
    thresholds = load_monitoring_thresholds(ROOT / "configs/monitoring/thresholds.yaml")
    roles = thresholds.raw_config["metric_roles"]

    assert "rolling_exception_rate" in roles["hard_performance_signals"]
    assert "kupiec_coverage" in roles["hard_performance_signals"]
    assert "challenger_divergence" in roles["contextual_challenge_signals"]
    assert "not proof" in roles["aggregation_semantics"]["challenger_divergence"].lower()
    assert thresholds.exception_rate_amber_multiplier == 1.25
    assert thresholds.exception_rate_red_multiplier == 1.50
    assert thresholds.statistical_red_p_value == 0.05
    assert thresholds.statistical_amber_p_value == 0.10
    assert thresholds.cluster_amber_exception_count == 2
    assert thresholds.cluster_red_exception_count == 3


def test_phase7_volatility_regime_uses_causal_initial_calibration_parameters() -> None:
    thresholds = load_monitoring_thresholds(ROOT / "configs/monitoring/thresholds.yaml")
    methodology = thresholds.raw_config["volatility_regime"]["methodology"].lower()

    assert thresholds.volatility_window == 60
    assert thresholds.volatility_calibration_observations == 500
    assert thresholds.volatility_lower_quantile == 0.25
    assert thresholds.volatility_upper_quantile == 0.75
    assert "first 500 valid" in methodology
    assert "frozen" in methodology


def test_phase7_reuses_phase6_data_quality_gate_parameters() -> None:
    thresholds = load_monitoring_thresholds(ROOT / "configs/monitoring/thresholds.yaml")

    assert thresholds.stale_price_threshold == 3
    assert thresholds.extreme_return_threshold == 0.15
    assert "phase 6" in thresholds.raw_config["data_quality"]["provenance"].lower()


def test_monitoring_modules_do_not_introduce_network_data_access() -> None:
    source = "\n".join(
        (ROOT / path).read_text()
        for path in [
            "src/market_risk_toolkit/monitoring/metrics.py",
            "src/market_risk_toolkit/monitoring/pipeline.py",
            "src/market_risk_toolkit/monitoring/thresholds.py",
        ]
    )

    assert "yfinance" not in source
    assert "requests." not in source
    assert "urllib" not in source
