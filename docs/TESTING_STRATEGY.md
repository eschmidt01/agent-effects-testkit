# Testing strategy

## Goals

The suite must prove semantic correctness, determinism, portability, and useful
shrinking. High test counts are not enough if worlds are invalid or oracles are
weak.

## Test layers

### Unit tests

Cover:

- portable model validation and JSON round trips;
- operation occurrence counting;
- before/after-commit event order;
- contract composition and fail-closed behavior;
- reducer candidate generation;
- artifact layout and loading;
- CLI exit codes and messages.

### Scenario tests

The refund domain is an executable specification:

- naive retry duplicates under lost acknowledgement;
- stable idempotency passes all initial fault modes;
- reconciliation passes through a different trace;
- unauthorized/unapproved cases do not mutate state;
- sensitive overreading fails despite correct operational state.

### Property-based tests

With the Hypothesis extra installed, generate combinations of:

- fault mode;
- approval and authorization state;
- irrelevant records;
- later: retries, existing effects, duplicate events, and concurrency schedules.

Every generated world must satisfy its validity predicate before execution.
Robust implementations should satisfy contracts for the full generated space.

### Shrinker tests

A shrinker test must establish:

1. the original case fails;
2. irrelevant state or faults exist;
3. the reduced case retains the target signature;
4. the reduced case is valid;
5. every accepted step strictly reduces complexity;
6. rerunning the reduced case reproduces deterministically.

### Adapter contract tests

Every external adapter should pass a shared conformance suite:

- independent world per trial;
- stable initial/final snapshots;
- close called once;
- faults target the intended occurrence;
- no secrets in portable data;
- network failures map to explicit runner errors;
- deterministic scripted-agent path for CI.

### Mutation and negative testing

Add deliberate broken implementations and prove contracts catch them. Useful
mutants include:

- changing the idempotency key on retry;
- omitting authorization at execution;
- accepting a timeout-after-commit without reconciliation;
- duplicate event processing;
- overreading sensitive fields;
- returning success without a state mutation;
- state mutation with an error response.

## Local commands

```bash
pytest
pytest --cov=agent_effects --cov-report=term-missing
pytest tests/test_hypothesis_refund.py
ruff check .
ruff format --check .
mypy --strict src tests
python -m compileall -q src tests examples
```

## CI matrix

- Python 3.11, 3.12, 3.13: deterministic and property suites.
- One job: lint, formatting, strict typing.
- One job: build wheel/sdist and install them into a clean environment.
- One job: run examples from installed distributions, not source checkout.
- Future adapter jobs should pin upstream minimum/current versions.

## Release gates

- no skipped deterministic tests;
- optional skips clearly identify missing extras;
- core branch coverage at least 90% before stable release;
- no warnings from pytest, build, or package metadata;
- naive demo fails for the expected signature;
- robust demos pass;
- reduced bundle verifies and reproduces;
- docs commands are exercised in CI where practical.
