# Contributing

Thanks for contributing to **Synaptic**.

## Ground rules
- Keep changes **small and reviewable**.
- Preserve **on-disk contracts** (JSONL + SQLite schema) unless a version bump is included.
- Prefer **local-first** defaults (no remote calls, no telemetry).
- Add or update a **smoke test** when behavior changes.

## Development setup
```bash
python -m venv .venv
source .venv/bin/activate  # (Windows: .venv\Scripts\activate)
python -m pip install -U pip
python -m pip install -e .
python scripts/smoke.py
```

## Pull requests
- Explain **what** and **why**.
- Include a brief **risk** note (what could break).
- If you touch storage/index formats, update:
  - `docs/SCHEMAS.md`
  - `CHANGELOG.md`
  - and bump version in `pyproject.toml` + `synaptic/__init__.py`

## Style
- Python >= 3.10
- Keep dependencies minimal.
- Avoid giant refactors unless discussed first.
