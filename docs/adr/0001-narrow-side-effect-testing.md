# ADR 0001: Keep the product narrowly focused on side-effect testing

- Status: Accepted
- Date: 2026-08-19

## Context

General LLM and agent evaluation, tracing, simulation, and runtime-governance
markets are already crowded. Public incidents nevertheless show a recurring gap
around ambiguous committed effects and retries.

## Decision

Core will focus on commit-aware semantic faults, deterministic outcome/access
contracts, valid world cases, counterexample shrinking, and portable bundles.
It will integrate with rather than replace agent frameworks, observability tools,
living environments, and production runtime guards.

## Consequences

- Initial surface is smaller and easier to trust.
- Some users seeking prompt scoring or dashboards will be out of scope.
- Framework integrations stay optional.
- Product expansion requires adoption evidence and a new ADR.
