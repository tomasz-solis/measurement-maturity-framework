# Project Structure

## Core Files

```
measurement-maturity-framework/
├── app.py                          # Main Streamlit application
├── requirements.txt                # All dependencies (production + dev tools)
├── pytest.ini                      # Test configuration
├── README.md                       # Main documentation
└── .gitignore                      # Git ignore rules
```

## Source Code

```
mmf/                                # Core framework library
├── __init__.py
├── config.py                       # Scoring configuration
├── validator.py                    # YAML validation logic
├── scoring.py                      # Maturity scoring
├── suggestions.py                  # Improvement suggestions
├── mermaid.py                      # Diagram generation
└── streamlit_mermaid.py            # Streamlit integration
```

## Tests

```
tests/                              # Test suite
├── __init__.py
├── test_validator.py               # Validator tests
├── test_scorer.py                  # Scorer tests
├── test_suggestions.py             # Suggestion tests
├── test_integration.py             # End-to-end pipeline tests
├── test_mermaid.py                 # Strategy tree tests
└── fixtures/                       # Test data
    ├── minimal_pack.yaml
    ├── empty_pack.yaml
    └── invalid_pack.yaml
```

## Templates and Examples

```
templates/                          # Starter templates
├── metric_template.yaml            # Single metric template
└── metric_pack_template.yaml       # Full pack template

examples/                           # Example metric packs
├── README.md                       # Examples overview
└── generic_product_metric_pack.yaml # Generic sample pack
```

## Documentation

```
docs/                               # Framework documentation
├── README.md                       # Docs index / navigation
└── SCORING_METHODOLOGY.md          # Detailed scoring rationale
```

## CI/CD

```
.github/                            # GitHub Actions workflows
└── workflows/
    ├── test.yml                    # Run tests on push/PR
    └── lint.yml                    # Code quality checks
```

**What to commit:**
- Commit `.github/` - These are your CI/CD automation workflows
- They run automatically on GitHub when you push code
- test.yml: Runs pytest on Python 3.10, 3.11, 3.12
- lint.yml: Runs black, flake8, mypy for code quality

## Ignored Files

These are in `.gitignore` and should NOT be committed:
- `venv/` - Virtual environment (local only)
- `__pycache__/` - Python bytecode cache
- `.DS_Store` - macOS metadata
- `.env` - API keys and secrets
- `scratch/`, `tmp/` - Temporary files

---

## Quick Reference

**Install dependencies:**
```bash
pip install -r requirements.txt              # All dependencies (includes dev tools)
```

**Run the app:**
```bash
streamlit run app.py
```

**Run tests:**
```bash
pytest                              # All tests
pytest tests/test_validator.py     # Specific test file
pytest -v                           # Verbose output
```

**Code quality:**
```bash
black mmf/ tests/                   # Format code
flake8 mmf/ tests/                  # Lint code
mypy mmf/                           # Type check
```

---

## What Goes Where

**Adding a new metric pack example:**
- Add to `examples/` directory
- The app prefers `generic_product_metric_pack.yaml` for the sidebar download
- If that file is missing, it falls back to the first `*.yaml` file it finds

**Adding new validation logic:**
- Edit `mmf/validator.py`
- Add tests to `tests/test_validator.py`

**Changing scoring rules:**
- Edit `mmf/config.py` (deductions, thresholds)
- Update `docs/SCORING_METHODOLOGY.md` with rationale
- Add tests to `tests/test_scorer.py`

**Private examples:**
- Keep reusable examples at the top level of `examples/`
- If you need local company-specific packs, place them under a gitignored path and keep them out of the canonical docs
