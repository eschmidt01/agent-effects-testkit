# Contributing

Thank you for helping make side-effecting agents safer to test.

## Before opening code

- Read `AGENTS.md`, `docs/PRODUCT_SPEC.md`, and the relevant ADR.
- Search existing issues and `TASKS.md`.
- For substantial behavior or schema changes, open a design issue first.
- Keep contributions within the narrow testing boundary.

## Setup

```bash
uv sync --extra dev
uv run pytest
uv run ruff check .
uv run ruff format --check .
uv run mypy --strict src tests
```

A minimal offline test is:

```bash
PYTHONPATH=src pytest -q
python -m compileall -q src tests examples scripts
```

## Pull requests

A pull request should:

- solve one coherent problem;
- include deterministic regression tests;
- add property tests when input-space exploration matters;
- preserve framework neutrality in core;
- update docs and changelog for public behavior;
- explain privacy, security, and compatibility consequences;
- include before/after failure bundle examples for shrinker changes.

## Design expectations

- Contracts specify valid outcomes, not one exact trace.
- Faults describe semantic timing at the business operation boundary.
- Shrinkers only accept strictly smaller, domain-valid cases.
- Portable artifacts contain JSON-compatible data and no secrets.
- Optional framework integrations live behind extras and isolated modules.
- Production incident-derived fixtures must be synthetic and source-attributed.

## Commit messages

Use an imperative summary under 72 characters where practical. Prefixes such as
`feat:`, `fix:`, `docs:`, `test:`, and `refactor:` are welcome but not required.

## Compatibility

Changes to `v1alpha1` schemas require a migration note. Breaking public API
changes during alpha are allowed only with tests and changelog documentation.
