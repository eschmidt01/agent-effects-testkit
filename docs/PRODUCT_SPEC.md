# Product specification

## Product statement

Agent Effects: test the world your AI agent leaves behind.

Agent Effects Testkit is “property-based transaction testing for AI agents.” It
helps application and reliability engineers reduce the valid world and
fault schedule in which a tool-using agent leaves incorrect business state or
violates a deterministic policy.

## Target users

Primary:

- applied-AI/product engineers shipping agents that call side-effecting tools;
- platform engineers maintaining internal agent frameworks or MCP/tool layers;
- reliability and security engineers testing retries, permissions, and recovery;
- open-source framework maintainers converting production incidents into tests.

Secondary:

- domain engineers supplying world fixtures and business invariants;
- QA engineers integrating deterministic agent tests into CI;
- researchers studying stateful agent failures.

## Jobs to be done

1. Before a release, verify that an agent cannot duplicate a payment, refund,
   case, message, or infrastructure mutation after an ambiguous failure.
2. Verify that multiple valid recovery strategies reach the same safe outcome.
3. Check authorization and least-privilege access at the action boundary.
4. Turn a large flaky failure into a small deterministic regression fixture.
5. Compare model/framework versions against the same business contracts without
   rewriting the test harness.
6. Export a portable artifact that another engineer can inspect locally.
7. See the failed transaction, state diff, and reduced case in a self-contained
   local HTML report without executing a reproducer.

## Core user journey

1. Implement or select a `World` adapter with reset/snapshot support.
2. Place `mark_committed()` immediately after each durable business effect.
3. Create a `TestCase` containing actor, goal, valid world, and fault schedule.
4. Adapt the target agent to `AgentAdapter`.
5. Write deterministic contracts over state and trace.
6. Run the trial from pytest or CLI.
7. On failure, shrink the case and store the bundle in CI.
8. Promote the reduced case to a permanent regression test.

## Functional requirements for the alpha

### Portable cases

- JSON-only actor, goal, world, metadata, and fault rules.
- Explicit schema version.
- Deterministic ID and seed fields.
- Early validation of conflicting fault schedules.

### Semantic faults

- Target a named operation occurrence.
- Support timeout-before-commit.
- Support timeout-after-commit only after an explicit commit marker.
- Record call, commit, and fault events in order.
- Expose whether an ambiguous failure committed to the agent adapter.

### Trials

- Create one isolated world per trial.
- Snapshot initial and final state.
- Preserve final state when the agent raises.
- Close the world exactly once.
- Evaluate contracts after execution.
- Optionally persist local failure artifacts.
- Return typed primary and secondary lifecycle failures with explicit partial
  state when a runner stage cannot complete.

### Contracts

- Pure deterministic Python interface.
- May inspect case, agent result, initial/final state, and trace.
- Fail closed when the contract implementation crashes.
- Produce stable codes and structured details.
- Do not require an exact tool trajectory unless the behavior itself is the
  contract.

### Shrinking

- Caller supplies a failure predicate and domain validity predicate.
- Candidates must be strictly smaller.
- Initial failure is verified before reduction.
- Reducers are composable and framework-neutral.
- The report records every accepted reduction.

### Failure bundles

- Versioned, local, JSON-based files.
- Original case and result remain consistent.
- Reduced case is separate when present (stored as `minimized-case.json` for
  schema compatibility).
- Trace is independently stream-readable.
- No secrets are collected automatically.
- Every payload is content-addressed and cross-checked for internal consistency
  before use; unsigned manifests do not establish authenticity or provenance.
- A registered reproducer can rerun the reduced case without a model API.

## Non-functional requirements

- Python 3.11–3.13.
- Core tests require no model API or network.
- Public models round-trip through JSON.
- Optional dependencies do not import from core paths.
- Deterministic tests finish quickly enough for ordinary CI.
- Package supports wheel and source distribution.
- Error messages identify operation, occurrence, and commit position.
- The API is typed and documented.

## Product success measures

Technical:

- robust reference implementations pass all generated semantic fault cases;
- seeded runs reproduce exactly;
- reduced cases are materially smaller than discovered cases;
- no false failures from invalid generated worlds;
- failure bundles survive round-trip and verification.

Adoption:

- time to first useful contract under two hours;
- external CI use by at least two teams;
- at least one upstream framework issue gains an executable reproduction built
  with the testkit;
- community adapters do not force framework dependencies into core.

## Non-goals

See the README. Most importantly, the project is not responsible for executing
production transactions safely. It tests systems that must still implement
runtime idempotency, authorization, audit, and compensation.
