# Contributing

Keep changes small, tested, and easy to read.

## Local setup

```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
pip install -r requirements-dev.txt
```

## Before you call work done

```bash
black app.py mmf/ tests/
flake8 app.py mmf/ tests/
mypy app.py mmf/
pytest
```

## A few repo-specific notes

- If you change scoring rules, update both the tests and `SCORING_METHODOLOGY.md`.
- If you change templates or examples, make sure the app sidebar still points to the right files.
- Keep reusable examples in `examples/`. Put one-off analysis material in `analysis/` or `case_studies/`.
- Check `.gitignore` before adding new generated files. This repo already tends to collect notebook output and local cache files.

For a quick map of the repo, see [PROJECT_STRUCTURE.md](PROJECT_STRUCTURE.md).
