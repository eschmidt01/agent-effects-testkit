# Coding-agent implementation plan

## Objective

Turn the starter into a credible installable alpha while preserving the narrow
semantic side-effect testing thesis.

## Recommended sequence

### Phase 1: package integrity

1. Complete `AE-001` schema export.
2. Complete `AE-002` integrity-checked failure bundles.
3. Complete `AE-005` lifecycle hardening.
4. Complete `AE-006` release checks.

Do not begin framework integrations before this phase passes clean-build and
installed-wheel tests.

### Phase 2: shrinking quality

1. Add ddmin list reduction (`AE-003`).
2. Add fault/argument reduction (`AE-004`).
3. Add deterministic benchmark fixtures.
4. Record algorithmic decisions in an ADR.

### Phase 3: one real integration

Choose LangGraph first because public reports expose checkpoint/re-dispatch
failure patterns. Build a scripted-model test so CI remains credential-free.
Do not add three superficial adapters simultaneously.

### Phase 4: external evidence

Publish one concise reproduction tied to an upstream issue, invite maintainers to
review it, and collect setup friction. Use that evidence to reorder the backlog.

## Agent delegation map

Parallel work is safe only when file ownership does not overlap:

- **Core model agent:** schemas/versioning/tests.
- **Artifact agent:** bundle verification/spec/tests.
- **Shrinker agent:** reducers/benchmarks/ADR.
- **Docs/research agent:** source updates and examples, no core edits.
- **Integration agent:** optional module and version matrix after core gates.

One coordinating agent should integrate, run all checks, and resolve API drift.

## Completion evidence

Each agent handoff should include:

- task ID and acceptance criteria status;
- files changed;
- exact commands and outputs;
- unresolved risks;
- compatibility/security notes;
- next recommended task.
