# Roadmap

The roadmap is evidence-gated. Shipping a broad platform before the narrow core
is adopted would erase the project's differentiation.

## Milestone A — credible local alpha (`0.1.0a1`, complete)

- portable schema export;
- integrity-checked failure bundles with unsigned hashes;
- delta-debugging shrinker;
- lifecycle hardening;
- 90%+ core branch coverage;
- reproducible wheel and source builds; and
- polished refund example.

**Exit condition:** an unfamiliar engineer can install the package, understand
the failure, and create a domain contract in under two hours.

## Milestone B — see the failure (`0.1.0a2`)

- visual README and lost-ack transaction diagram;
- deterministic, self-contained HTML failure report;
- report-enabled packaged demo;
- visual MkDocs home and public synthetic report; and
- explicit community contribution surface.

**Exit condition:** an unfamiliar developer can see expected versus observed
state, the commit/fault timeline, and the reduced regression case without
reading raw bundle JSON.

## Milestone C — one framework proof (`0.2.0a1`, proposed)

- one optional LangGraph integration;
- deterministic checkpoint and resumption scenario;
- stable-idempotency and reconciliation variants; and
- no external model, API key, or LangGraph Cloud dependency.

**Exit condition:** the optional integration reproduces the same semantic lost-
ack failure through framework-neutral traces and bundles, with no framework
dependency in core.

Additional frameworks remain evidence-gated rather than bundled into this
milestone.

## Milestone D — fault packs

- duplicate events and webhooks;
- stale reads and optimistic concurrency;
- permission revocation;
- long-running task interruption;
- cancellation and compensation; and
- deterministic concurrent schedule prototype.

**Exit condition:** fault packs are derived from retained external regression
cases rather than only synthetic imagination.

## Milestone E — ecosystem and usability

- deeper local failure-report usability;
- domain scaffold command;
- additional contract helpers;
- privacy-safe public counterexample corpus; and
- adapters for living environments and common sandbox systems.

**Exit condition:** external contributors maintain at least one adapter or fault
pack.

## 1.0 criteria

- stable portable schemas with migration policy;
- documented compatibility contract;
- no known cross-file bundle integrity gaps;
- deterministic seeded execution and shrinking;
- real CI adoption by multiple independent teams;
- security review of artifact handling and external adapters;
- maintainership beyond a single person; and
- a clear answer to what belongs in core versus integrations.

## Explicitly deferred

- hosted control plane;
- multi-tenant dashboard;
- prompt or model scoring platform;
- autonomous generation of business contracts from prose;
- production runtime idempotency store; and
- arbitrary-code sandbox implementation.
