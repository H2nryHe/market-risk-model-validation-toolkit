# PROJECT_SPEC.md
# Market Risk / Model Validation Toolkit

## 1. Project Overview

This repository implements a practical market risk and model validation toolkit for liquid portfolios.
The goal is to simulate the workflow of a bank market risk / model risk team:

- ingest and clean market data
- construct simple portfolios
- compute risk measures
- validate model performance
- run stress scenarios
- generate concise risk reports

The toolkit is designed to showcase skills relevant to:
- Market Risk Quant
- Model Validation / Model Risk
- Quantitative Risk Analyst
- Risk Strats / Risk Analytics

This is not intended to be a production trading system.
It is a reproducible research and portfolio project emphasizing:
- transparent assumptions
- robust data checks
- correct implementation of standard risk metrics
- backtesting and model validation
- clear reporting

---

## 2. Objectives

The repo should answer the following questions:

1. How large is portfolio risk under different VaR / ES methodologies?
2. How well do these risk models perform out-of-sample?
3. Under what market regimes do they fail?
4. How sensitive is the portfolio to predefined stress scenarios?
5. How can we summarize results in a concise model validation memo?

---

## 3. Core Deliverables

### Deliverable A — Risk Engine
Implement portfolio risk estimation for:

- Historical VaR
- Parametric VaR
- Historical Expected Shortfall
- Parametric Expected Shortfall

Baseline horizon:
- 1-day horizon

Optional extension:
- 10-day horizon via square-root-of-time or block aggregation, with caveat discussion

Confidence levels:
- 95%
- 99%

---

### Deliverable B — Portfolio Layer
Support at least 2–3 simple portfolio constructions, for example:

- Equity ETF portfolio
- Rates proxy portfolio (e.g. TLT / IEF / SHY or futures proxy if clean data is available)
- Multi-asset portfolio (equity + bond + commodity proxy)

Each portfolio must include:
- weights
- daily returns
- rolling PnL
- summary statistics

---

### Deliverable C — Backtesting / Validation
Implement validation logic for VaR models:

- exception count
- Kupiec unconditional coverage test
- Christoffersen conditional coverage test
- rolling comparison across models
- regime analysis (calm vs stress periods)

Validation outputs should include:
- exceedance plots
- exception tables
- p-values and interpretation
- commentary on model weaknesses

---

### Deliverable D — Stress Testing
Implement at least 3 stress scenarios.

Examples:
- Equity selloff shock
- Rates up / rates down shock
- Volatility spike proxy
- Cross-asset stress scenario

Each scenario should produce:
- portfolio shock PnL
- contribution by asset / bucket
- scenario description and assumptions

---

### Deliverable E — Reporting
Produce a concise report artifact, such as:

- Markdown report
- HTML report
- notebook summary
- validation memo in markdown/PDF-ready format

Minimum report contents:
- data description
- portfolio construction
- model assumptions
- VaR / ES comparison
- backtesting results
- stress results
- model limitations
- final recommendation

---

## 4. Technical Scope

### In Scope
- Daily market data ingestion from public sources
- Return calculation and portfolio aggregation
- Standard VaR / ES implementations
- Standard VaR backtests
- Stress testing framework
- Reproducible CLI / notebook workflow
- Unit tests for core metrics
- Clean README with figures

### Out of Scope (for MVP)
- intraday risk
- derivatives Greeks engine
- full Monte Carlo XVA
- enterprise database integration
- real-time streaming risk
- regulatory capital replication in full production detail

---

## 5. Data

Preferred public data source:
- Yahoo Finance via yfinance or equivalent public source

Candidate instruments:
- SPY, QQQ, IWM
- TLT, IEF, SHY
- GLD, USO or other liquid proxies
- VIX proxy instruments if useful and reliable

Data frequency:
- daily

Minimum history:
- enough to include both calm and stress regimes
- ideally multiple years

Required data checks:
- missing values
- duplicated dates
- non-monotonic index
- suspicious return spikes
- alignment across assets

