# AGENTS.md

This file is the primary operating contract for coding agents working in this
repository. Human instructions in the current conversation or issue override it.

## Mission

Build a small, dependable open-source testkit that finds and reduces
real-world side-effect failures in tool-using AI agents.

The product wedge is **commit-aware semantic fault testing + deterministic
outcome contracts + reduced counterexamples**. Preserve that wedge until user
evidence justifies expansion.

## Read before changing code

1. `README.md`
2. `TASKS.md`
3. `docs/PRODUCT_SPEC.md`
4. `docs/ARCHITECTURE.md`
5. `docs/TESTING_STRATEGY.md`
6. the relevant file under `docs/adr/`

## Non-negotiable product boundaries

- Do not turn the project into an agent framework, model gateway, trace SaaS,
  prompt playground, or broad LLM-evaluation platform.
- Do not introduce an LLM judge for an invariant that deterministic code can
  express.
- Do not require an API key, hosted account, or network access for core tests.
- Do not prescribe one exact agent trajectory when multiple safe trajectories
  reach the same valid outcome.
- Do not treat a generic transport timeout as equivalent to
  `timeout_after_commit`.
- Do not shrink a case without running its domain validity predicate.
- Do not execute arbitrary subprocesses, containers, or user code without a
  reviewed threat-model update.
- Do not silently collect telemetry.

## Architecture map

- `models.py`: versioned, JSON-only portable schemas.
- `faults.py`: operation occurrence tracking and commit-aware effects.
- `world.py` / `protocols.py`: adapter boundaries.
- `runner.py`: world lifecycle, agent execution, snapshots, contracts, bundles.
- `contracts.py`: deterministic, fail-closed oracles.
- `shrink.py`: strictly complexity-reducing, validity-preserving reduction.
- `artifacts.py`: stable local failure bundles.
- `pytest_plugin.py`: direct pytest helpers; domain logic stays normal Python.
- `agent_effects_pytest.py`: minimal auto-load shim that avoids eager core imports.
- `examples/refund.py`: executable reference specification, not disposable demo.

## Core invariants

Any change must preserve these unless an ADR explicitly supersedes them:

1. Portable models contain only JSON-compatible values.
2. A fault rule is unique by `(operation, occurrence)`.
3. `timeout_before` fires before `mark_committed()`.
4. `timeout_after_commit` can fire only after exactly one `mark_committed()`.
5. The runner snapshots both initial and final world state and closes the world.
6. Agent exceptions become a failed `TrialResult`, preserving final state.
7. Contracts fail closed when an oracle raises.
8. Shrink candidates must be strictly smaller and domain-valid.
9. Failure artifacts are local, versioned, inspectable, and deterministic except
   for creation timestamps.
10. The core suite runs without external services.

## Development commands

```bash
# Preferred
uv sync --extra dev
uv run pytest
uv run ruff check .
uv run ruff format --check .
uv run mypy
uv build

# Offline/minimal environment
PYTHONPATH=src pytest -q
python -m compileall -q src tests examples
PYTHONPATH=src python -m agent_effects.cli demo --agent naive --output /tmp/aet
PYTHONPATH=src python -m agent_effects.cli demo --agent idempotent
```

The naive demo is expected to exit `1`; the idempotent and reconciliation demos
must exit `0`.

## Task workflow

1. Select one unchecked task from `TASKS.md` whose dependencies are complete.
2. Restate its acceptance criteria in the branch/PR description.
3. Add or update a failing test before implementation when practical.
4. Make the smallest coherent change.
5. Run the full local validation matrix.
6. Update docs, schemas, changelog, and ADRs when behavior changes.
7. Mark only the completed task; do not mark adjacent speculative work.
8. Leave a concise handoff using `docs/agent/SESSION_CHECKLIST.md`.

## Coding standards

- Python 3.11+; strict type checking is the target.
- Public functions and extension points require docstrings and explicit types.
- Prefer immutable Pydantic models for portable data and small dataclasses for
  behavior objects.
- Keep core modules framework-neutral and asynchronous at I/O boundaries.
- Make injected faults deterministic from the case; no random global state.
- Prefer explicit errors over implicit fallback.
- Never catch `BaseException`; catch `Exception` only where the runner must
  preserve a result.
- Avoid optional dependencies in core imports.
- New schemas need a version string, round-trip tests, and migration notes.
- Every bug fix needs a minimal regression case or failure bundle fixture.

## Definition of done

A task is complete only when:

- acceptance criteria are demonstrably met;
- deterministic tests pass;
- property tests pass when the optional dependency is installed;
- lint, formatting, and strict typing pass in a normal connected environment;
- no generated caches, virtual environments, secrets, or large binaries are
  committed;
- public behavior and roadmap docs are updated;
- security/privacy consequences are documented;
- the change stays inside the product boundary.

## Escalate instead of guessing

Create an ADR or leave the task blocked when a decision would:

- change artifact/schema compatibility;
- add a runtime enforcement feature rather than a test feature;
- add hosted infrastructure;
- introduce model-based grading;
- run untrusted code;
- make the core depend on a specific agent framework;
- weaken a deterministic safety contract.
