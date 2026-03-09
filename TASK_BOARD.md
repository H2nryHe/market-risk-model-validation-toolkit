# TASK_BOARD.md
# Market Risk / Model Validation Toolkit

## Stage 0 — Repo Setup
### Goal
Create a clean, reproducible project skeleton.

### Tasks
- [x] Initialize repo structure
- [x] Add `src/`, `tests/`, `configs/`, `reports/`, `notebooks/`
- [x] Add `requirements.txt`
- [x] Add `.gitignore`
- [x] Add basic `README.md` stub
- [x] Add `PROJECT_SPEC.md`, `TASK_BOARD.md`, `AGENT_PROMPTS.md`

### Exit Criteria
- [ ] Repo installs in a fresh environment
- [x] Directory structure is stable
- [x] Basic import paths work

---

## Stage 1 — Data Ingestion & Validation
### Goal
Download and validate daily market data for selected instruments.

### Tasks
- [x] Select initial universe (e.g. SPY, QQQ, TLT, GLD)
- [x] Implement data download function
- [x] Save raw data snapshots
- [x] Standardize adjusted close / return-ready format
- [x] Implement checks:
  - [x] duplicate dates
  - [x] missing dates / missing values
  - [x] non-monotonic index
  - [x] extreme return flagging
  - [x] cross-asset alignment
- [x] Produce cleaned return panel

### Outputs
- [x] `data/raw/` snapshots
- [x] `data/processed/returns.parquet` or csv
- [x] validation summary table

### Exit Criteria
- [x] Clean aligned daily returns panel exists
- [x] Data quality checks run without manual intervention
- [x] Validation summary is saved

---

## Stage 2 — Portfolio Construction
### Goal
Build one or more simple portfolios from cleaned returns.

### Tasks
- [x] Define portfolio configs in yaml/json
- [x] Implement equal-weight portfolio
- [x] Implement optional custom-weight portfolio
- [x] Compute portfolio daily returns
- [x] Compute cumulative PnL / NAV series
- [x] Add summary stats:
  - [x] annualized return
  - [x] annualized volatility
  - [x] Sharpe (simple version)
  - [x] max drawdown

### Outputs
- [x] portfolio config file
- [x] portfolio return series
- [x] summary stats table
- [x] cumulative return plot

### Exit Criteria
- [x] At least one portfolio is reproducibly generated
- [x] Summary statistics are correct and tested

---

## Stage 3 — VaR / ES Engine
### Goal
Implement core risk measures.

### Tasks
- [x] Implement historical VaR
- [x] Implement parametric VaR
- [x] Implement historical ES
- [x] Implement parametric ES
- [x] Support 95% and 99%
- [x] Support rolling-window estimation
- [x] Add unit tests against small hand-check examples

### Outputs
- [x] risk metric module in `src/risk/`
- [x] time series of rolling VaR / ES
- [x] comparison plot across methods

### Exit Criteria
- [x] Historical and parametric VaR/ES run end-to-end
- [x] Tests pass for basic edge cases and sanity checks
- [x] Outputs are reproducible

---

## Stage 4 — Backtesting & Model Validation
### Goal
Evaluate predictive quality of VaR models.

### Tasks
- [x] Define exceedance logic
- [x] Compute exception counts
- [x] Implement Kupiec test
- [x] Implement Christoffersen conditional coverage test
- [x] Generate rolling validation summary
- [ ] Compare model performance by subperiod / regime
- [x] Plot exceedance markers against realized losses

### Outputs
- [x] backtesting table
- [x] exceedance plot
- [x] p-value summary
- [x] interpretation notes

### Exit Criteria
- [x] Backtesting works for all implemented VaR models
- [x] Statistical test results are interpretable
- [x] At least one conclusion is drawn about model failure modes

---

## Stage 5 — Stress Testing
### Goal
Run deterministic portfolio stress scenarios.

### Tasks
- [x] Design scenario schema
- [x] Create at least 3 scenarios:
  - [x] equity selloff
  - [x] rates shock
  - [x] cross-asset mixed shock
- [x] Implement scenario PnL application
- [x] Add contribution by asset
- [x] Save scenario result tables

### Outputs
- [x] scenario config files
- [x] scenario loss table
- [x] asset contribution table
- [x] bar chart or markdown summary

### Exit Criteria
- [x] All scenarios run from config
- [x] Scenario losses reconcile with portfolio weights and shocks
- [x] Results are included in report-ready format

---

## Stage 6 — Reporting
### Goal
Produce a professional validation-style report.

### Tasks
- [x] Create markdown report template
- [x] Summarize data coverage and assumptions
- [x] Summarize portfolio construction
- [x] Insert VaR / ES comparison
- [x] Insert backtesting results
- [x] Insert stress results
- [x] Add model limitations and next steps
- [x] Save one sample report to `reports/`

### Outputs
- [x] `reports/sample_validation_report.md`
- [x] figures in `data/artifacts/` or `reports/figures/`

### Exit Criteria
- [x] A reviewer can understand the project without reading source code
- [x] Report is resume-demo ready

---

## Stage 7 — README Polish
### Goal
Make the repo recruiter-friendly.

### Tasks
- [ ] Write concise project overview
- [ ] Add feature list
- [ ] Add setup instructions
- [ ] Add sample outputs / figures
- [ ] Add repo structure
- [ ] Add “Why this matters for market risk/model validation” section
- [ ] Add limitations / future work
- [ ] Add resume-ready bullets draft

### Exit Criteria
- [ ] README can be skimmed in under 2 minutes
- [ ] Technical depth is obvious
- [ ] Results are visible without opening notebooks

---

## Stage 8 — Testing & CI
### Goal
Make the repo look disciplined and reliable.

### Tasks
- [x] Add pytest suite
- [x] Add formatting/lint config
- [x] Add GitHub Actions CI
- [x] Ensure tests run on push
- [ ] Add badges to README if desired

### Exit Criteria
- [x] CI passes on clean clone
- [x] Core math functions are covered by tests
- [x] Repo looks production-minded

---

## Nice-to-Have Extensions
- [ ] risk contribution / marginal VaR
- [ ] filtered historical simulation
- [ ] EVT tail model
- [ ] CLI runner
- [ ] HTML report generation
- [ ] regime detection module
- [ ] factor-based stress testing

---

## MVP Definition
The MVP is complete when all of the following are true:

- [ ] Daily data ingestion and validation works
- [ ] At least one portfolio is built
- [ ] Historical and parametric VaR/ES are implemented
- [ ] Kupiec backtest is implemented
- [ ] At least 3 stress scenarios run
- [ ] One markdown report is generated
- [ ] Core tests pass

---

## Resume-Ready Outcome
By the end of MVP, the project should support bullets like:

- [ ] Built a Python market risk toolkit for multi-asset portfolios with rolling historical/parametric VaR and ES
- [ ] Implemented VaR backtesting using exception analysis and Kupiec coverage tests
- [ ] Designed deterministic stress scenarios and generated report-ready validation outputs
- [ ] Added data validation, configuration-driven workflows, and unit tests for reproducible risk analytics
