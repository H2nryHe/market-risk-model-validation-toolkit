"""Conceptual soundness diagnostics for the Gaussian VaR / ES model."""

from __future__ import annotations

import argparse
import hashlib
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from scipy import stats

from market_risk_toolkit.portfolio.analytics import build_portfolio
from market_risk_toolkit.portfolio.config import load_portfolio_config
from market_risk_toolkit.portfolio.io import load_returns_panel

DEFAULT_ROLLING_WINDOW = 60
REGIME_LABELS = ("LOW_VOL", "NORMAL_VOL", "HIGH_VOL")


@dataclass(frozen=True)
class ConceptualArtifactPaths:
    """Paths written by the conceptual soundness diagnostic run."""

    summary_json: Path
    distribution_csv: Path
    rolling_csv: Path
    regime_csv: Path
    report_md: Path
    histogram_figure: Path
    qq_figure: Path
    rolling_regime_figure: Path


def analyze_distribution(returns: pd.Series) -> dict[str, float | int]:
    """Compute deterministic whole-distribution diagnostics."""

    clean = _clean_returns(returns)
    mean = float(clean.mean())
    volatility = float(clean.std(ddof=1))
    jarque_bera = stats.jarque_bera(clean.to_numpy())
    empirical_1 = float(clean.quantile(0.01))
    empirical_5 = float(clean.quantile(0.05))
    gaussian_1 = float(stats.norm.ppf(0.01, loc=mean, scale=volatility))
    gaussian_5 = float(stats.norm.ppf(0.05, loc=mean, scale=volatility))
    return {
        "observation_count": int(clean.shape[0]),
        "mean_daily_return": mean,
        "volatility": volatility,
        "skewness": float(clean.skew()),
        "excess_kurtosis": float(clean.kurt()),
        "minimum": float(clean.min()),
        "maximum": float(clean.max()),
        "empirical_1pct_return_quantile": empirical_1,
        "empirical_5pct_return_quantile": empirical_5,
        "gaussian_1pct_return_quantile": gaussian_1,
        "gaussian_5pct_return_quantile": gaussian_5,
        "return_1pct_absolute_difference": empirical_1 - gaussian_1,
        "return_1pct_relative_difference": _stable_relative_difference(empirical_1, gaussian_1),
        "return_5pct_absolute_difference": empirical_5 - gaussian_5,
        "return_5pct_relative_difference": _stable_relative_difference(empirical_5, gaussian_5),
        "jarque_bera_statistic": float(jarque_bera.statistic),
        "jarque_bera_p_value": float(jarque_bera.pvalue),
    }


def compute_tail_comparison(returns: pd.Series) -> dict[str, float | int]:
    """Compare observed loss-tail behavior with a fitted Gaussian distribution."""

    clean = _clean_returns(returns)
    losses = -clean
    mean = float(clean.mean())
    volatility = float(clean.std(ddof=1))

    empirical_95_loss = float(losses.quantile(0.95))
    empirical_99_loss = float(losses.quantile(0.99))
    gaussian_95_loss = float(-(mean + volatility * stats.norm.ppf(0.05)))
    gaussian_99_loss = float(-(mean + volatility * stats.norm.ppf(0.01)))

    beyond_95 = losses > gaussian_95_loss
    beyond_99 = losses > gaussian_99_loss
    observation_count = int(clean.shape[0])
    return {
        "empirical_95_loss_quantile": empirical_95_loss,
        "gaussian_95_loss_quantile": gaussian_95_loss,
        "loss_95_absolute_difference": empirical_95_loss - gaussian_95_loss,
        "loss_95_relative_difference": _stable_relative_difference(
            empirical_95_loss,
            gaussian_95_loss,
        ),
        "observations_beyond_gaussian_95_loss_threshold": int(beyond_95.sum()),
        "frequency_beyond_gaussian_95_loss_threshold": float(beyond_95.mean()),
        "empirical_99_loss_quantile": empirical_99_loss,
        "gaussian_99_loss_quantile": gaussian_99_loss,
        "loss_99_absolute_difference": empirical_99_loss - gaussian_99_loss,
        "loss_99_relative_difference": _stable_relative_difference(
            empirical_99_loss,
            gaussian_99_loss,
        ),
        "observations_beyond_gaussian_99_loss_threshold": int(beyond_99.sum()),
        "frequency_beyond_gaussian_99_loss_threshold": float(beyond_99.mean()),
        "observation_count": observation_count,
    }


