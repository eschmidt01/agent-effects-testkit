# Online research validation

**Research date:** 2026-08-19

**Decision:** Proceed with a narrow public alpha; do not position it as a broad
agent-evaluation platform.

## Question

Is there enough public evidence that engineers need a framework-neutral tool for
commit-aware side-effect testing and reduced reproductions of agent failures?

## Method

The research reviewed:

- public issue reports from agent frameworks and SDKs;
- official evaluation guidance from model/application vendors;
- practitioner discussions on Hacker News and technical forums;
- current open-source testing, simulation, runtime guard, and observability
  projects;
- property-based and stateful-testing research.

This is directional market and technical validation, not proof of product-market
fit. Public issue trackers contain selection bias, several reports promote the
author's own tool, and teams with mature internal systems may not discuss them
publicly. These limitations inform the adoption gates in `TASKS.md`.

## What engineers are reporting

### Real side effects are replayed after retries and interruptions

| Evidence | Reported failure | Product implication |
|---|---|---|
| LangGraph issue #7417 | Long tool calls are silently re-dispatched while the original is still running, producing 2–3× redundant work and cost. | Test checkpoint/re-dispatch semantics against final business state. |
| Microsoft Agent Framework issue #3938 | Resume from the last checkpoint replays tool calls that already completed and produced real-world effects. | Model the commit boundary independently of the workflow checkpoint. |
| LiveKit Agents issue #3702 | A user interruption loses completed tool-call results, so the next turn executes them again. | Include interruption and missing-acknowledgement schedules. |
| Stripe AI issue #402 | Agent-level retry after a timeout can create a second charge because a new invocation receives a new idempotency key. | The initial reference case should be a lost acknowledgement and duplicate financial effect. |
| CrewAI issue #5802 | Task retry can re-execute payments, emails, or trades after the first call completed. | Keep the engine framework-neutral; this is not one framework's bug. |

Sources:

- https://github.com/langchain-ai/langgraph/issues/7417
- https://github.com/microsoft/agent-framework/issues/3938
- https://github.com/livekit/agents/issues/3702
- https://github.com/stripe/ai/issues/402
- https://github.com/crewAIInc/crewAI/issues/5802

The reports do not prove frequency across all deployments. They do establish a
repeatable failure class across independent runtimes: a real effect commits, the
agent loses authoritative knowledge of that commit, and orchestration retries.

### Agent teams need state-aware, end-to-end evaluation

Anthropic's agent-evaluation guidance distinguishes a transcript from the
outcome in the environment: an agent can claim a booking or refund succeeded
while the database state says otherwise. It recommends combining code-based
state checks with transcript/tool analysis.

- https://www.anthropic.com/engineering/demystifying-evals-for-ai-agents

Vercel's agent-evaluation guidance similarly argues that single-turn
prompt/response evaluation does not establish correct tool sequencing or
workflow completion, and recommends deterministic code checks where possible.

- https://vercel.com/blog/eval-driven-development-build-better-ai-faster

This supports outcome contracts, but it also means **stateful evals alone are not
novel**. The differentiator must be the combination of commit-aware fault
semantics and same-signature reduced cases.

### Practitioners still describe debugging and evals as bespoke

Recent Hacker News launches and discussions repeatedly describe teams building
custom tracing, simulation, and evaluation systems because ordinary prompt
playgrounds and single-turn tools do not capture tools, memory, events, and full
session behavior. They also show a crowded vendor category.

Representative threads:

- Lucidic: https://news.ycombinator.com/item?id=44735843
- Cekura: https://news.ycombinator.com/item?id=47232903
- Confident AI / DeepEval: https://news.ycombinator.com/item?id=43116633
- Gentrace end-to-end app evals: https://news.ycombinator.com/item?id=42381139

The conclusion is not “build another dashboard.” It is that a small,
composable developer primitive has a better chance of adoption than a new
all-in-one platform.

## Competitive pressure test

### Crowded categories we should not enter

