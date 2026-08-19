# Agent Effects Testkit

[![CI](https://github.com/eschmidt01/agent-effects-testkit/actions/workflows/ci.yml/badge.svg)](https://github.com/eschmidt01/agent-effects-testkit/actions/workflows/ci.yml)
[![Python 3.11–3.13](https://img.shields.io/badge/python-3.11%E2%80%933.13-3776AB.svg)](https://www.python.org/downloads/)
[![License: Apache-2.0](https://img.shields.io/badge/license-Apache--2.0-blue.svg)](LICENSE)
[![Version: 0.1.0a1](https://img.shields.io/badge/version-0.1.0a1-orange.svg)](CHANGELOG.md)

A pytest-native transaction-testing toolkit for engineers building AI agents
that create durable side effects. Use it when retries, resumptions, cancellation,
or lost acknowledgements can leave the business world in an invalid state.

> A refund commits.<br>
> Its acknowledgement is lost.<br>
> The agent retries.<br>
> Two refunds exist.<br>
> Agent Effects detects the invalid business state and reduces the failure into
> a reproducible regression case.

Try the explicit lost-acknowledgement demonstration without an API key or model
call:

```bash
python -m pip install \
  https://github.com/eschmidt01/agent-effects-testkit/releases/download/v0.1.0a1/agent_effects_testkit-0.1.0a1-py3-none-any.whl
agent-effects init ./lost-ack-demo --template lost-ack
cd lost-ack-demo
pytest -q  # intentionally fails with a duplicate-effect contract violation
```

The alpha does not provide an agent framework, hosted service, model judge,
runtime idempotency layer, or sandbox for installed reproducer code.

AI agents do not only produce text. They create refunds, send messages, update
cases, mutate infrastructure, and resume long-running work. A response can look
correct while the underlying world is wrong—for example, a refund succeeds, its
acknowledgement times out, and the agent retries into a duplicate refund.

Agent Effects Testkit exercises those failures as deterministic software tests:

```text
valid initial world
× actor and permissions
× goal
× commit-aware fault schedule
→ run the agent
→ inspect final state and trace
→ enforce deterministic contracts
→ reduce the failure to a portable, same-signature reproduction
```

The alpha intentionally focuses on a narrow, high-value primitive:

- **commit-aware faults** such as timeout-before-commit and
  timeout-after-commit;
- **outcome contracts** over business state, authorization, privacy, and
  idempotency;
- **validity-preserving shrinking** of faults and world data;
- **integrity-checked failure bundles** for CI artifacts and regression tests;
- **framework-neutral adapters**, starting with ordinary Python callables.

It is not another prompt-scoring dashboard, LLM judge, agent orchestrator, or
runtime idempotency product. It complements those systems by turning ambiguous
side-effect behavior into a small deterministic test case.

## Status

`0.1.0a1` is an experimental public-alpha candidate for deterministic
pre-production testing of AI-agent side effects. The core abstractions,
structured runner lifecycle, portable schemas, hierarchical reduction, guarded
starter projects, and integrity-checked failure bundles are implemented and
tested locally. The remote-CI and external-adoption gates remain open; this is
not a company-ready or generally production-ready claim. See
[`docs/RESEARCH_VALIDATION.md`](docs/RESEARCH_VALIDATION.md) and
[`docs/RESEARCH_EVIDENCE.md`](docs/RESEARCH_EVIDENCE.md) for the online
research behind this scope, [`VALIDATION_REPORT.md`](VALIDATION_REPORT.md)
for the reproducible local verification record, and [`TASKS.md`](TASKS.md) for
agent-ready work.

## Sixty-second demo

Python 3.11–3.13 is supported.

```bash
python -m venv .venv
source .venv/bin/activate
pip install -e '.[dev]'

# Expected to fail and write a bundle containing a reduced case.
agent-effects demo --agent naive

# Different safe recovery strategies; both should pass.
agent-effects demo --agent idempotent
agent-effects demo --agent reconcile

pytest

# Verify internal consistency, inspect, and reproduce the emitted bundle.
agent-effects bundle verify .agent-effects/failures/<bundle>
agent-effects bundle inspect .agent-effects/failures/<bundle>
agent-effects reproduce --dry-run .agent-effects/failures/<bundle>
agent-effects reproduce .agent-effects/failures/<bundle>

# Export stable v1alpha1 JSON Schemas.
agent-effects schema export --output ./schemas
```

The naive agent returns a success message but leaves two refunds after a lost
acknowledgement. The testkit catches the incorrect final state and reduces an
initially noisy case to the essential fault:

```yaml
operation: issue_refund
occurrence: 1
mode: timeout_after_commit
```

The bundle commands use complete SHA-256 hashes and cross-file identities to
check integrity relative to the manifest and internal consistency. Unsigned
hashes do not authenticate the author or establish provenance. Verification is
local, executes no code, and needs no model key or network connection.
`reproduce --dry-run` identifies the installed reproducer without executing it;
`reproduce` crosses that boundary and runs registered installed code.

Generate a passing project to adapt, or the explicit lost-ack demonstration:

```bash
agent-effects init ./my-agent-tests
agent-effects init ./lost-ack-demo --template lost-ack
```

## Public API example

```python
from agent_effects.examples.refund import (
    AGENTS,
    REFUND_CONTRACTS,
    RefundWorld,
    make_refund_case,
)
from agent_effects.models import FaultMode
from agent_effects.pytest_plugin import assert_contracts


def test_refund_agent_survives_lost_ack(agent_effects_runner) -> None:
    result = agent_effects_runner.run_sync(
        case=make_refund_case(
            fault_mode=FaultMode.TIMEOUT_AFTER_COMMIT,
        ),
        world_factory=RefundWorld,
        agent=AGENTS["idempotent"],
        contracts=REFUND_CONTRACTS,
    )
    assert_contracts(result)
```

A world adapter marks the exact business commit boundary:

```python
async with self.faults.operation("issue_refund", payment_id=payment_id) as effect:
    refund = await persist_refund(...)
    effect.mark_committed(refund_id=refund.id)
    return refund
```

That lets the testkit distinguish:

- **timeout before commit:** retry may be necessary;
- **timeout after commit:** the effect happened, but the agent does not know it.

## Repository map

```text
src/agent_effects/
├── faults.py          # Commit-aware semantic failure injection
├── contracts.py       # Deterministic outcome contracts
├── runner.py          # Isolated trial lifecycle
├── shrink.py          # Validity-preserving counterexample reduction
├── artifacts.py       # Portable failure bundles
├── protocols.py       # Framework-neutral extension interfaces
├── pytest_plugin.py   # Direct pytest assertion helper
└── examples/refund.py # Complete lost-acknowledgement reference domain

src/agent_effects_pytest.py # Minimal auto-loaded pytest fixture shim

docs/
├── RESEARCH_VALIDATION.md
├── PRODUCT_SPEC.md
├── ARCHITECTURE.md
├── TESTING_STRATEGY.md
├── THREAT_MODEL.md
├── ROADMAP.md
├── FAILURE_BUNDLE_SPEC.md
├── INTEGRATION_GUIDE.md
├── adr/
└── agent/             # Instructions and handoff process for coding agents
```

## Design principles

1. **Final state over persuasive prose.** A successful-looking answer is not a
   successful transaction.
2. **Deterministic checks before model judges.** Business invariants should be
   code whenever code can express them.
3. **Multiple safe trajectories are valid.** Contracts specify acceptable
   outcomes, not one brittle sequence of tool calls.
4. **Faults describe business semantics.** A generic HTTP timeout is not enough;
   commit position changes the correct recovery behavior.
5. **Generated worlds must remain valid.** Shrinking may not create impossible
   foreign-key relationships or nonsensical authorization states.
6. **A failure should become a regression test.** Every result is local,
   inspectable, versioned JSON—not trapped in a hosted dashboard.
7. **No required network or model key.** The core, demos, and CI are fully
   deterministic and local-first.

## Current non-goals

The alpha does not attempt to provide:

- agent orchestration or model routing;
- prompt management or general response-quality scoring;
- a hosted observability platform;
- a replacement for runtime idempotency and authorization controls;
- a universal mock of every SaaS provider;
- automatic execution of untrusted agent code in a secure sandbox;
- a custom contract DSL before the Python API has real adoption evidence.

## Development

With `uv`:

```bash
uv sync --extra dev
uv run pytest
uv run ruff check .
uv run ruff format --check .
uv run mypy
```

Without `uv`:

```bash
pip install -e '.[dev]'
make check
```

The optional Hypothesis suite is enabled by the `dev` or `hypothesis` extra.
The deterministic suite remains runnable without it.

## Working with coding agents

Start with [`AGENTS.md`](AGENTS.md), then read:

1. [`TASKS.md`](TASKS.md)
2. [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md)
3. [`docs/agent/IMPLEMENTATION_PLAN.md`](docs/agent/IMPLEMENTATION_PLAN.md)
4. the ADR relevant to the task

Agents should implement one acceptance-tested task at a time and leave a handoff
entry using [`docs/agent/SESSION_CHECKLIST.md`](docs/agent/SESSION_CHECKLIST.md).

## Contributing and security

Read [`CONTRIBUTING.md`](CONTRIBUTING.md) before opening a pull request. Please
report security issues according to [`SECURITY.md`](SECURITY.md), especially if
a failure bundle can leak sensitive test or production data.

Use the [issue tracker](https://github.com/eschmidt01/agent-effects-testkit/issues)
for bugs and feature requests, or submit the voluntary
[alpha adoption report](https://github.com/eschmidt01/agent-effects-testkit/issues/new?template=alpha_adoption_report.yml)
after a clean-room trial.

Apache-2.0 licensed. See [`LICENSE`](LICENSE) and [`NOTICE`](NOTICE).
