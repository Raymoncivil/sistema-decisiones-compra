# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Purpose

Data mining and intelligent analysis system to optimize product buy/sell decisions. It analyzes historical data, rotation, and profitability to classify products as: buy / do not buy / use alternative, always including reasoning and a confidence level.

## Tech Stack

- **Python** — primary language
- **FastAPI** — REST API layer (`src/api/`)
- **Pandas, NumPy** — data manipulation and analysis
- **Scikit-learn** — ML models (explainable models only — no black boxes)
- **Matplotlib, Seaborn** — visualization and reports
- **SQLite** (dev) / **PostgreSQL** (prod)

## Planned Module Structure

```
src/
  data/            # ingestion and cleaning pipelines
  analysis/        # data mining and ML models
  recommendations/ # decision engine (buy / skip / alternative)
  api/             # FastAPI endpoints
  reports/         # report generation
```

## Development Setup (once implemented)

```bash
python -m venv .venv
.venv\Scripts\activate          # Windows
pip install -r requirements.txt

# Run API server
uvicorn src.api.main:app --reload

# Run a specific analysis script
python -m src.analysis.<module>

# Run tests
pytest
pytest tests/test_<module>.py   # single module
```

## Core Constraints

- **Always validate data** before analysis: check for nulls, outliers, and data type consistency.
- **Never delete original historical data** — transformations must produce new datasets, not overwrite source data.
- **Every recommendation must include**: the reasoning behind it and a confidence level (e.g., 0–1 score or low/medium/high).
- **Validate models on test data** before using them on real/production data.
- Only use explainable models (decision trees, linear models, rule-based systems, SHAP-explained ensembles) — not opaque black boxes.

## Expected Analysis Types

- Profitability analysis per product
- Product classification: buy / do not buy / alternative
- Product segmentation by behavior (rotation, margin, seasonality)
- Future demand prediction
