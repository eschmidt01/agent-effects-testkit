# Architecture

## Overview

```text
                  ┌──────────────────────────┐
                  │ TestCase                 │
                  │ actor / goal / world     │
                  │ semantic fault schedule  │
                  └────────────┬─────────────┘
                               │
                        WorldFactory
                               │
                  ┌────────────▼─────────────┐
                  │ isolated World           │
                  │ state + tools + recorder │
                  │ FaultInjector            │
                  └───────┬──────────┬───────┘
                          │          │
                 AgentAdapter   state snapshots
                          │          │
                  ┌───────▼──────────▼───────┐
                  │ TrialRunner              │
                  │ agent result + trace     │
                  └────────────┬─────────────┘
                               │
                   deterministic Contracts
                               │
                  ┌────────────▼─────────────┐
                  │ TrialResult             │
                  │ pass / violations       │
                  └───────┬──────────┬───────┘
                          │          │
                     FailureStore  GreedyShrinker
                          │          │ reruns valid candidates
                          └────┬─────┘
                               ▼
                    portable failure bundle
```

## Layers

### Portable model layer

`models.py` contains immutable Pydantic models. Portable values use Pydantic's
named recursive JSON type, which prevents arbitrary objects from leaking into
artifacts. Every externally stored top-level model carries an explicit version.

Core schemas:

- `TestCase`
- `FaultRule`
- `TraceEvent`
- `AgentRun`
- `ContractViolation` / `ContractReport`
- `EvaluationContext`
- `TrialResult`
- `ShrinkReport`
- `LifecycleFailure`
- `FailureBundleManifest` / `BundleFile`

`TrialResult` makes unavailable initial state, final state, and agent output
explicit with nullable fields. It never substitutes an empty object for a stage
that did not complete.

### Pytest integration boundary

The distribution exposes `agent_effects_pytest.py` as the auto-loaded pytest
entry point. That shim imports only pytest and lazily imports `TrialRunner` when
the fixture is requested. This prevents plugin discovery from eagerly importing
the complete runtime before coverage, tracing, or application instrumentation
starts. `agent_effects.pytest_plugin` remains the explicit import location for
`assert_contracts`.

### Extension protocol layer

`protocols.py` deliberately defines small structural interfaces:

- `World`: `snapshot()`, `close()`, and an `EventRecorder`;
- `AgentAdapter`: execute one case against one world;
- `Contract`: evaluate one immutable context;
- `CaseReducer`: propose simplified cases;
- `WorldFactory`, `FailurePredicate`, and `CaseValidator` callables.

A framework integration belongs behind these protocols and an optional extra.

### Semantic fault layer

`FaultInjector` counts attempts per operation. `EffectScope` records the call and
may fail on entry (`timeout_before`) or after the operation explicitly calls
`mark_committed()` (`timeout_after_commit`).

```text
timeout_before:
  TOOL_CALL → FAULT

timeout_after_commit:
  TOOL_CALL → application mutation → COMMIT → FAULT
```

The application adapter owns the definition of the durable business commit. A
database transaction, provider receipt, event append, or durable task state can
all be valid commit boundaries. The testkit does not infer this from HTTP status.

### World layer

A world is an isolated test environment. The starter uses an in-memory refund
world, but future adapters may target a database transaction, Docker Compose,
LocalStack, a service simulator, or an HTTP sandbox.

World requirements:

- created from one `TestCase`;
- no cross-trial mutable state;
- deterministic snapshot representation;
- explicit cleanup;
- fault-aware operations;
- domain validity defined outside the world for shrinking.

### Runner layer

`TrialRunner` owns the lifecycle:

1. create world;
2. snapshot initial state;
3. run the agent, converting ordinary exceptions into `AgentRun(status="error")`;
4. snapshot final state;
5. evaluate contracts when the required values exist;
6. close the world exactly once;
7. construct an immutable result with primary and secondary lifecycle failures;
8. optionally persist an integrity-checked failure bundle without destroying the result if
   persistence fails.

World factories and world/agent methods may be synchronous or asynchronous.
Failures in creation, snapshots, execution, contract orchestration, cleanup, and
artifact generation have stable stages and categories. See
`RUNNER_LIFECYCLE.md`.

### Contract layer

Contracts are deterministic and side-effect free. A contract may validate:

- exact cardinality of a business effect;
- uniqueness by domain key rather than provider request ID;
- correct state transition and amount;
- no mutation without authorization/approval;
- absence of sensitive reads;
- required audit evidence;
- bounded retries or prohibited operations.

Contracts fail closed: an exception becomes `contract_error` rather than an
accidental pass.

### Shrinking layer

`GreedyShrinker` verifies the initial failure, then considers candidates from
ordered reducers. A candidate is evaluated only when:

- it differs from the current case;
- its JSON complexity is strictly lower;
- the domain validity predicate accepts it.

A candidate replaces the current case only when the caller's failure predicate
still holds. The caller usually preserves the original violation signature.

The greedy algorithm is intentionally small; delta debugging is the next major
algorithmic task.

### Artifact layer

`FailureStore` writes the original and reduced cases, independent snapshots,
faults, trace, violations, result, reproduction instructions, and optional shrink
report. `FailureBundle` verifies safe paths, size limits, SHA-256 hashes, schemas,
and cross-file identities before exposing typed payloads. Registered reproducers
rerun the reduced case without accepting arbitrary import paths from bundle
data. See `FAILURE_BUNDLE_SPEC.md`.

## Data and control boundaries

### Trusted

- test definitions and contract code;
- domain validity predicates;
- adapters reviewed as part of the application;
- synthetic fixtures in this repository.

### Potentially untrusted

- target agent code;
- tool inputs generated by a model;
- external service responses;
- production-derived state;
- third-party adapters and failure bundles.

The Python process is not a sandbox. See `THREAT_MODEL.md`.

## Concurrency

The alpha executes one agent trial in one event loop. Worlds may implement
internal concurrency, but the core does not yet generate schedules or control
interleavings. A future scheduler must make concurrency deterministic and
shrinkable rather than relying on timing sleeps.

## Versioning

- Python API: alpha semantic versioning.
- Case schema: `agent-effects.case/v1alpha1`.
- Result schema: `agent-effects.result/v1alpha1`.
- Failure bundle: `agent-effects.failure/v1alpha1`.

Breaking artifact changes require a new schema version and migration strategy.
