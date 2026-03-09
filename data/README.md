# Data

This directory is split into:

- `raw/` for immutable source snapshots
- `processed/` for cleaned, aligned analysis datasets
- `artifacts/` for plots, tables, and intermediate outputs

Generated contents are ignored by git except for directory placeholders.

Current Stage 1 pipeline outputs:

- `raw/adjusted_close_raw.csv`
- `raw/download_metadata.json`
- `processed/adjusted_close.csv`
- `processed/returns.csv`
- `artifacts/data_validation_summary.json`
- `artifacts/data_validation_flags.csv`