def compute_rolling_diagnostics(returns: pd.Series, window: int = DEFAULT_ROLLING_WINDOW) -> pd.DataFrame:
    """Compute trailing rolling distribution diagnostics."""

    if window < 2:
        raise ValueError("Rolling diagnostic window must be at least 2 observations.")
    clean = _clean_returns(returns)
    rolling = clean.rolling(window=window, min_periods=window)
    frame = pd.DataFrame(
        {
            "portfolio_return": clean,
            "rolling_volatility": rolling.std(ddof=1),
            "rolling_skewness": rolling.apply(_sample_skewness, raw=True),
            "rolling_excess_kurtosis": rolling.apply(_sample_excess_kurtosis, raw=True),
        }
    )
    frame.index.name = "date"
    return frame


def classify_descriptive_regimes(
    rolling_volatility: pd.Series,
) -> tuple[pd.Series, dict[str, float | str | bool]]:
    """Classify volatility regimes using full-sample retrospective quantiles."""

    valid = rolling_volatility.dropna()
    if valid.empty:
        raise ValueError("Rolling volatility has no valid observations to classify.")
    low_boundary = float(valid.quantile(0.25))
    high_boundary = float(valid.quantile(0.75))
    regimes = pd.Series(index=rolling_volatility.index, dtype="object", name="regime")
    regimes.loc[rolling_volatility <= low_boundary] = "LOW_VOL"
    regimes.loc[(rolling_volatility > low_boundary) & (rolling_volatility < high_boundary)] = (
        "NORMAL_VOL"
    )
    regimes.loc[rolling_volatility >= high_boundary] = "HIGH_VOL"
    metadata: dict[str, float | str | bool] = {
        "method": "full_sample_rolling_volatility_quantiles",
        "low_volatility_threshold": low_boundary,
        "high_volatility_threshold": high_boundary,
        "retrospective_descriptive": True,
        "note": "Regime thresholds use full-sample rolling volatility quantiles and are not causal monitoring thresholds.",
    }
    return regimes, metadata


def summarize_regimes(
    returns: pd.Series,
    rolling_diagnostics: pd.DataFrame,
    regimes: pd.Series,
    min_tail_observations: int = 100,
) -> pd.DataFrame:
    """Summarize distribution behavior inside each descriptive volatility regime."""

    clean = _clean_returns(returns)
    rows: list[dict[str, Any]] = []
    for label in REGIME_LABELS:
        mask = regimes == label
        regime_returns = clean.loc[mask.reindex(clean.index, fill_value=False)]
        observation_count = int(regime_returns.shape[0])
        has_enough_tail_data = observation_count >= min_tail_observations
        row: dict[str, Any] = {
            "regime": label,
            "observation_count": observation_count,
            "mean_return": _float_or_nan(regime_returns.mean()),
            "volatility": _float_or_nan(regime_returns.std(ddof=1)),
            "skewness": _float_or_nan(regime_returns.skew()),
            "excess_kurtosis": _float_or_nan(regime_returns.kurt()),
            "empirical_1pct_return_quantile": _float_or_nan(regime_returns.quantile(0.01))
            if observation_count
            else np.nan,
            "empirical_99pct_loss_quantile": _float_or_nan((-regime_returns).quantile(0.99))
            if observation_count
            else np.nan,
            "tail_sample_limitation": not has_enough_tail_data,
            "tail_sample_note": (
                "Tail quantile has limited support below 100 observations."
                if not has_enough_tail_data
                else ""
            ),
        }
        if observation_count:
            row["average_rolling_volatility"] = _float_or_nan(
                rolling_diagnostics.loc[mask, "rolling_volatility"].mean()
            )
        else:
            row["average_rolling_volatility"] = np.nan
        rows.append(row)
    return pd.DataFrame(rows)


