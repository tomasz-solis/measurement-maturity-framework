# Contributing

Keep changes small, tested and easy to read.

## Setup

```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
pip install -r requirements-dev.txt
```

## Before calling work done

```bash
black app.py mmf/ tests/
flake8 app.py mmf/ tests/
mypy app.py mmf/
pytest
```

## Notes

- Changing scoring rules means updating the tests and `SCORING_METHODOLOGY.md`.
- Changing templates or examples means checking the sidebar still points to the right files.
- Reusable examples go in `examples/`. One-off analysis goes in `analysis/` or `case_studies/`.
- Check `.gitignore` before adding generated files. Notebook output and local caches pile up here.

Repo map: [PROJECT_STRUCTURE.md](PROJECT_STRUCTURE.md).
