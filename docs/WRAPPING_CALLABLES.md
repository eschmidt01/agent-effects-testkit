# Wrap an existing callable agent

`CallableAgentAdapter` is the framework-neutral first integration point. The
callable receives the portable `TestCase` and your isolated world adapter, then
returns `AgentRun`.

```python
from agent_effects import AgentRun, CallableAgentAdapter


async def invoke_application_agent(case, world):
    text = await application_agent(case.goal, tools=world)
    return AgentRun(status="completed", output=text)


adapter = CallableAgentAdapter("application-agent", invoke_application_agent)
```

Synchronous callables are also accepted. The world factory, snapshots, cleanup,
and agent may independently be synchronous or asynchronous.

Keep application credentials outside `TestCase`: cases, traces, schemas, and
bundles are portable JSON. Use a test account and an adapter that can reset and
snapshot the affected state. Do not point intentional retry tests at production.

Run the adapter from pytest:

```python
def test_lost_ack(agent_effects_runner):
    result = agent_effects_runner.run_sync(
        case=case,
        world_factory=ApplicationWorld,
        agent=adapter,
        contracts=(one_business_effect,),
        reproducer_id="my-package/application-agent/v1",
    )
    assert result.passed, result.contracts.violations
```

Register reproducible application code through the
`agent_effects.reproducers` package entry-point group. Bundle data is never used
as an arbitrary import path.
