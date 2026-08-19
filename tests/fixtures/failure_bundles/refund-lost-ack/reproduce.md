# Reproduce this Agent Effects failure

Verify and rerun the reduced case stored as minimized-case.json:

```bash
agent-effects bundle verify .
agent-effects reproduce --dry-run .
agent-effects reproduce .
```

Registered reproducer: `agent-effects.examples.refund/naive/v1`

`bundle verify` and `bundle inspect` do not execute code. `reproduce` executes the installed registered reproducer.
