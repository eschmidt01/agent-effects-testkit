# Getting started

## Five-minute concept

Agent Effects tests whether an agent leaves the world correct after an ambiguous
side effect. A normal unit test supplies a case, an isolated world, an agent, and
deterministic contracts. The testkit adds a fault schedule around the durable
business commit:

1. `timeout_before` proves the write did not commit.
2. `timeout_after_commit` proves the write committed but its acknowledgment was
   lost.
3. The runner snapshots initial and final state and records framework-neutral
   events.
4. Contracts evaluate state and trace facts, not the persuasiveness of model text.
5. The shrinker retains the exact failure signature while removing irrelevant
   input.
6. A local bundle preserves the original case, reduced case, trace, result, and
   reduction report.

This is a pre-production testing tool, not an agent framework, sandbox, or runtime
idempotency layer.

## Install

Python 3.11–3.13 is supported.

```bash
python -m venv .venv
source .venv/bin/activate
pip install \
  "agent-effects-testkit @ git+https://github.com/eschmidt01/agent-effects-testkit@main"
pip install pytest
agent-effects version
```

Core tests require no network after installation, API key, hosted account, or
model service.

## Automated clean-room quickstart

The following workflow is exercised by the installed-wheel acceptance test. It
has not yet been timed by an external person, so it is described as an automated
clean-room quickstart rather than a human-validated 15-minute claim.

```bash
agent-effects init ./lost-ack-demo --template lost-ack
cd lost-ack-demo
pytest -q
```

The selected demonstration template intentionally fails. Its refund commits,
`timeout_after_commit` loses the acknowledgment, and a naive retry creates a
duplicate. The assertion shows the bundle path.

```bash
agent-effects bundle verify .agent-effects/failures/<bundle>
agent-effects bundle inspect .agent-effects/failures/<bundle>
agent-effects bundle report .agent-effects/failures/<bundle> --open
agent-effects reproduce --dry-run .agent-effects/failures/<bundle>
agent-effects reproduce .agent-effects/failures/<bundle>
```

`verify`, `inspect`, and `report` parse verified data only. The dry run identifies installed
reproducer code without executing it. The final command executes that registered
code and must reproduce the same typed failure signature.

Open `policy.py`, change `STABLE_IDEMPOTENCY` to `True`, then run:

```bash
pytest -q
```

The test now passes because the retry uses the stable business idempotency key.
For a passing project intended for adaptation instead, run:

```bash
agent-effects init ./my-agent-tests
cd my-agent-tests
pytest -q
```

Next, replace the generated callable and in-memory world with your application
entry point and test adapter.
