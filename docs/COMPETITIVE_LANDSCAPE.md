# Competitive landscape

The relevant ecosystem is broad. This document defines integration boundaries
rather than declaring every adjacent project a competitor.

## Evaluation and regression systems

Examples include DeepEval/Confident AI, Promptfoo, Inspect AI, Braintrust,
LangSmith, Langfuse, Attest, and many domain-specific simulators. They provide
valuable datasets, assertions, graders, tracing, and reporting.

**Agent Effects boundary:** export results to them later; do not rebuild their
prompt/model scoring, dashboards, or collaboration layers.

## Stateful and living test environments

Projects such as Terrarium, Mimic, Archal, LocalStack, browser sandboxes, and
application-specific fakes provide realistic APIs and persistent state.

**Agent Effects boundary:** treat them as `World` backends. Own test-case
semantics, commit-aware fault schedules, contracts, and shrinking—not a catalog
of every service clone.

## Runtime safety and idempotency

SafeAgent, agent-ledger, tool authorization middleware, workflow engines, and
provider idempotency keys can prevent duplicate execution at runtime.

**Agent Effects boundary:** test whether these controls survive process restart,
checkpoint replay, changed idempotency keys, ambiguous responses, and concurrent
events. Do not become a production transaction coordinator.

## Agent runtimes with formal or state-machine semantics

Temper, Stately Agent, LangGraph, Temporal-based systems, and other durable
runtimes can model state transitions and replay.

**Agent Effects boundary:** remain framework-neutral and test externally
observable business outcomes. Integrations may use runtime-specific hooks, but
portable cases and contracts cannot depend on them.

## Fault injection and chaos tools

Faultkit, network proxies, service meshes, and custom test doubles inject
latency, transport errors, malformed payloads, and unavailable services.

**Agent Effects boundary:** compose with low-level chaos while adding the
semantic distinction between “definitely did not commit” and “committed but
acknowledgement was lost.”

## Differentiation checklist

A feature belongs in core when it strengthens at least two of these:

- semantic business-effect timing;
- deterministic final-state or access contracts;
- valid world generation;
- signature-preserving counterexample reduction;
- portable cross-framework failure artifacts.

A feature probably belongs elsewhere when its primary value is:

- model/prompt quality scoring;
- production tracing dashboards;
- agent orchestration;
- runtime execution guarantees;
- provider API emulation;
- hosted team collaboration.
