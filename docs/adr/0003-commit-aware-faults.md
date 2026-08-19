# ADR 0003: Faults must model business commit position

- Status: Accepted
- Date: 2026-08-19

## Context

A generic timeout is ambiguous. If it occurs before a durable effect, retry can
be required. If the effect committed and only the acknowledgement was lost,
blind retry can duplicate it.

## Decision

Operations explicitly mark the durable business commit. The initial fault model
supports timeout-before and timeout-after-commit targeted by operation
occurrence. Timeout-after-commit is invalid without a commit marker.

## Consequences

- Adapters require a small amount of domain instrumentation.
- Fault behavior is deterministic and testable.
- The system avoids guessing commit state from transport status.
- More complex partial/multi-resource commits require future ADRs.
