# Roadmap

The roadmap is evidence-gated. Shipping a broad platform before the narrow core
is adopted would erase the project's differentiation.

## Milestone A — credible local alpha

- portable schema export;
- integrity-checked failure bundles with unsigned hashes;
- delta-debugging shrinker;
- lifecycle hardening;
- 90%+ core branch coverage;
- reproducible wheel and source builds;
- polished refund and duplicate-notification examples.

**Exit condition:** an unfamiliar engineer can install the package, understand
the failure, and create a domain contract in under two hours.

## Milestone B — framework proofs

- LangGraph integration;
- OpenAI Agents SDK integration;
- CrewAI integration;
- OpenTelemetry trace import;
- one HTTP sandbox adapter.

**Exit condition:** at least two independent frameworks reproduce the same
semantic failure through the portable case model, with no framework dependency
in core.

## Milestone C — fault packs

- duplicate events/webhooks;
- stale reads and optimistic concurrency;
- permission revocation;
- long-running task interruption;
- cancellation and compensation;
- deterministic concurrent schedule prototype.

**Exit condition:** fault packs are derived from retained external regression
cases rather than only synthetic imagination.

## Milestone D — ecosystem and usability

- local static failure viewer;
- domain scaffold command;
- contract helper library;
- privacy-safe public counterexample corpus;
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
- maintainership beyond a single person;
- a clear answer to what belongs in core versus integrations.

## Explicitly deferred

- hosted control plane;
- multi-tenant dashboard;
- prompt/model scoring platform;
- autonomous generation of business contracts from prose;
- production runtime idempotency store;
- arbitrary-code sandbox implementation.