def build_conceptual_summary(
    returns: pd.Series,
    *,
    portfolio_name: str,
    portfolio_weights: dict[str, float],
    input_data_path: str | Path,
    rolling_window: int,
) -> tuple[dict[str, Any], pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    """Build all conceptual diagnostics for serialization."""

    clean = _clean_returns(returns)
    distribution = analyze_distribution(clean)
    tail_comparison = compute_tail_comparison(clean)
    rolling_diagnostics = compute_rolling_diagnostics(clean, window=rolling_window)
    regimes, regime_metadata = classify_descriptive_regimes(
        rolling_diagnostics["rolling_volatility"]
    )
    rolling_with_regimes = rolling_diagnostics.copy()
    rolling_with_regimes["regime"] = regimes
    regime_summary = summarize_regimes(clean, rolling_with_regimes, regimes)

    distribution_table = _distribution_table(distribution, tail_comparison)
    summary = {
        "model_id": "MR-001",
        "model_name": "Gaussian Parametric VaR / ES",
        "portfolio": {
            "name": portfolio_name,
            "strategy": "equal_weight",
            "weights": portfolio_weights,
        },
        "input_data_path": str(input_data_path),
        "input_data_hash": sha256_file(input_data_path),
        "observation_count": int(distribution["observation_count"]),
        "date_range": {
            "start": clean.index.min().strftime("%Y-%m-%d"),
            "end": clean.index.max().strftime("%Y-%m-%d"),
        },
        "distribution": distribution,
        "tail_comparison": tail_comparison,
        "regime_methodology": {
            "rolling_window": rolling_window,
            "regime_definition": {
                "LOW_VOL": "rolling volatility <= 25th percentile",
                "NORMAL_VOL": "25th percentile < rolling volatility < 75th percentile",
                "HIGH_VOL": "rolling volatility >= 75th percentile",
            },
            **regime_metadata,
        },
        "limitations": [
            "Public ETF proxies are used instead of real institutional positions.",
            "The sample is finite and covers one historical market period.",
            "Regime thresholds are retrospective/descriptive and not causal monitoring thresholds.",
            "Diagnostics use daily returns and do not address other horizons.",
            "Conceptual diagnostics do not replace formal outcomes analysis.",
            "No challenger evidence is produced in Phase 2.",
            "No independent implementation verification is performed in Phase 2.",
        ],
        "candidate_concern": (
            "Gaussian tail assumptions may be materially weak during high-volatility or "
            "fat-tail periods; later outcomes and challenger analysis should test this."
        ),
        "phase_2_conclusion": "Conceptual soundness concerns identified.",
        "final_validation_decision": None,
    }
    return summary, distribution_table, rolling_with_regimes.reset_index(), regime_summary


def run_conceptual_diagnostics(
    *,
    portfolio_config_path: str | Path = "configs/portfolios/example_portfolio.yaml",
    rolling_window: int = DEFAULT_ROLLING_WINDOW,
    output_dir: str | Path = "data/artifacts",
    report_path: str | Path = "reports/sections/conceptual_soundness.md",
    figure_dir: str | Path = "reports/figures",
) -> ConceptualArtifactPaths:
    """Run Phase 2 conceptual diagnostics and write deterministic artifacts."""

    config = load_portfolio_config(portfolio_config_path)
    returns_panel = load_returns_panel(config.returns_path)
    portfolio = build_portfolio(returns_panel, config)
    summary, distribution_table, rolling_table, regime_summary = build_conceptual_summary(
        portfolio.daily_returns,
        portfolio_name=config.name,
        portfolio_weights={str(k): float(v) for k, v in portfolio.weights.items()},
        input_data_path=config.returns_path,
        rolling_window=rolling_window,
    )

    output = Path(output_dir)
    report = Path(report_path)
    figures = Path(figure_dir)
    output.mkdir(parents=True, exist_ok=True)
    report.parent.mkdir(parents=True, exist_ok=True)
    figures.mkdir(parents=True, exist_ok=True)

    paths = ConceptualArtifactPaths(
        summary_json=output / "conceptual_soundness_summary.json",
        distribution_csv=output / "distribution_diagnostics.csv",
        rolling_csv=output / "rolling_distribution_diagnostics.csv",
        regime_csv=output / "regime_summary.csv",
        report_md=report,
        histogram_figure=figures / "return_distribution_vs_gaussian.png",
        qq_figure=figures / "normal_qq_plot.png",
        rolling_regime_figure=figures / "rolling_volatility_regimes.png",
    )
    paths.summary_json.write_text(_json_dumps(summary), encoding="utf-8")
    distribution_table.to_csv(paths.distribution_csv, index=False)
    rolling_table.to_csv(paths.rolling_csv, index=False)
    regime_summary.to_csv(paths.regime_csv, index=False)
    paths.report_md.write_text(_render_report(summary, regime_summary), encoding="utf-8")
    _save_distribution_figure(portfolio.daily_returns, paths.histogram_figure)
    _save_qq_figure(portfolio.daily_returns, paths.qq_figure)
    _save_rolling_regime_figure(rolling_table, paths.rolling_regime_figure)
    return paths


def sha256_file(path: str | Path) -> str:
    """Return the SHA-256 hash of a file."""

    digest = hashlib.sha256()
    with Path(path).open("rb") as file:
        for chunk in iter(lambda: file.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run Phase 2 conceptual soundness diagnostics.")
    parser.add_argument("--portfolio-config", default="configs/portfolios/example_portfolio.yaml")
    parser.add_argument("--rolling-window", type=int, default=DEFAULT_ROLLING_WINDOW)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    paths = run_conceptual_diagnostics(
        portfolio_config_path=args.portfolio_config,
        rolling_window=args.rolling_window,
    )
    print(
        _json_dumps(
            {
                "summary_json": str(paths.summary_json),
                "distribution_csv": str(paths.distribution_csv),
                "rolling_csv": str(paths.rolling_csv),
                "regime_csv": str(paths.regime_csv),
                "report_md": str(paths.report_md),
            }
        )
    )
    return 0


def _clean_returns(returns: pd.Series) -> pd.Series:
    clean = returns.copy(deep=True).dropna().astype(float)
    if clean.empty:
        raise ValueError("Return series is empty after dropping missing values.")
    clean = clean.sort_index()
    clean.name = returns.name or "portfolio_return"
    return clean


def _stable_relative_difference(observed: float, reference: float) -> float | None:
    if abs(reference) < 1.0e-12:
        return None
    return float((observed - reference) / abs(reference))


def _sample_skewness(values: np.ndarray) -> float:
    series = pd.Series(values)
    return float(series.skew())


def _sample_excess_kurtosis(values: np.ndarray) -> float:
    series = pd.Series(values)
    return float(series.kurt())


def _float_or_nan(value: Any) -> float:
    if pd.isna(value):
        return float("nan")
    return float(value)


def _distribution_table(
    distribution: dict[str, float | int],
    tail_comparison: dict[str, float | int],
) -> pd.DataFrame:
    rows = []
    for metric, value in distribution.items():
        rows.append({"section": "distribution", "metric": metric, "value": value})
    for metric, value in tail_comparison.items():
        rows.append({"section": "left_tail", "metric": metric, "value": value})
    return pd.DataFrame(rows)


def _json_dumps(payload: dict[str, Any]) -> str:
    return json.dumps(payload, indent=2, sort_keys=True, default=_json_default) + "\n"


def _json_default(value: object) -> object:
    if isinstance(value, (np.floating, np.integer)):
        return value.item()
    if isinstance(value, float) and np.isnan(value):
        return None
    raise TypeError(f"Object of type {type(value).__name__} is not JSON serializable")


def _render_report(summary: dict[str, Any], regime_summary: pd.DataFrame) -> str:
    distribution = summary["distribution"]
    tail = summary["tail_comparison"]
    regime_methodology = summary["regime_methodology"]
    regime_lines = "\n".join(
        (
            f"| {row.regime} | {int(row.observation_count)} | "
            f"{row.mean_return:.6f} | {row.volatility:.6f} | "
            f"{row.skewness:.3f} | {row.excess_kurtosis:.3f} | "
            f"{row.empirical_99pct_loss_quantile:.4%} | "
            f"{'yes' if row.tail_sample_limitation else 'no'} |"
        )
        for row in regime_summary.itertuples(index=False)
    )
    high_vol = regime_summary.loc[regime_summary["regime"] == "HIGH_VOL"].iloc[0]
    normal_vol = regime_summary.loc[regime_summary["regime"] == "NORMAL_VOL"].iloc[0]
    fragility_sentence = (
        "The HIGH_VOL regime has the largest volatility and a materially larger "
        "99% empirical loss quantile than the NORMAL_VOL regime, so Gaussian tail "
        "fragility appears most relevant in stressed volatility conditions."
        if high_vol["empirical_99pct_loss_quantile"] > normal_vol["empirical_99pct_loss_quantile"]
        else "Regime tail differences are present, but the diagnostic does not support a strong ranking without later outcomes analysis."
    )
    return f"""# Conceptual Soundness Review - MR-001

## 1. Model Under Review

MR-001 is the Gaussian Parametric VaR / ES model. It is the primary model under
validation defined in the Phase 1 governance inventory.

## 2. Purpose and Intended Use

The Phase 1 governance artifacts define MR-001 for daily internal market-risk
monitoring of the project's hypothetical liquid multi-asset portfolio. The
portfolio is the existing V1 baseline equal-weight portfolio: SPY 25%, QQQ 25%,
TLT 25%, and GLD 25%. This review does not evaluate regulatory capital,
live institutional systems, or real institutional approval.

## 3. Core Model Assumptions

The relevant conceptual assumptions are that daily portfolio returns are
approximately Gaussian within the estimation framework, that mean and volatility
adequately characterize the relevant one-day distribution, that Gaussian
probabilities are a reasonable approximation for tail behavior, and that the
historical sample dynamics are sufficiently representative for rolling
estimation.

## 4. Empirical Distribution Assessment

The frozen Phase 0 return snapshot contains {summary["observation_count"]:,}
portfolio-return observations from {summary["date_range"]["start"]} to
{summary["date_range"]["end"]}. Mean daily return is
{distribution["mean_daily_return"]:.6f}, volatility is
{distribution["volatility"]:.6f}, skewness is {distribution["skewness"]:.3f},
and excess kurtosis is {distribution["excess_kurtosis"]:.3f}.

Jarque-Bera statistic is {distribution["jarque_bera_statistic"]:.3f} with
p-value {distribution["jarque_bera_p_value"]:.3e}. This is statistical evidence
that the return distribution is inconsistent with exact Gaussianity. It is not,
by itself, a final model validation decision.

The empirical 1% return quantile is
{distribution["empirical_1pct_return_quantile"]:.4%} versus a fitted Gaussian
1% quantile of {distribution["gaussian_1pct_return_quantile"]:.4%}. The
empirical 5% return quantile is
{distribution["empirical_5pct_return_quantile"]:.4%} versus a fitted Gaussian
5% quantile of {distribution["gaussian_5pct_return_quantile"]:.4%}. The QQ plot
and histogram artifacts provide visual evidence for this comparison.

## 5. Left-Tail Assessment

Loss-tail diagnostics are kept separate from rolling VaR backtesting. They use
the full fitted distribution only as a conceptual assumption check.

At the 95% loss tail, the empirical loss quantile is
{tail["empirical_95_loss_quantile"]:.4%} versus a Gaussian-implied threshold of
{tail["gaussian_95_loss_quantile"]:.4%}. Observations beyond the fitted
Gaussian 95% loss threshold occur {tail["observations_beyond_gaussian_95_loss_threshold"]}
times, a frequency of {tail["frequency_beyond_gaussian_95_loss_threshold"]:.2%}.

At the 99% loss tail, the empirical loss quantile is
{tail["empirical_99_loss_quantile"]:.4%} versus a Gaussian-implied threshold of
{tail["gaussian_99_loss_quantile"]:.4%}. Observations beyond the fitted
Gaussian 99% loss threshold occur {tail["observations_beyond_gaussian_99_loss_threshold"]}
times, a frequency of {tail["frequency_beyond_gaussian_99_loss_threshold"]:.2%}.

Observed excess kurtosis and heavier empirical left-tail behavior provide a
plausible mechanism for Gaussian VaR / ES to underestimate extreme losses,
particularly at high confidence levels.

## 6. Time Variation and Regime Stability

Rolling diagnostics use a trailing {regime_methodology["rolling_window"]}-day
window, so each rolling value uses only observations available through that
date. The descriptive volatility regimes are based on full-sample rolling
volatility quantiles:

- LOW_VOL: {regime_methodology["low_volatility_threshold"]:.6f} or lower
- NORMAL_VOL: between the 25th and 75th percentiles
- HIGH_VOL: {regime_methodology["high_volatility_threshold"]:.6f} or higher

These thresholds are DESCRIPTIVE RETROSPECTIVE REGIME ANALYSIS. They use
full-sample quantiles, are not causal monitoring thresholds, and must not be
presented as live trading or production monitoring signals. Phase 7 monitoring
thresholds will require a live-safe and predeclared approach.

| Regime | Obs. | Mean | Volatility | Skew | Excess Kurtosis | 99% Loss Quantile | Tail Limitation |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | --- |
{regime_lines}

{fragility_sentence}

## 7. Implications for MR-001

The statistical evidence shows returns are inconsistent with exact Gaussianity.
The model-risk implication is narrower and more practical: negative skewness,
excess kurtosis, and empirical tail differences may cause Gaussian VaR / ES to
understate downside risk in stressed or fat-tail periods. This does not by
itself establish model failure. Outcomes analysis and challenger comparison are
required in later validation phases.

Candidate concern: Gaussian tail assumptions may be materially weak during
high-volatility or fat-tail periods.

## 8. Limitations of Phase 2

- Public ETF proxies are used instead of real institutional positions.
- The sample is finite and covers one historical market period.
- Regime thresholds are retrospective/descriptive and not causal monitoring thresholds.
- The diagnostics use a daily horizon only.
- Conceptual diagnostics do not replace formal outcomes analysis.
- No challenger evidence is produced in Phase 2.
- No independent implementation verification is performed in Phase 2.

## 9. Phase 2 Conclusion

Conceptual soundness concerns identified. The evidence supports further testing
of MR-001 tail behavior in Phase 3 through Phase 5, but no final validation
decision is assigned in Phase 2.
"""


def _save_distribution_figure(returns: pd.Series, destination: Path) -> None:
    clean = _clean_returns(returns)
    mean = float(clean.mean())
    volatility = float(clean.std(ddof=1))
    x_values = np.linspace(float(clean.min()), float(clean.max()), 300)
    fig, ax = plt.subplots(figsize=(8, 5))
    ax.hist(clean, bins=50, density=True, alpha=0.55, label="Empirical returns")
    ax.plot(
        x_values,
        stats.norm.pdf(x_values, loc=mean, scale=volatility),
        color="black",
        linewidth=1.8,
        label="Fitted Gaussian",
    )
    ax.set_title("Portfolio Returns vs Fitted Gaussian")
    ax.set_xlabel("Daily portfolio return")
    ax.set_ylabel("Density")
    ax.legend()
    fig.tight_layout()
    fig.savefig(destination, dpi=150)
    plt.close(fig)


def _save_qq_figure(returns: pd.Series, destination: Path) -> None:
    clean = _clean_returns(returns)
    fig = plt.figure(figsize=(6, 6))
    ax = fig.add_subplot(111)
    stats.probplot(clean.to_numpy(), dist="norm", plot=ax)
    ax.set_title("Normal QQ Plot - Portfolio Returns")
    fig.tight_layout()
    fig.savefig(destination, dpi=150)
    plt.close(fig)


def _save_rolling_regime_figure(rolling_table: pd.DataFrame, destination: Path) -> None:
    frame = rolling_table.dropna(subset=["rolling_volatility"]).copy()
    color_map = {"LOW_VOL": "#2a9d8f", "NORMAL_VOL": "#4c78a8", "HIGH_VOL": "#d1495b"}
    fig, ax = plt.subplots(figsize=(10, 5))
    for regime, group in frame.groupby("regime", sort=False):
        ax.scatter(
            group["date"],
            group["rolling_volatility"],
            s=8,
            label=regime,
            color=color_map.get(str(regime), "#666666"),
            alpha=0.8,
        )
    ax.set_title("Trailing Rolling Volatility Regimes")
    ax.set_xlabel("Date")
    ax.set_ylabel("60-day rolling volatility")
    ax.legend(markerscale=2)
    fig.tight_layout()
    fig.savefig(destination, dpi=150)
    plt.close(fig)


if __name__ == "__main__":
    raise SystemExit(main())
