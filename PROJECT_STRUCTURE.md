# Project structure

## Top level

| Path | Contents |
|---|---|
| `app.py` | Streamlit entry point |
| `mmf/` | Validation, scoring, suggestions and UI helpers |
| `tests/` | Unit and integration tests |
| `templates/` | Starter YAML for new metrics and packs |
| `examples/` | Sample packs for the sidebar and docs |
| `case_studies/` | Rebuilt real-world failures that show MMF's scope |
| `analysis/` | Notebooks and scripts for calibration and sensitivity checks |
| `README.md` | Product overview |
| `SCORING_METHODOLOGY.md` | Scoring rules and reasoning |

## Package

| Module | Role |
|---|---|
| `mmf/validator.py` | Schema and structural checks |
| `mmf/scoring.py` | Metric and pack scoring |
| `mmf/suggestions.py` | Next-step suggestions |
| `mmf/mermaid.py` | Strategy graph |
| `mmf/layout.py`, `mmf/components.py`, `mmf/sidebar.py` | Streamlit rendering helpers |
| `mmf/config.py` | Default deductions, thresholds, config validation |

## Tests

| File | Covers |
|---|---|
| `tests/test_validator.py` | Validator behaviour |
| `tests/test_scorer.py` | Scoring contract and edge cases |
| `tests/test_suggestions.py` | Suggestion text and priorities |
| `tests/test_integration.py` | Full pack flow |
| `tests/test_mermaid.py` | Strategy graph output |
| `tests/test_bayesian_scoring.py` | Bayesian sensitivity layer |

Much of the scoring analysis uses synthetic fixtures in `tests/fixtures/synthetic_packs/`. When you change docs or tests, check the fixture paths still match.

## Commands

```bash
pip install -r requirements.txt
pip install -r requirements-dev.txt
streamlit run app.py
pytest
black app.py mmf/ tests/
flake8 app.py mmf/ tests/
mypy app.py mmf/
```

## Where to make changes

| Change | Where |
|---|---|
| New validation rule | `mmf/validator.py`, tests in `tests/test_validator.py` |
| New scoring rule | `mmf/config.py`, `mmf/scoring.py` and their tests |
| New suggestion | `mmf/suggestions.py` and its tests |
| New example pack | `examples/` (the sidebar defaults to `onboarding_measurement_ready.yaml`) |
| New case study or analysis | `case_studies/` or `analysis/`, kept out of the app code |
