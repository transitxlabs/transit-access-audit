# Contributing

Thank you for contributing to transit-access-audit.

## Development setup

```bash
python -m venv .venv
source .venv/bin/activate
pip install -e ".[geo,dev]"
python scripts/build_fixtures.py
```

## Quality checks

```bash
ruff check src tests
mypy src
pyright src
pytest
python -m build
```

## Guidelines

- Keep core checks runnable without Java or network access.
- Label proximity metrics as **proximity coverage**, not walk accessibility.
- Map new checks to public standards in `research/03_standards.md` and `CHECK_SOURCES`.
- Do not commit agency GTFS snapshots without a recorded licence in `DATA_LICENSES.md`.
- Do not claim legal compliance; report data and standards conformance only.
