<div class="ae-hero" markdown>

<p class="ae-kicker">Agent Effects Testkit · experimental public alpha</p>

# Test the world your AI agent leaves behind.

<p class="ae-lede">Your agent said “refund complete.” Agent Effects found two refunds.</p>

Agent Effects injects failures at durable commit boundaries, checks the final
business state with deterministic contracts, and reduces a failure into a
portable regression case.

<div class="ae-actions">
  <a class="md-button md-button--primary" href="GETTING_STARTED/">Start the quickstart</a>
  <a class="md-button" href="reports/refund-lost-ack.html">Open a failure report</a>
</div>

<ul class="ae-proof">
  <li>No API key</li>
  <li>No model call</li>
  <li>No hosted service</li>
</ul>

</div>

<picture class="ae-transaction">
  <source media="(prefers-color-scheme: dark)" srcset="assets/hero-lost-ack-dark.svg">
  <img src="assets/hero-lost-ack-light.svg" alt="Lost acknowledgement transaction trace: a refund request commits, its acknowledgement is lost, a retry creates a second refund, the final-state contract observes two instead of one, and the case reduces to one order and one fault.">
</picture>

<div class="ae-demo-grid" markdown>

<div markdown>

## See the failure

```bash
python -m pip install \
  "agent-effects-testkit @ git+https://github.com/eschmidt01/agent-effects-testkit@main"
agent-effects demo --agent naive --report
```

</div>

<div class="ae-terminal-result" markdown>

**Contract failure**

```text
expected 1 refund
observed 2 refunds
signature: duplicate_business_effect
```

The demo exits with status `1` and writes an integrity-checked bundle plus a
self-contained local report.

</div>

</div>

## From one failure to a regression test

<div class="ae-step-grid">
  <a href="WRAPPING_CALLABLES/">
    <strong>1. Wrap the callable</strong>
    <span>Run the agent you already have against an isolated world.</span>
  </a>
  <a href="COMMIT_BOUNDARIES/">
    <strong>2. Mark the commit</strong>
    <span>Identify the exact point where the business effect becomes durable.</span>
  </a>
  <a href="CONTRACTS/">
    <strong>3. Assert the world</strong>
    <span>Check cardinality, authorization, linkage, and trace invariants.</span>
  </a>
  <a href="REPORTS/">
    <strong>4. Keep the case</strong>
    <span>Inspect the reduced failure and promote it to a regression test.</span>
  </a>
</div>

## What Agent Effects tests

| Method | Primary question | Evidence |
| --- | --- | --- |
| Response evaluation | Did the answer look correct? | Text or structured output |
| Trace inspection | What calls and decisions occurred? | Events, spans, tool results |
| Transport fault injection | Did the service tolerate a disconnect? | Retries, status codes, latency |
| **Final-state transaction testing** | **What world did the agent leave behind?** | **Snapshots, commit markers, deterministic contracts** |

Agent Effects focuses on the final row. It is not a runtime transaction layer,
sandbox, agent framework, hosted dashboard, or production-readiness guarantee.
Read the [security boundaries](THREAT_MODEL.md) before sharing bundles, or
[submit voluntary alpha feedback](ALPHA_FEEDBACK.md).
