# Agent Effects

## Test the world your AI agent leaves behind.

**Your agent said “refund complete.” Agent Effects found two refunds.**

Agent Effects Testkit injects deterministic failures around durable business
commits, checks the final world with code, and reduces a failure into a portable
regression case.

<picture>
  <source media="(prefers-color-scheme: dark)" srcset="assets/hero-lost-ack-dark.svg">
  <img src="assets/hero-lost-ack-light.svg" alt="Lost acknowledgement transaction: a refund commits, its acknowledgement is lost, retry creates a second refund, and the failure reduces to one order and one fault.">
</picture>

```bash
python -m pip install \
  "agent-effects-testkit @ git+https://github.com/eschmidt01/agent-effects-testkit@main"
agent-effects demo --agent naive --report
```

The demo prints `expected 1 refund`, `observed 2 refunds`, and the path to a
self-contained local report. It needs no API key, model call, hosted service, or
network access after installation.

[Open the public synthetic report](reports/refund-lost-ack.html){ .md-button .md-button--primary }
[Five-minute quickstart](GETTING_STARTED.md){ .md-button }

## What to do next

- [Wrap an existing callable agent](WRAPPING_CALLABLES.md).
- [Mark the durable commit boundary](COMMIT_BOUNDARIES.md).
- [Write final-state and trace contracts](CONTRACTS.md).
- [Generate, inspect, and share a static report](REPORTS.md).
- [Understand verification and security boundaries](THREAT_MODEL.md).
- [Submit a voluntary alpha adoption report](ALPHA_FEEDBACK.md).

Agent Effects is an experimental public alpha for deterministic pre-production
testing of AI-agent side effects. It is not a runtime transaction layer,
sandbox, agent framework, hosted dashboard, or production-readiness guarantee.
