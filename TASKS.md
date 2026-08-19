# Agent-ready task backlog

This backlog is ordered to turn the starter into a credible public alpha without
losing the product wedge. A coding agent should take one unchecked task at a
time and satisfy every acceptance criterion.

## P0 — alpha hardening

### AE-001: Export and validate portable JSON Schemas

**Goal:** Make cases, results, fault rules, traces, shrink reports, and bundle
manifests usable across languages and CI systems.

**Acceptance criteria**

- [x] `agent-effects schema export --output <dir>` writes stable JSON Schema
  files for every public portable model.
- [x] Schema `$id` values contain the existing `v1alpha1` version.
- [x] A test validates example JSON against the exported schemas.
- [x] `docs/SCHEMA_VERSIONING.md` defines additive vs. breaking changes.
- [x] No generated schema is imported at runtime by the Python core.

### AE-002: Add a first-class reduced reproduction API

**Goal:** Make a failure bundle directly reusable as a pytest regression.

**Acceptance criteria**

- [x] `FailureBundle` loads and validates `manifest.json`, original case,
  reduced case, result, trace, and shrink report.
- [x] `agent-effects bundle verify <path>` checks hashes and cross-file IDs.
- [x] The bundle includes a deterministic content manifest with SHA-256 hashes.
- [x] A test corrupts each payload type and proves verification fails closed.
- [x] Existing alpha results remain readable through `load_result`; strict bundle
  verification returns an explicit regeneration error for hashless alpha bundles.

### AE-003: Replace greedy list removal with delta debugging

**Goal:** Reduce large record collections in logarithmically fewer evaluations.

**Acceptance criteria**

- [x] Implement chunk-removal/ddmin for JSON lists.
- [x] Keep the current `CaseReducer` protocol backward compatible.
- [x] Never evaluate a non-smaller or invalid case.
- [x] A benchmark fixture with 1,000 noise records shrinks to zero in fewer than
  80 trial evaluations.
- [x] Determinism is tested across repeated runs.

### AE-004: Shrink fault schedules and operation arguments

**Goal:** Reduce not only world records but also fault occurrence and call data.

**Acceptance criteria**

- [x] Reducers can remove unrelated faults and lower an occurrence number only
  when the failure persists.
- [x] Add an opt-in reducer for domain-declared goal/actor fields.
- [x] Reducers cannot mutate reserved schema/version fields.
- [x] The failure signature and domain validity predicate remain mandatory.
- [x] The refund example proves an extra unrelated fault is removed.

### AE-007: Public-alpha onboarding workflow

**Goal:** Let a new engineer install, generate, run, reduce, verify, and
reproduce a deterministic side-effect failure without reading internals.

**Acceptance criteria**

- [x] `agent-effects init` generates a guarded passing starter project.
- [x] The explicit `lost-ack` template demonstrates failure then stable-idempotency success.
- [x] Contract helpers cover recurring state and trace invariants with stable IDs.
- [x] Onboarding, commit-boundary, contract, signature, shrinking, bundle, and
  troubleshooting documentation builds under MkDocs strict mode.
- [x] A clean-room script exercises the workflow using only the built wheel.
- [ ] An external engineer independently completes and times the quickstart.

### AE-005: Runner lifecycle hardening

**Goal:** Preserve useful results when snapshots, contracts, or cleanup fail.

**Acceptance criteria**

- [x] World initialization, initial snapshot, final snapshot, and close failures
  have distinct deterministic violation codes.
- [x] Cleanup is attempted exactly once.
- [x] A close failure never hides an already recorded agent exception.
- [x] Timing uses a test-injectable monotonic clock.
- [x] Cancellation behavior is documented and tested.

### AE-006: Release-quality static checks

**Acceptance criteria**

- [x] Ruff check and format pass.
- [x] Strict mypy passes without `type: ignore` in public core modules.
- [x] Branch coverage is at least 90% for core modules.
- [ ] Python 3.11, 3.12, and 3.13 pass in CI.
- [x] `uv build` produces installable sdist and wheel artifacts.

### AE-008: Initial public repository preparation

**Goal:** Make the validated candidate safe to import into a public repository
without claiming remote-CI or release success.

**Acceptance criteria**

- [x] Reduction reports state the participating reducers, validity predicate,
  budgets, exhaustion flags, target signature, and precise local guarantee.
- [x] Source-control policy retains schemas and one synthetic bundle fixture
  while excluding builds, caches, environments, and raw validation output.
- [x] Secret/path/symlink/size/direct-license hygiene checks are documented.
- [x] Issue forms, least-privilege CI, Dependabot, and voluntary alpha-feedback
  assets are present.
- [x] Remote-release and external-onboarding procedures are documented.
- [x] A proposed LangGraph ADR exists without integration code or core dependency.
- [x] The audited source is captured in one initial local import commit.
- [ ] The exact candidate commit passes an observable GitHub Actions run.
- [ ] The passing commit is tagged `v0.1.0a1` and published as an authorized
  GitHub prerelease.

## P1 — real framework adoption

### AE-101: LangGraph integration example

Build a separately optional integration that executes an existing LangGraph
agent against an instrumented world without importing LangGraph from core.

