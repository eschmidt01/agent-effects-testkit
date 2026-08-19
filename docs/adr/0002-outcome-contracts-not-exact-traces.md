# ADR 0002: Specify acceptable outcomes, not one exact trajectory

- Status: Accepted
- Date: 2026-08-19

## Context

A safe agent may recover through stable idempotency, reconciliation, human
approval, or compensation. Snapshot-testing one tool sequence can reject valid
strategies and overfit a model/framework version.

## Decision

Contracts should primarily assert final state, authorization, privacy, and other
semantic invariants. Trace assertions are appropriate only when the behavior
itself is required or prohibited.

## Consequences

- Different safe implementations can pass the same suite.
- Contracts need domain expertise.
- Debugging still uses the trace, but the trace is not automatically the oracle.
