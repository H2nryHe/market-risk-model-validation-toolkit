from __future__ import annotations

import json
from pathlib import Path

import pandas as pd

from market_risk_toolkit.monitoring.metrics import AMBER, GREEN, RED

ROOT = Path(__file__).resolve().parents[1]


def test_monitoring_summary_documents_historical_frozen_scope_and_no_phase8_decision() -> None:
    summary = json.loads((ROOT / "data/artifacts/monitoring_summary.json").read_text())

    assert summary["phase"] == 7
    assert summary["snapshot_is_live"] is False
    assert "historical frozen-data replay" in summary["monitoring_scope"]
    assert "not live" in summary["monitoring_scope"]
    assert summary["final_validation_decision"] is None


def test_monitoring_snapshot_is_last_frozen_forecast_date_for_mr001_95_and_99() -> None:
    forecasts = pd.read_csv(ROOT / "data/artifacts/challenger_forecasts.csv")
    snapshot = pd.read_csv(ROOT / "data/artifacts/monitoring_snapshot.csv")

    assert snapshot["as_of_date"].nunique() == 1
    assert snapshot["as_of_date"].iloc[0] == forecasts["date"].max()
    assert set(snapshot["confidence_level"]) == {0.95, 0.99}
    assert snapshot["snapshot_is_live"].eq(False).all()
    assert snapshot["snapshot_scope"].str.contains("not live/current", regex=False).all()


def test_monitoring_history_contains_required_metric_columns_and_only_mr001_rows() -> None:
    history = pd.read_csv(ROOT / "data/artifacts/monitoring_history.csv")
    required = {
        "date",
        "confidence_level",
        "mr001_var",
        "mr001_es",
        "realized_loss",
        "is_exception",
        "rolling_exception_rate_125",
        "rolling_exception_rate_250",
        "kupiec_p_value_250",
        "conditional_coverage_p_value_250",
        "exceptions_last_5d",
        "exceptions_last_10d",
        "days_since_last_exception",
        "mr002_divergence",
        "mr003_divergence",
        "mr004_divergence",
        "max_challenger_divergence",
        "volatility_60d",
        "volatility_regime",
        "high_vol_tail_escalation",
        "data_quality_status",
        "exception_rate_status",
        "kupiec_status",
        "conditional_coverage_status",
        "cluster_status",
        "challenger_divergence_status",
        "challenger_review_required",
        "far_tail_performance_watch",
        "dependence_watch_status",
        "tail_watch_status",
        "overall_status",
        "open_findings",
        "snapshot_is_live",
    }

    assert required.issubset(history.columns)
    assert set(history["confidence_level"]) == {0.95, 0.99}
    assert not any(column.startswith("mr005") for column in history.columns)


def test_challenger_red_alone_no_longer_forces_hard_red_overall() -> None:
    history = pd.read_csv(ROOT / "data/artifacts/monitoring_history.csv")
    challenger_only = history[
        history["challenger_divergence_status"].eq(RED)
        & history["exception_rate_status"].eq(GREEN)
        & history["kupiec_status"].eq(GREEN)
        & history["dependence_watch_status"].eq(GREEN)
    ]

    assert not challenger_only.empty
    assert challenger_only["challenger_review_required"].eq(True).all()
    assert challenger_only["far_tail_performance_watch"].eq(AMBER).all()
    assert challenger_only["overall_status"].eq(AMBER).all()


def test_99_exception_rate_or_kupiec_red_forces_far_tail_performance_red() -> None:
    history = pd.read_csv(ROOT / "data/artifacts/monitoring_history.csv")
    tail_99 = history[history["confidence_level"].eq(0.99)].copy()
    component_red = tail_99["exception_rate_status"].eq(RED) | tail_99["kupiec_status"].eq(RED)

    assert tail_99.loc[component_red, "far_tail_performance_watch"].eq(RED).all()
    assert tail_99.loc[component_red, "overall_status"].eq(RED).all()


def test_high_vol_tail_escalation_requires_tail_watch_warning_or_breach() -> None:
    history = pd.read_csv(ROOT / "data/artifacts/monitoring_history.csv")
    escalations = history[history["high_vol_tail_escalation"].eq(True)]

    assert not escalations.empty
    assert escalations["volatility_regime"].eq("HIGH_VOL").all()
    assert escalations["far_tail_performance_watch"].isin([AMBER, RED]).all()