| Category | Examples | Why not compete directly |
|---|---|---|
| General LLM/agent evals | DeepEval, Promptfoo, Inspect, Attest | Mature assertion, dataset, and judge ecosystems. |
| Tracing/observability | LangSmith, Langfuse, Braintrust, Lucidic | Strong incumbents; not the unique problem. |
| Living/stateful environments | Terrarium, Mimic, Archal, browser/operator benchmarks | Valuable backends and integration targets, not a moat by themselves. |
| Runtime idempotency/governance | SafeAgent, agent-ledger, authorization middleware | Prevents effects in production; our layer should test implementations and recovery behavior. |
| Verified agent runtimes | Temper, Stately Agent and framework-specific state machines | Powerful but tied to their execution/spec model. |
| Chaos proxies | Faultkit and transport/MCP fault injectors | Useful source of low-level failures, but generally unaware of business commit position. |

### Narrow gap

The alpha should own this workflow:

1. Define a valid relational world and actor.
2. Mark the durable business commit boundary inside an operation.
3. Generate semantic ambiguity such as timeout-before or timeout-after-commit.
4. Run any agent/framework through an adapter.
5. Check final state, access behavior, and audit events with deterministic code.
6. Remove unrelated faults, records, fields, turns, or schedule elements until
   no smaller same-signature candidate is found by the configured reducers and
   budgets.
7. Persist the case as a local regression artifact.

The closest alternatives cover pieces of this. The project should avoid claims
that no other tool supports state, simulation, faults, or shrinking. Its claim is
about the integrated, framework-neutral transaction-testing primitive.

## Why property-based testing is the right foundation

Hypothesis and related stateful/property-based systems demonstrate a productive
developer experience: generate many valid cases, discover an unexpected
failure, and shrink it into a small counterexample. Recent work also applies
property-based and metamorphic testing to stateful protocols and AI-generated
tests.

Sources:

- https://hypothesis.readthedocs.io/en/latest/
- https://www.anthropic.com/research/property-based-testing
- https://arxiv.org/abs/2506.06056

The important adaptation is that an agent case is not only a primitive input. It
contains a world, identity, permissions, goal, fault schedule, and sometimes a
concurrent event history. Domain validity therefore has to be first-class.

## R&D result included in this repository

The refund reference domain creates four deterministic agent behaviors:

- a naive retry implementation that changes idempotency keys;
- a stable-idempotency implementation;
- a reconciliation implementation;
- an implementation that succeeds operationally but overreads sensitive data.

Under `timeout_after_commit`, the naive implementation returns a success message
and leaves two refunds. The two robust implementations pass through different
safe trajectories, and the overreading implementation fails a least-privilege
contract. The shrinker removes unrelated world records and faults while
preserving the failure signature.

Run:

```bash
agent-effects demo --agent naive
agent-effects demo --agent idempotent
agent-effects demo --agent reconcile
agent-effects demo --agent overreading --fault none
```

## Decision and product constraints

Proceed because:

- the failure class is independently visible across multiple frameworks;
- official guidance validates final-state contracts;
- the general eval/observability market is crowded enough to reward a smaller
  interoperable primitive;
- the technical spike distinguishes unsafe and safe recovery paths without an
  LLM judge;
- a reduced, portable failure bundle is an immediately useful engineering artifact.

Constrain the alpha because:

- desk research cannot prove willingness to adopt;
- instrumenting commit boundaries may require domain-specific work;
- runtime guards may solve some failures before testing;
- integrations can become a maintenance trap;
- shrinking distributed/concurrent worlds is technically difficult.

## Falsification plan

The thesis is materially strengthened only when independent teams use it. The
project should not broaden until it reaches the adoption gates in `TASKS.md`:
three teams encode real contracts, two retain the testkit in CI, and one keeps a
reduced bundle as a regression test.

Reconsider or pivot when shrinking does not simplify real failures, state reset
is consistently too expensive, or established eval platforms ship the same
commit-aware cross-framework primitive.