---

## 6. Methodology

### 6.1 Portfolio Returns
For a portfolio with weights w and asset return vector r_t:

portfolio return:
r_p,t = w' r_t

portfolio PnL can be modeled using:
- normalized notional = 1
or
- explicit notional input

---

### 6.2 Historical VaR
Use rolling historical window of returns and compute empirical quantiles.

Parameters:
- rolling window (e.g. 250 days)
- alpha = 95%, 99%

---

### 6.3 Parametric VaR
Assume portfolio returns are approximately normal over the chosen horizon.

Compute:
- rolling mean
- rolling volatility
- Gaussian quantile VaR

Also document limitations:
- tail underestimation
- regime instability
- non-normality

---

### 6.4 Expected Shortfall
Compute:
- historical ES from tail average
- parametric ES under Gaussian assumption

---

### 6.5 Backtesting
Compare realized next-day portfolio loss against predicted VaR.

Required tests:
- Kupiec unconditional coverage
- Christoffersen conditional coverage

Interpretation should be included in report:
- too many exceptions
- too few exceptions
- clustered exceptions
- model instability during crisis windows

---

### 6.6 Stress Testing
Create deterministic scenario shocks and apply them to current portfolio.

Example format:
- SPY: -8%
- QQQ: -10%
- TLT: +2%
- GLD: +1%

Allow scenario definitions through config files.

---

## 7. Evaluation Criteria

The project is successful if it demonstrates:

1. Correct implementation of core risk metrics
2. Clean and reproducible pipeline
3. Sensible portfolio construction and assumptions
4. Meaningful backtesting and interpretation
5. Professional reporting quality

---

## 8. Suggested Repository Structure

.
├── README.md
├── PROJECT_SPEC.md
├── TASK_BOARD.md
├── AGENT_PROMPTS.md
├── requirements.txt
├── configs/
│   ├── portfolios/
│   └── stress_scenarios/
├── data/
│   ├── raw/
│   ├── processed/
│   └── artifacts/
├── notebooks/
│   ├── 01_data_exploration.ipynb
│   ├── 02_portfolio_construction.ipynb
│   ├── 03_var_es_models.ipynb
│   ├── 04_backtesting.ipynb
│   └── 05_stress_testing.ipynb
├── src/
│   ├── data/
│   ├── portfolio/
│   ├── risk/
│   ├── validation/
│   ├── stress/
│   ├── reporting/
│   └── utils/
├── tests/
│   ├── test_returns.py
│   ├── test_var.py
│   ├── test_es.py
│   ├── test_backtests.py
│   └── test_stress.py
└── reports/
    └── sample_validation_report.md

---

## 9. MVP Milestones

### MVP
- load and clean daily data
- construct 1 portfolio
- historical and parametric VaR/ES
- Kupiec backtest
- 3 stress scenarios
- 1 markdown report
- basic tests

### V1
- multiple portfolios
- Christoffersen test
- rolling regime comparison
- richer report figures
- CLI entry points

### V2
- factor decomposition
- EVT or filtered historical simulation
- Monte Carlo extension
- risk contribution / marginal VaR
- lightweight dashboard

---

## 10. Resume Value Proposition

This project should let the candidate credibly claim:

- built a reproducible market risk analytics toolkit in Python
- implemented historical/parametric VaR and ES with rolling-window backtesting
- performed Kupiec and Christoffersen validation tests across market regimes
- designed scenario stress testing and report generation for multi-asset portfolios
- developed data validation, testing, and reporting infrastructure resembling a model risk workflow

---

## 11. Non-Negotiables

The repo must have:
- clean README
- reproducible setup
- no fake results
- explicit assumptions
- at least one real output artifact
- figures and interpretation, not just code
- tests for the core formulas

The repo must avoid:
- overclaiming production readiness
- hand-wavy math
- unverified performance claims
- messy notebook-only implementation without reusable modules