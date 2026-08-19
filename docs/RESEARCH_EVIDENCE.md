# Public engineering evidence

**Collected:** 2026-08-19

**Purpose:** Validate the first product wedge using public reports before coding
agents expand the implementation.

The machine-readable source log is in
[`research/evidence.csv`](research/evidence.csv). It records public issue
reports, official guidance, and practitioner discussions. It is not a claim
that every report is independently reproduced or that issue frequency equals
market size.

## Strongest recurring failure pattern

Across independent agent runtimes, the same distributed-systems ambiguity shows
up in different forms:

1. a tool produces a durable real-world effect;
2. the acknowledgement, checkpoint, tool result, or session state is lost;
3. the orchestrator or model believes the action may not have happened;
4. a retry or resume re-executes the effect;
5. the transcript can still look plausible while the external state is wrong.

High-signal examples include:

- LiveKit production logs showing an interrupted reservation flow create two
  orders after the first completed tool result was omitted from history;
- LangGraph reports of long tool calls being dispatched again from a checkpoint
  while the original run was still active;
- Microsoft Agent Framework reports of completed external effects replaying when
  execution resumes from the last successful checkpoint;
- Microsoft Agent Framework approval/session mismatch losing tool-call state and
  triggering repeated calls;
- Warp reports of commands that already executed being surfaced to the agent as
  cancelled, which invites duplicate retries.

This is the reason the alpha starts with a **commit-aware lost acknowledgement**
rather than a broad collection of generic HTTP failures.

## What forum discussions add

Forum and launch discussions are weaker evidence than reproducible issues, but
they help identify product shape:

- engineers describe testing against real APIs as flaky, slow, rate-limited, and
  hard to reproduce;
- practitioners report failures that only become visible across a full session,
  not in one prompt or tool call;
- comments repeatedly ask how to verify dangerous tool selection and incomplete
  verification flows;
- the same discussions describe agent observability and general eval platforms
  as crowded.

That combination argues for a composable local test primitive, not another
hosted trace dashboard.

## Official engineering guidance

Anthropic's agent-evaluation guidance explicitly separates the transcript from
the outcome: an agent can claim an action succeeded while the environment's
final state shows otherwise. It also recommends deterministic graders where
possible and warns against over-constraining one exact valid trajectory.

Hypothesis demonstrates the developer experience this project should adapt:
generate valid cases, discover a counterexample, and reduce it to a simple
reproducer. Agent Effects applies that workflow to a composite input containing
world state, identity, permissions, fault schedule, and potentially concurrent
events.

## Competitive interpretation

The research did **not** validate these as distinctive products:

- a general agent eval framework;
- a trace/replay UI;
- a stateful mock environment by itself;
- a generic network or MCP chaos proxy;
- a production idempotency runtime.

Those categories already have active open-source and commercial projects.
Agent Effects should integrate with them while owning the narrower test loop:

```text
valid world
+ explicit business commit boundary
+ semantic ambiguity
+ deterministic state/access contracts
+ validity-preserving reduction
= portable reduced regression case
```

## Confidence assessment

| Claim | Confidence | Why |
|---|---|---|
| Duplicate/replayed side effects are a real agent-engineering failure class. | High | Independent issue reports include logs, concrete reproductions, and multiple runtimes. |
| Final-state contracts are necessary for useful agent evaluation. | High | Official guidance and production reports agree. |
| The general eval/observability market is crowded. | High | Numerous established products and direct practitioner comments. |
| Commit-aware shrinking is sufficiently differentiated for an OSS wedge. | Medium | Adjacent tools cover parts; no mature project found with this exact integrated center of gravity. |
| Teams will adopt this particular API and instrument commit boundaries. | Unknown | Desk research cannot replace real usage; adoption gates remain in `TASKS.md`. |

## Research rules for future agents

When updating this evidence:

1. prefer reports with reproductions, logs, maintainer acknowledgement, or a
   linked fix;
2. distinguish one reporter's claim from independently confirmed behavior;
3. record publication date and current issue status;
4. separate runtime-prevention products from pre-production testing tools;
5. do not claim product-market fit from stars, launches, or issue counts;
6. add new sources to the CSV before changing the product thesis.
