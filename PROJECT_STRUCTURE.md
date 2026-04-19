# Project Structure

This repo is small enough that the important parts fit on one page.

## Top level

- `app.py`: Streamlit entry point.
- `mmf/`: package code for validation, scoring, suggestions, and UI helpers.
- `tests/`: unit and integration tests.
- `templates/`: starter YAML files for new metrics and packs.
- `examples/`: reusable sample packs for the app sidebar and docs.
- `case_studies/`: reconstructed real-world failures used to show MMF's scope.
- `analysis/`: notebooks and scripts for calibration and robustness work.
- `README.md`: product-level overview.
- `SCORING_METHODOLOGY.md`: scoring rules and rationale.

## Package layout

- `mmf/validator.py`: schema and structural checks.
- `mmf/scoring.py`: metric-level and pack-level scoring.
- `mmf/suggestions.py`: deterministic next-step suggestions.
- `mmf/mermaid.py`: strategy graph generation.
- `mmf/layout.py`, `mmf/components.py`, `mmf/sidebar.py`: Streamlit rendering helpers.
- `mmf/config.py`: default deductions, thresholds, and config validation.

## Tests

- `tests/test_validator.py`: validator behavior.
- `tests/test_scorer.py`: scoring contract and edge cases.
- `tests/test_suggestions.py`: deterministic suggestion text and priorities.
- `tests/test_integration.py`: end-to-end pack flow.
- `tests/test_mermaid.py`: strategy graph output.
- `tests/test_bayesian_scoring.py`: robustness layer checks.

Note: the repo now uses synthetic fixtures under `tests/fixtures/synthetic_packs/` for much of the scoring analysis. If you update docs or tests, check that the fixture paths still match reality.

## Quick commands

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

- New validation rule: update `mmf/validator.py` and add tests in `tests/test_validator.py`.
- New scoring rule: update `mmf/config.py`, `mmf/scoring.py`, and the relevant tests.
- New suggestion behavior: update `mmf/suggestions.py` and its tests.
- New example pack: add it under `examples/`. The sidebar prefers `generic_product_metric_pack.yaml`.
- New case study or analysis artifact: keep it under `case_studies/` or `analysis/`, not mixed into the app code.
