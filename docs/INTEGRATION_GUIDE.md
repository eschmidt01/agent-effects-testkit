# Integration guide

## 1. Choose one side-effecting workflow

Start with a workflow whose correctness can be inspected deterministically:
refund, message send, case creation, permission update, deployment, or durable
analysis task. Avoid beginning with subjective response quality.

## 2. Define a portable case

```python
from agent_effects import FaultMode, FaultRule, TestCase

case = TestCase(
    id="case-create-lost-ack",
    actor={"id": "employee-42", "roles": ["employee"]},
    goal={"type": "create_case", "category": "leave"},
    world={"approvals": {"employee-42": True}, "cases": []},
    faults=(
        FaultRule(
            operation="create_case",
            mode=FaultMode.TIMEOUT_AFTER_COMMIT,
            occurrence=1,
        ),
    ),
)
```

Keep secrets and live endpoints outside this model.

## 3. Implement the world

Subclass `BaseWorld` or implement the `World` protocol. Operations must record
the durable business boundary:

```python
async def create_case(self, payload, idempotency_key):
    async with self.faults.operation(
        "create_case",
        idempotency_key=idempotency_key,
    ) as effect:
        row = await self.repository.insert(payload)
        effect.mark_committed(case_id=row.id)
        return row
```

Do not call `mark_committed()` after merely sending a request unless that request
is itself the durable effect. Place it after the point the operation cannot be
assumed absent.

## 4. Provide a validity predicate

```python
def is_valid(case: TestCase) -> bool:
    employee_ids = {row["id"] for row in case.world["employees"]}
    return case.actor["id"] in employee_ids
```

The predicate should enforce relational and policy preconditions. A shrinker
without this guard can manufacture impossible failures.

## 5. Adapt the agent

For ordinary Python:

```python
from agent_effects import AgentRun, CallableAgentAdapter


async def run_agent(case, world):
    output = await application_agent(case.goal, tools=world)
    return AgentRun(status="completed", output=output)


adapter = CallableAgentAdapter("application-agent", run_agent)
```

Framework integrations should live in optional modules and translate their
result into `AgentRun`; business tools still point at the instrumented world.

## 6. Write outcome contracts

```python
from agent_effects import ContractViolation, EvaluationContext, contract


@contract("one leave case")
def one_case(ctx: EvaluationContext):
    rows = [row for row in ctx.final_state["cases"] if row["employee_id"] == ctx.case.actor["id"]]
    if len(rows) == 1:
        return []
    return [
        ContractViolation(
            code="case_cardinality",
            message="Expected exactly one leave case.",
            contract="one leave case",
            path="$.cases",
        )
    ]
```

Use stable violation codes. Prefer domain business keys over request IDs when
checking uniqueness.

## 7. Run from pytest

```python
def test_case_creation(agent_effects_runner):
    result = agent_effects_runner.run_sync(
        case=case,
        world_factory=CaseWorld,
        agent=adapter,
        contracts=(one_case,),
    )
    assert_contracts(result)
```

## 8. Add shrink reducers

Select reducers that remove unrelated records, faults, actor attributes, or goal
fields while preserving validity. The failure predicate should retain the
original signature rather than merely “any failure.”

## 9. Promote reduced failures

Store the bundle as a restricted CI artifact and verify it before use:

```bash
agent-effects bundle verify ./failure-bundle
agent-effects bundle inspect ./failure-bundle
agent-effects reproduce ./failure-bundle
```

Reproduction requires a built-in or installed registered reproducer ID. Once the
bundle is reviewed and sanitized, copy the reduced case from the compatibility
filename `minimized-case.json` into a regression
fixture and run it on every relevant change.