def test_high_volatility_alone_does_not_force_overall_red() -> None:
    history = pd.read_csv(ROOT / "data/artifacts/monitoring_history.csv")
    green_high_vol = history[
        history["volatility_regime"].eq("HIGH_VOL")
        & history["exception_rate_status"].eq(GREEN)
        & history["kupiec_status"].eq(GREEN)
        & history["conditional_coverage_status"].eq(GREEN)
        & history["cluster_status"].eq(GREEN)
        & history["challenger_divergence_status"].eq(GREEN)
        & history["far_tail_performance_watch"].eq(GREEN)
        & history["dependence_watch_status"].eq(GREEN)
    ]

    if not green_high_vol.empty:
        assert green_high_vol["overall_status"].eq(GREEN).all()


def test_phase6_data_quality_gate_is_integrated_as_green_for_clean_frozen_data() -> None:
    history = pd.read_csv(ROOT / "data/artifacts/monitoring_history.csv")
    summary = json.loads((ROOT / "data/artifacts/monitoring_summary.json").read_text())

    assert history["data_quality_status"].eq(GREEN).all()
    assert any("data-quality" in item.lower() for item in summary["limitations"])


def test_monitoring_volatility_thresholds_are_not_phase2_full_sample_thresholds() -> None:
    monitoring = json.loads((ROOT / "data/artifacts/monitoring_summary.json").read_text())
    phase2 = json.loads((ROOT / "data/artifacts/conceptual_soundness_summary.json").read_text())

    monitoring_calibration = monitoring["volatility_calibration"]
    phase2_regime = phase2["regime_methodology"]
    assert monitoring_calibration["calibration_observations"] == 500
    assert "first 500" in monitoring_calibration["methodology"]
    assert monitoring_calibration["lower_threshold"] != phase2_regime["low_volatility_threshold"]
    assert monitoring_calibration["upper_threshold"] != phase2_regime["high_volatility_threshold"]
    assert phase2_regime["method"] == "full_sample_rolling_volatility_quantiles"


def test_breach_log_has_unique_ids_thresholds_escalation_actions_and_finding_links() -> None:
    breaches = pd.read_csv(ROOT / "data/artifacts/monitoring_breaches.csv")

    assert not breaches.empty
    assert breaches["breach_id"].is_unique
    assert breaches["threshold"].str.len().gt(0).all()
    assert breaches["escalation_action"].str.len().gt(0).all()
    assert set(breaches["status"]).issubset({AMBER, RED})
    assert breaches["finding_id"].str.contains("MV-001|MV-002").all()
    assert set(breaches.loc[breaches["status"].eq(RED), "driver_type"]).issubset(
        {"DATA_QUALITY", "FAR_TAIL_PERFORMANCE", "TEMPORAL_DEPENDENCE"}
    )
    challenger = breaches[breaches["driver_type"].eq("CONTEXTUAL_CHALLENGER")]
    assert not challenger.empty
    assert challenger["status"].eq(AMBER).all()
    assert challenger["escalation_action"].str.contains("not treating it as proof", regex=False).all()


def test_framework_comparison_artifact_preserves_v1_0_and_v1_1_alert_diagnostics() -> None:
    comparison = pd.read_csv(ROOT / "data/artifacts/monitoring_framework_comparison.csv")

    assert set(comparison["framework_version"]) == {1.0, 1.1}
    assert set(comparison["confidence_level"]) == {0.95, 0.99}
    assert comparison["observation_count"].eq(1804).all()
    assert comparison["red_fraction"].between(0.0, 1.0).all()
    assert comparison["longest_continuous_red_streak"].ge(0).all()
    assert comparison["red_episode_count"].ge(0).all()


def test_monitoring_summary_records_version_review_without_final_decision() -> None:
    summary = json.loads((ROOT / "data/artifacts/monitoring_summary.json").read_text())
    review = summary["framework_version_review"]

    assert review["previous_version"] == "1.0"
    assert review["active_version"] == "1.1"
    assert review["numeric_threshold_change"] is False
    assert review["v1_thresholds_hash"]
    assert summary["final_validation_decision"] is None


def test_monitoring_report_states_controls_are_not_finding_closure_or_final_decision() -> None:
    report = (ROOT / "reports/monitoring_report.md").read_text().lower()

    assert "not a live/current market-risk status" in report
    assert "not equivalent to closing" in report
    assert "findings are not closed in phase 7" in report
    assert "no validated, validated_with_conditions, restricted_use, or" in report
    assert "not_validated decision is assigned here" in report
    assert "phase 8 subsequently assigned the final validation decision **restricted_use**" in report
    assert "does not close mv-001 or" in report
    assert "root causes were eliminated" in report
    assert "monitoring framework version review" in report
    assert "alert saturation" in report
    assert "challenger difference alone is not treated as proof" in report
    assert "version 1.1 is not a post-hoc attempt to make mr-001 pass" in report
