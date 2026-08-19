# Runner lifecycle and failure semantics

`TrialRunner` treats execution as a sequence of independently observable stages:

1. world creation;
2. initial snapshot;
3. agent execution;
4. final snapshot;
5. contract evaluation;
6. cleanup;
7. failure-artifact generation.

Ordinary exceptions and `asyncio.CancelledError` at these boundaries become typed
`LifecycleFailure` records. Each record contains the stage, ownership category,
exception type, message, and whether it is the primary failure.

The first failure remains primary. Later failures are retained as secondary
failures. For example, an agent exception followed by a close exception reports
the agent failure as primary and cleanup as secondary. Cleanup is attempted once
whenever world creation returned a world.

## Partial results

`TrialResult.initial_state`, `final_state`, and `agent_run` are optional. `None`
means the stage did not produce that value; it is not an invented empty snapshot.
Contracts run only when both snapshots and an agent result are available.

Agent exceptions retain the established `agent_error` contract code for backward
compatibility. Infrastructure stages use stable `runner_<stage>` codes. Contract
violations remain distinct from infrastructure and adapter failures.

## Cancellation

Cancellation at a runner boundary is captured as a structured result so committed
state and cleanup evidence are not lost. The runner does not claim to cancel work
inside an external service. An adapter that needs stronger cancellation semantics
must model those semantics in the world and contracts.

## Synchronous adapters

World factories, world `snapshot()` and `close()` methods, and agent adapter
`run()` methods may return a direct value or an awaitable. `run_sync()` is for
synchronous callers and intentionally rejects use inside an active event loop.