**Acceptance criteria**

- [ ] Example reproduces a checkpoint/retry side-effect replay.
- [ ] Stable-idempotency and reconciliation implementations both pass.
- [ ] Cancellation and long-running tool behavior are covered.
- [ ] Dependency is isolated behind an extra and separate module.
- [ ] Upstream version matrix is documented.

### AE-102: OpenAI Agents SDK integration example

**Acceptance criteria**

- [ ] Wrap tool execution without modifying the application agent prompt.
- [ ] Preserve tool arguments and actor/session correlation in trace events.
- [ ] Test pre-execution authorization denial and timeout-after-commit.
- [ ] No OpenAI credential is needed for deterministic CI; use a scripted model
  or adapter fixture.

### AE-103: CrewAI integration example

**Acceptance criteria**

- [ ] Reproduce task retry after a committed side effect.
- [ ] Demonstrate a reduced duplicate-email or duplicate-payment case.
- [ ] Keep integration code out of core imports.

### AE-104: OpenTelemetry trace import

**Goal:** Reuse production traces as candidate cases without becoming an
observability vendor.

**Acceptance criteria**

- [ ] Import the relevant OpenTelemetry GenAI/tool spans into `TraceEvent`.
- [ ] Preserve unknown attributes in namespaced metadata.
- [ ] Redaction hooks run before artifacts are persisted.
- [ ] No exporter or hosted backend is introduced.

### AE-105: HTTP sandbox adapter protocol

Define, but do not over-generalize, a protocol for worlds hosted in LocalStack,
Mimic, Terrarium-like environments, or an application test server.

**Acceptance criteria**

- [ ] Explicit reset, snapshot, close, and fault-control endpoints.
- [ ] Auth and secrets are injected by the caller and never serialized.
- [ ] Timeouts and network errors produce deterministic runner violations.
- [ ] A local FastAPI test server demonstrates the adapter.

## P1 — fault and contract packs

### AE-120: Duplicate webhook/event pack

- [ ] Model at-least-once event delivery.
- [ ] Contract verifies one logical business effect despite duplicate events.
- [ ] Include a marketplace order or notification example.

### AE-121: Stale-read / optimistic-concurrency pack

- [ ] Model a read at version N followed by a human write at N+1.
- [ ] Reject blind overwrite and accept compare-and-swap/reconciliation paths.
- [ ] Shrink away unrelated records and concurrent actors.

### AE-122: Authorization revocation pack

- [ ] Model permission granted at planning time and revoked before execution.
- [ ] Verify authorization at the action boundary rather than prompt time.
- [ ] Include structured audit evidence in the failure bundle.

### AE-123: Long-running task and interruption pack

- [ ] Model started/running/completed/failed/cancelled task states.
- [ ] Verify user cancellation does not replay completed effects.
- [ ] Accept resumable and compensating recovery strategies.

## P2 — developer experience

### AE-201: Failure bundle HTML viewer

Build a static, local-only viewer for state diffs, events, violations, and shrink
steps. It must consume the portable bundle and have no server or account.

### AE-202: Domain scaffold command

`agent-effects init-domain refunds` should generate a world skeleton, validity
predicate, contracts, tests, and documentation—not agent orchestration.

### AE-203: Contract helper library

Add typed helpers for cardinality, uniqueness, monotonic state transitions,
least-privilege reads, and authorization-at-effect without hiding domain logic.

- [x] Alpha helpers cover cardinality, uniqueness, authorization-before-write,
  forbidden reads, record linkage, cancellation, and trace ordering.
- [ ] Add a monotonic state-transition helper after a second domain validates its shape.

### AE-204: Corpus of reduced public failures

Create synthetic, privacy-safe regression fixtures based on publicly documented
failure patterns. Every fixture must cite the source pattern and avoid copying
private data.

## Research and adoption gates

### AE-R01: Repository issue mining

- [ ] Maintain a reproducible script/query list for public issue mining.
- [ ] Classify evidence by failure mechanism, affected framework, business
  effect, reproducibility, and whether the source is independent.
- [ ] Publish limitations and avoid treating self-promotional reports as equal
  to independently confirmed incidents.

Evidence maintenance informs priorities but an arbitrary report count does not
block the first usable public alpha. External use in `AE-R02` is the stronger
validation gate.

### AE-R02: External design-partner proof

This cannot be replaced by more desk research indefinitely.

- [ ] Three independent teams encode one real deterministic contract each.
- [ ] Two teams run the testkit in CI for at least four weeks.
- [ ] At least one reduced bundle becomes a retained regression test.
- [ ] Median first-contract setup takes under two hours.

### AE-R03: Kill/pivot review

Pause expansion and revisit the thesis when any two are true:

- [ ] Teams cannot expose/reset state without excessive custom infrastructure.
- [ ] Shrinking rarely produces a materially simpler reproduction.
- [ ] Runtime guards make pre-production testing redundant for target users.
- [ ] Existing eval platforms ship the same commit-aware shrinking primitive.
- [ ] Integration maintenance exceeds core product work.
- [ ] Users consistently ask for a hosted dashboard rather than the testkit.
