# Bank-Style Market Risk Model Validation & Governance Lab

Educational portfolio project for market risk model validation. It builds a full validation lifecycle around MR-001, a rolling Gaussian VaR / Expected Shortfall model for a hypothetical SPY / QQQ / TLT / GLD portfolio. It is not for live institutional use, regulatory capital, or compliance claims.

## What This Project Demonstrates

- Independent implementation verification inside a single repository
- Conceptual challenge of Gaussian tail assumptions
- Challenger benchmarking against historical, EWMA, and filtered historical methods
- Outcomes analysis across frequency, clustering, severity, and volatility regimes
- Deterministic market-data quality failure testing
- Formal findings, remediation tracking, monitoring, and final validation decisioning

## Validation Case

MR-001 estimates one-day 95% and 99% VaR / ES under a rolling Gaussian return assumption. The validation question is whether that model is fit for daily internal market-risk monitoring, portfolio loss-threshold awareness, model comparison, and project risk reporting for the hypothetical portfolio.

## Key Findings

- Independent verification matched 464/464 calculations with zero maximum absolute difference.
- MR-001 99% Gaussian VaR recorded 41/1804 exceptions, a 2.27% exception rate versus a 1% nominal tail.
- MR-001 95% exception frequency is close to nominal at 4.82%, but exceptions are clustered.
- HIGH_VOL 99% exception rate is 3.43%, with concentration ratio 1.51.
- Historical and FHS challengers improve some 99% coverage dimensions but retain dependence and finite-tail limitations.
- Data-quality controls detected and blocked 5/5 injected data failures with 0 false negatives.

## Validation Lifecycle

Inventory -> Conceptual Soundness -> Implementation Verification -> Challengers -> Outcomes -> Sensitivity -> Data Quality -> Findings -> Monitoring -> Final Decision

## Final Validation Decision

Decision: **RESTRICTED_USE**.

Supported use: transparent baseline one-day Gaussian VaR / ES reference, model comparison, and limited internal monitoring with visible caveats.

Restricted use: MR-001 99% Gaussian VaR must not be used as a standalone far-tail risk measure. 99% interpretation requires challenger context, v1.1 monitoring, data-quality gates, and high-volatility escalation. The latest monitoring snapshot is historical frozen-data evidence as of 2026-03-06, not live/current status.

## Architecture

```text
configs/                  # Data, model, validation, monitoring, stress configs
governance/               # Inventory, materiality, findings, remediation
src/market_risk_toolkit/  # Data, portfolio, risk, validation, DQ, monitoring code
data/artifacts/           # Deterministic CSV/JSON validation evidence
reports/                  # Executive summary, final report, monitoring report
tests/                    # Unit, integration, governance, and consistency tests
```

## Reproduce

```bash
python -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
pip install -r requirements.txt
pytest -q
```

Core tests are deterministic and do not require live yfinance access. The frozen V2 artifacts use a local development data cutoff rather than an open-ended market-data refresh.

## Reports and Artifacts

- [Executive summary](reports/executive_summary.md)
- [Full V2 validation report](reports/v2_validation_report.md)
- [Monitoring report](reports/monitoring_report.md)
- [Model inventory](governance/model_inventory.csv)
- [Findings registry](governance/findings.csv)
- [Remediation log](governance/remediation_log.csv)
- [Final validation decision JSON](data/artifacts/final_validation_decision.json)
- [Release metrics registry](data/artifacts/release_metrics.json)

## Limitations

- Educational portfolio project using public ETF proxies
- Project-level independent reference implementation, not organizational independence
- One-day horizon and daily adjusted-close data
- Fixed historical dataset and finite empirical tails
- Project-specific monitoring thresholds
- No real institutional approval authority
- No regulatory capital, live institutional use, or compliance claim
