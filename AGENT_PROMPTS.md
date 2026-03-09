# AGENT_PROMPTS.md
# Market Risk / Model Validation Toolkit

## Stage 0 Prompt — Repo Setup
You are helping build a GitHub portfolio project called **Market Risk / Model Validation Toolkit**.

Goal:
Create the initial repository skeleton for a Python project that showcases bank-style market risk and model validation work.

Requirements:
- Create a clean repo structure with `src/`, `tests/`, `configs/`, `reports/`, `notebooks/`, and `data/` subfolders
- Add a `requirements.txt`
- Add a practical `.gitignore`
- Add placeholder files for `README.md`, `PROJECT_SPEC.md`, `TASK_BOARD.md`, `AGENT_PROMPTS.md`
- Keep the codebase modular and recruiter-friendly
- Do not implement business logic yet unless needed for import sanity

Output:
- Show the proposed directory tree
- Create the initial files with concise placeholder content
- Explain any important setup choices briefly

Definition of done:
- The repo is ready for incremental implementation
- A fresh Python environment can install dependencies cleanly
- The structure looks like a serious quantitative analytics project

---

## Stage 1 Prompt — Data Ingestion & Validation
Continue building the **Market Risk / Model Validation Toolkit** repo.

Goal:
Implement a robust daily market data ingestion and validation pipeline.

Requirements:
- Use a public source such as `yfinance`
- Start with a small liquid universe such as `SPY`, `QQQ`, `TLT`, `GLD`
- Download daily adjusted close data
- Save raw snapshots locally
- Build a cleaned aligned return panel
- Implement validation checks for:
  - duplicate dates
  - missing values
  - non-monotonic index
  - suspicious return spikes
  - cross-asset date alignment
- Save a validation summary artifact

Coding requirements:
- Keep logic in reusable modules under `src/data/`
- Avoid notebook-only logic
- Use clear function boundaries and docstrings
- Prefer pandas-based implementation

Output:
- New/updated source files
- Example validation output
- Brief explanation of design choices

Definition of done:
- Clean aligned daily returns are produced reproducibly
- Validation checks run automatically
- The pipeline can support downstream risk modeling

---

## Stage 2 Prompt — Portfolio Construction
Continue the repo.

Goal:
Implement portfolio construction on top of the cleaned returns panel.

Requirements:
- Support at least:
  - equal-weight portfolio
  - custom-weight portfolio from config
- Compute:
  - portfolio daily returns
  - cumulative returns
  - annualized return
  - annualized volatility
  - Sharpe ratio
  - max drawdown
- Store portfolio configs in `configs/portfolios/`
- Save summary outputs and at least one figure

Coding requirements:
- Put logic under `src/portfolio/`
- Add tests for basic return aggregation and summary statistics
- Keep APIs simple and explicit

Output:
- Portfolio module
- Example config
- One sample portfolio result table
- One cumulative return plot

Definition of done:
- At least one portfolio can be built end-to-end from cleaned returns
- Summary stats are correct and readable
- The results are report-ready

---

## Stage 3 Prompt — VaR / ES Engine
Continue the repo.

Goal:
Implement core market risk metrics for portfolio returns.

Requirements:
- Implement:
  - historical VaR
  - parametric VaR
  - historical ES
  - parametric ES
- Support confidence levels 95% and 99%
- Support rolling-window estimates
- Use sensible defaults such as a 250-day window
- Return results in a clean tabular format
- Produce at least one comparison plot

Coding requirements:
- Put logic under `src/risk/`
- Add unit tests using small synthetic inputs where expected values are easy to check
- Keep formulas transparent and well-documented
- Explicitly note model assumptions and limitations in comments/docstrings where appropriate

Output:
- Risk metric implementation
- Tests
- Example rolling VaR/ES outputs
- Comparison figure

Definition of done:
- Historical and parametric VaR/ES run on a sample portfolio
- Tests pass
- Outputs are suitable for validation/backtesting

---

## Stage 4 Prompt — Backtesting & Validation
Continue the repo.

Goal:
Implement VaR backtesting and model validation.

