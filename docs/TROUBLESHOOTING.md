# Troubleshooting

## Targeted operation never executed

The agent may have taken an earlier branch, or the world method may not use
`faults.operation()`. The diagnostic lists configured operations and suggests
confirming control flow and instrumentation.

## Operation name does not match

Compare the configured name with the observed instrumented operation names in
the diagnostic. Names are exact and case-sensitive; occurrences are one-based.

## `timeout_after_commit` never reaches a marker

Place `mark_committed()` immediately after the durable business write. Do not
place it after a request send that might not commit.

## Original case is invalid

The validity predicate rejected the baseline. Repair the initial relational and
policy state before shrinking; invalid candidates are skipped without execution.

## Baseline is unstable

Observed signatures differed across confirmation runs. Make the agent/world
deterministic, seed stochastic components, or increase `confirm_signature_runs`.
No minimality claim is made for an unstable baseline.

## Evaluation or time budget exhausted

The reduction report identifies the exhausted budget and reduced case accepted so far.
Increase `max_evaluations` or `max_elapsed_ms` only after checking that candidate
execution is isolated and deterministic.

## Final snapshot unavailable

Contracts needing final state are skipped. Fix `world.snapshot()`; the structured
result retains earlier stage information and trace data.

## Cleanup failed after another failure

The earlier failure remains primary and cleanup is recorded as secondary. Fix
`world.close()` so state cannot leak into later trials.

## Bundle schema is unsupported

Install a toolkit version supporting the manifest schema, or regenerate the
bundle with a supported producer. Readers do not silently reinterpret versions.

## No reproducer is registered

Install the adapter package that owns the declared entry point, or rerun the
originating test with a stable `reproducer_id`. `reproduce --dry-run` identifies
the declaration without running code.
