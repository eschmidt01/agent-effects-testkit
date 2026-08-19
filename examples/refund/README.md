# Refund example

This example models the production failure where a refund succeeds, its response
is lost, and an agent retries. The naive agent changes its idempotency key and
creates two refunds. The robust agents either reuse a stable key or reconcile
against world state.

Run the packaged demo:

```bash
agent-effects demo --agent naive
agent-effects demo --agent idempotent
agent-effects demo --agent reconcile
```

The first command is expected to exit non-zero and write a reduced failure
bundle. The latter two should pass the same state contracts through different
valid execution trajectories.