Requirements:
- Define realized loss vs predicted VaR exceedance logic
- Compute exception counts
- Implement:
  - Kupiec unconditional coverage test
  - Christoffersen conditional coverage test
- Produce comparison tables across VaR models
- Produce at least one exceedance plot
- Add concise interpretation text or comments about what the results mean

Coding requirements:
- Put logic under `src/validation/`
- Keep the statistical test implementation readable
- Add tests or sanity checks where possible
- Make output suitable for inclusion in a validation memo

Output:
- Validation module
- Table of exception stats and p-values
- Exceedance visualization
- Short written interpretation

Definition of done:
- Backtesting works for all implemented VaR models
- Statistical output is interpretable
- The repo now demonstrates true model validation rather than just risk calculation

---

## Stage 5 Prompt — Stress Testing
Continue the repo.

Goal:
Implement deterministic scenario stress testing.

Requirements:
- Design a config-driven scenario framework
- Add at least 3 scenarios, such as:
  - equity selloff
  - rates shock
  - mixed cross-asset stress
- Compute portfolio PnL under each scenario
- Show asset-level contributions
- Save results in report-friendly tables

Coding requirements:
- Put logic under `src/stress/`
- Put scenario definitions under `configs/stress_scenarios/`
- Keep the scenario engine simple, auditable, and easy to extend

Output:
- Scenario config files
- Stress testing module
- Example stress result tables
- One figure or concise markdown summary

Definition of done:
- All scenarios run from config
- PnL outputs reconcile correctly
- Stress results are ready for a final report

---

## Stage 6 Prompt — Reporting
Continue the repo.

Goal:
Create a concise but professional market risk / model validation report.

Requirements:
- Produce a markdown report in `reports/sample_validation_report.md`
- Include:
  - project objective
  - data and portfolio description
  - VaR / ES methodology
  - backtesting results
  - stress testing results
  - limitations
  - next steps
- Reference generated figures/tables where appropriate
- Write in a professional, quantitative style

Important:
- Do not overclaim production readiness
- Be explicit about assumptions
- Keep the report readable by a recruiter or quant interviewer

Output:
- The completed markdown report
- Any linked figures or tables needed by the report

Definition of done:
- Someone can understand the full project from the report alone
- The report is resume- and interview-ready

---

## Stage 7 Prompt — README Polish
Continue the repo.

Goal:
Turn the repository into a strong GitHub portfolio piece.

Requirements:
- Write a polished `README.md`
- Include:
  - one-paragraph project summary
  - why the project matters for market risk / model validation roles
  - feature list
  - repo structure
  - setup instructions
  - sample outputs / figures
  - limitations and future work
- Add a short section with resume-ready bullet ideas

Important:
- Optimize for recruiter skimability
- Make the business relevance obvious
- Keep it concrete and not generic

Output:
- Updated README
- Suggested screenshots/figures if helpful

Definition of done:
- The repo looks mature and intentional
- A recruiter can understand the value in under two minutes

---

## Stage 8 Prompt — Testing & CI
Continue the repo.

Goal:
Add engineering discipline and reproducibility.

Requirements:
- Add pytest coverage for core modules
- Add lint/format tooling if appropriate
- Add GitHub Actions CI to run tests on push
- Ensure the project works on a clean environment

Important:
- Keep CI minimal but real
- Prioritize reliability over complexity

Output:
- Test files
- CI workflow
- Brief explanation of what is covered and why

Definition of done:
- Tests pass locally and in CI
- The repo looks like a real quantitative engineering project

---

## Final Integration Prompt
You are now at the integration stage for **Market Risk / Model Validation Toolkit**.

Goal:
Review the repository as a whole and make it portfolio-ready.

Tasks:
- Check consistency across modules, configs, tests, notebooks, and reports
- Remove dead code and redundant files
- Ensure file names and APIs are coherent
- Ensure the README matches actual outputs
- Ensure the report references real generated artifacts
- Confirm that the project supports strong resume bullets for market risk / model validation roles

Output:
- A concise repo review
- A list of final fixes applied
- A list of any remaining limitations honestly stated

Definition of done:
- The repository is coherent, reproducible, and ready to show employers