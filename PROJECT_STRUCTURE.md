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
├── test_validator.py               # Validator tests (15+ test classes)
├── test_scorer.py                  # Scorer tests (8+ test classes)
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
└── README.md                       # Examples overview
```

## Documentation

```
docs/                               # Framework documentation
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
- The app will automatically discover `*.yaml` files there

**Adding new validation logic:**
- Edit `mmf/validator.py`
- Add tests to `tests/test_validator.py`

**Changing scoring rules:**
- Edit `mmf/config.py` (deductions, thresholds)
- Update `docs/SCORING_METHODOLOGY.md` with rationale
- Add tests to `tests/test_scorer.py`

**Company-specific content:**
- create `examples/yourcompany/`
- Can be excluded from public repo by uncommenting in `.gitignore`
