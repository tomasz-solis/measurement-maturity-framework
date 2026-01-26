# Contributing

## What to Commit

**Always commit:**
- Source code (`mmf/`, `tests/`, `app.py`)
- Configuration (`.github/`, `pytest.ini`, `requirements*.txt`)
- Documentation (`README.md`, `docs/`, `PROJECT_STRUCTURE.md`)
- Templates (`templates/`)
- Examples (`examples/`)

**Never commit:**
- Virtual environments (`venv/`)
- Python cache (`__pycache__/`, `*.pyc`)
- Secrets (`.env`)
- OS files (`.DS_Store`)
- Temporary files (`scratch/`, `tmp/`)

See [.gitignore](.gitignore) for the complete list.

## Development Workflow

**1. Set up environment:**
```bash
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
pip install -r requirements.txt
```

**2. Make changes:**
- Edit source files
- Add tests for new features
- Update documentation

**3. Run quality checks:**
```bash
# Format code
black mmf/ tests/ app.py

# Check style
flake8 mmf/ tests/ app.py

# Type check
mypy mmf/

# Run tests
pytest -v
```

**4. Commit:**
```bash
git add <files>
git commit -m "description"
git push
```

## CI/CD

The `.github/workflows/` directory contains GitHub Actions that run automatically:

- **test.yml** - Runs pytest on Python 3.10, 3.11, 3.12 (Ubuntu + macOS)
- **lint.yml** - Runs black, flake8, mypy for code quality

These run on every push and pull request. Fix any failures before merging.

## Project Structure

See [PROJECT_STRUCTURE.md](PROJECT_STRUCTURE.md) for detailed explanation of directories and files.
