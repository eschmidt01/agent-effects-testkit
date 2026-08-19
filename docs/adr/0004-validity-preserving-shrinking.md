# ADR 0004: Shrinking must preserve domain validity

- Status: Accepted
- Date: 2026-08-19

## Context

Removing records can create impossible worlds: a notification without a case,
a payment referencing a missing customer, or an actor absent from the directory.
Such counterexamples waste debugging time and destroy trust.

## Decision

Every shrink operation is gated by a caller-provided validity predicate. Core
also requires strictly lower JSON complexity before evaluating a candidate.

## Consequences

- Domain integrations must define validity.
- Reduction may stop before a globally minimal case; the implementation reports
  only the guarantee established under configured reducers and budgets.
- The resulting reproduction remains meaningful and executable.
