# ADR 0005: Future LangGraph integration remains an optional extra

- Status: Proposed; implementation gated on green remote CI for the exact
  `v0.1.0a1` candidate commit
- Date: 2026-08-19

## Context

The first framework integration should test LangGraph interruption, checkpoint,
and resumption behavior without making the core testkit a framework or requiring
LangGraph Cloud. As of this ADR, PyPI lists LangGraph 1.2.9. Official LangGraph
documentation describes thread IDs as checkpoint cursors, node restart on
interrupt resumption, checkpoint namespaces for subgraphs, and replay of nodes
after a selected checkpoint.

Primary references:

- <https://pypi.org/project/langgraph/>
- <https://docs.langchain.com/oss/python/langgraph/interrupts>
- <https://docs.langchain.com/oss/python/langgraph/persistence>
- <https://docs.langchain.com/oss/python/langgraph/use-subgraphs>
- <https://docs.langchain.com/oss/python/langgraph/use-time-travel>

## Decision

The proposed first implementation will live in this repository behind:

```bash
pip install "agent-effects-testkit[langgraph]"
```

Core imports and installation remain LangGraph-free. The initial proposed and
CI-tested dependency range is `langgraph>=1.2,<1.3`; Dependabot and an explicit
compatibility PR may widen it after the adapter suite passes against the new
minor line. This is a proposed range, not current support, until implementation
and tests exist.

### Trace mapping

The adapter will emit the existing portable `TraceEvent` envelope:

- tool invocation becomes `TOOL_CALL`, with tool name as `operation` and
  JSON-only arguments plus stable context identifiers in `data`;
- tool completion will use a proposed framework-neutral `TOOL_RESULT` event
  kind, with result/error status and the matching tool-call ID;
- durable application effects remain `COMMIT` events emitted by
  `mark_committed()`; a LangGraph tool return must never imply a commit;
- interrupts, resumptions, and checkpoint observations use `AGENT` events with
  stable operations `interrupt`, `resume`, and `checkpoint` and a
  `framework="langgraph"` data attribute; and
- tool exceptions use `ERROR` with the matching tool-call identity.

Adding `TOOL_RESULT` requires the normal portable-schema compatibility review
before implementation. Tool arguments and results must remain JSON-only and use
the existing application redaction boundary.

### Identity propagation

The adapter context will carry:

- `thread_id`: the application-supplied LangGraph checkpoint cursor;
- `checkpoint_id` and `checkpoint_ns`: copied from checkpoint configuration;
- `run_id`: one testkit trial execution, stable across a resume sequence;
- `actor_id`: derived from the portable case's actor data through an explicit
  application mapping;
- `tool_call_id`: the framework-provided call ID, or a deterministic ID derived
  from run, namespace, node/task, tool name, and occurrence when absent; and
- `graph_path`: an ordered tuple of graph/subgraph node names.

These values are carried through an immutable adapter context rather than global
state. Nested graphs extend `graph_path` and `checkpoint_ns`; they do not replace
the parent run, thread, or actor identity. Async context propagation must preserve
these values across nested execution.

### Interruption, resumption, and duplicate detection

An interrupted run records the interrupt and last observed checkpoint. A resume
uses the same `thread_id` and records the source checkpoint plus a new execution
attempt. Repeated tool execution is detected by correlating logical operation,
business key, graph path, and checkpoint lineage—not merely by equal text
output. Final-state cardinality/uniqueness contracts remain authoritative for
whether a duplicate business effect occurred.

The reference scenario is:

> A tool performs a durable side effect, execution is interrupted or resumed
> from a checkpoint without a recorded acknowledgment, and naive execution
> produces a duplicate effect. Stable idempotency and reconciliation both
> satisfy the same final-state contracts.

Tests will use an in-memory checkpointer, scripted graph nodes/tools, and the
in-memory refund world. They require no external model, API key, network call,
LangGraph Cloud, Agent Server, or LangSmith.

### Application responsibilities

The application must still provide:

- a valid isolated world, reset/snapshot/cleanup, and synthetic credentials;
- the real durable commit marker inside the tool implementation;
- actor extraction and business-key semantics;
- deterministic state and trace contracts;
- safe idempotency or reconciliation behavior; and
- redaction and external sandboxing where needed.

The adapter observes and tests these responsibilities; it does not supply
production transaction enforcement, authorization, persistence, or sandboxing.

### Compatibility and deprecation

Each supported LangGraph minor line must pass the same credential-free adapter
suite. Dropping a minor requires a changelog entry, one alpha/minor release of
advance deprecation notice when feasible, and an actionable import-time version
diagnostic. Framework metadata stays in trace `data`; core case, trace, result,
signature, reduction, and bundle schemas remain framework-neutral. No
LangGraph-specific object may cross a portable model boundary.

## Consequences

- Core remains lightweight and callable-adapter users do not install LangGraph.
- A narrow version range creates deliberate maintenance work but makes the first
  public integration testable.
- The integration cannot start until remote CI passes for the committed
  `v0.1.0a1` candidate revision.
