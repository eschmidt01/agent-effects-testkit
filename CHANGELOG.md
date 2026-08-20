# Changelog

All notable changes will be documented here. The project follows Semantic
Versioning once it reaches a stable public API; alpha releases may make breaking
changes with explicit migration notes.

## [Unreleased]

### Added

- Deterministic `agent-effects bundle report` HTML generation with `--output`
  and local `--open` support
- Self-contained failure view covering expected/observed state, fault schedule,
  commit-aware timeline, violations, structured diff, reduction guarantee,
  reproduction boundary, and collapsible raw JSON
- HTML injection, tampering, local-file opening, and no-reproducer-resolution
  security tests
- `agent-effects demo --agent naive --report` visual failure workflow
- Light/dark lost-ack diagrams, reproducible terminal GIF, report screenshot,
  social preview, visual documentation home, and GitHub Pages workflow

### Changed

- Public message now leads with “Agent Effects — Test the world your AI agent
  leaves behind,” while retaining Agent Effects Testkit as the formal package
- Documentation, transaction diagrams, social preview, and failure report now
  use a restrained GitHub-style visual system with system fonts, neutral
  surfaces, crisp borders, and accessible light/dark palettes
- The terminal demonstration now ends on a verified bundle and report path,
  and working-directory artifacts display without machine-specific prefixes
- MkDocs navigation is grouped into Get started, Guides, Reference, and Project
  sections instead of promoting every document to a top-level tab
- Roadmap completes the visual report before the proposed single LangGraph
  integration

### Fixed

- Removed an unfinished shell comment and an absolute local path from the
  reproducible terminal demonstration
- Enabled the documentation workflow to deploy the visual-report branch before
  merge so the public Pages URL can be reviewed instead of returning 404

### Security

- Report generation accepts only a fully verified bundle, escapes untrusted
  strings, uses no remote assets or scripts, and emits a restrictive CSP
- Reports warn that bundle content may be sensitive and redaction remains
  adapter-owned

### Planned

- Independent clean-room onboarding and adoption feedback
- One deep LangGraph integration after this pull request and a green remote CI

## [0.1.0a1] - 2026-08-19

### Added

- Typed lifecycle failures for world creation, snapshots, agent execution,
  contract orchestration, cleanup, and artifact generation
- Explicit partial trial results and injectable monotonic timing
- Synchronous and asynchronous world/agent lifecycle support
- Deterministic `v1alpha1` JSON Schema export and checked compatibility fixtures
- Content-addressed, loadable failure bundles with strict cross-file verification
- `bundle verify`, `bundle inspect`, and registered one-command reproduction
- Typed `FailureSignature` values for exact contract and lifecycle identity
- Sequential hierarchical/ddmin reduction with canonical caching, validity
  checks, confirmation runs, budgets, extension reducers, and reduction reports
- `agent-effects init` passing starter and explicit API-key-free `lost-ack` demo
- Deterministic contract helpers for cardinality, uniqueness, authorization,
  forbidden reads, record linkage, cancellation, and event ordering
- Automated installed-wheel clean-room workflow and complete onboarding guides
- Voluntary alpha-adoption issue form, external onboarding protocol,
  least-privilege GitHub Actions candidate workflow, and unexecuted remote
  release procedure
- Proposed, implementation-gated ADR for an optional LangGraph integration
- Public repository metadata and an observed Python 3.11–3.13 GitHub Actions
  release matrix with package and installed-wheel clean-room validation

### Changed

- `TrialResult.initial_state`, `final_state`, and `agent_run` are nullable so a
  failed stage is represented explicitly rather than as invented empty data
- Failure bundles now contain independent snapshots, faults, trace, violations,
  reproduction instructions, and SHA-256 metadata; early hashless bundles must
  be regenerated for strict verification
- Core coverage floor raised from 85% to 90%
- New manifests carry an authoritative full SHA-256 content digest and typed
  signature while retaining old `v1alpha1` bundle loading compatibility
- Bundle verification language now states the unsigned-hash boundary precisely;
  `reproduce --dry-run` identifies code without executing it
- The shortened failure ID remains display-only; full-digest collision handling
  chooses a safe non-overwriting directory
- Hierarchical reduction now reports `locally_minimal`, the participating
  reducers, named validity predicate, explicit budget-exhaustion flags, and a
  typed guarantee; it does not claim global minimality
- `ReductionGuarantee` is public, and `HierarchicalShrinker.shrink` accepts an
  optional stable `validity_predicate_id` for portable reports

### Fixed

- Keep `agent-effects init` conflict recovery guidance visible when long paths
  are rendered in narrow non-interactive terminals such as GitHub Actions

### Compatibility

- Existing `agent-effects.case/v1alpha1` cases and legacy `0.1.0a0` bundle
  manifests continue to load.
- The legacy `GreedyShrinker`, `CaseReducer`, `ShrinkReport`, and tuple
  `TrialResult.signature` remain available.
- `HierarchicalShrinker` is a new API and requires an explicit typed target
  signature and domain validity predicate; no existing public call changed.
- Writers replaced the pre-release-only `ReductionStopReason.MINIMAL` spelling
  with `LOCALLY_MINIMAL`; readers retain `LEGACY_MINIMAL` solely to load earlier
  local `v1alpha1` reports without assigning a minimality guarantee. New report
  guarantee/validity fields have compatibility defaults.

[Unreleased]: https://github.com/eschmidt01/agent-effects-testkit/compare/v0.1.0a1...HEAD
[0.1.0a1]: https://github.com/eschmidt01/agent-effects-testkit/releases/tag/v0.1.0a1

## [0.1.0a0] - 2026-08-19

### Added

- JSON-only portable case, trace, result, contract, and shrink models
- Commit-aware `timeout_before` and `timeout_after_commit` fault injection
- Deterministic state and trace contracts
- Async trial runner with final-state preservation on agent errors
- Validity-preserving greedy shrinker
- Portable local failure bundles
- Pytest fixture and assertion helper
- CLI doctor, demo, case validation, and bundle inspection commands
- Complete refund/lost-acknowledgement reference domain
- Professional OSS, research, architecture, security, and coding-agent docs
