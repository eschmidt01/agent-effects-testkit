# Coding-agent session checklist

## Start

- [ ] Read `AGENTS.md` and relevant ADRs.
- [ ] Select exactly one task from `TASKS.md`.
- [ ] Confirm dependencies and current tests.
- [ ] Identify the product-boundary and security risks.

## During implementation

- [ ] Add a failing regression test where practical.
- [ ] Keep portable values JSON-only.
- [ ] Preserve deterministic, local operation.
- [ ] Keep optional framework dependencies isolated.
- [ ] Update docs when public behavior changes.
- [ ] Avoid unrelated cleanup.

## Validate

- [ ] `pytest`
- [ ] property tests with Hypothesis installed
- [ ] `ruff check .`
- [ ] `ruff format --check .`
- [ ] `mypy`
- [ ] `python -m compileall -q src tests examples`
- [ ] clean wheel/sdist build when packaging changed
- [ ] naive demo fails with expected signature
- [ ] robust demos pass

## Handoff template

```text
Task: AE-___ — title
Status: complete | partial | blocked

Changed:
- ...

Validation:
- command → result

Decisions:
- ...

Risks / unresolved:
- ...

Next:
- ...
```
