from __future__ import annotations

import asyncio
from pathlib import Path

import pytest

from agent_effects.adapters import CallableAgentAdapter
from agent_effects.contracts import PredicateContract
from agent_effects.models import AgentRun, JsonObject, TestCase
from agent_effects.runner import TrialRunner
from agent_effects.world import BaseWorld


class RecordingWorld(BaseWorld):
    def __init__(self, case: TestCase) -> None:
        super().__init__(case)
        self.state: JsonObject = {"writes": []}
        self.close_count = 0

    async def snapshot(self) -> JsonObject:
        writes = self.state["writes"]
        assert isinstance(writes, list)
        return {"writes": list(writes)}

    async def close(self) -> None:
        self.close_count += 1


def test_agent_exception_preserves_final_state_and_closes_world() -> None:
    worlds: list[RecordingWorld] = []

    def factory(case: TestCase) -> RecordingWorld:
        world = RecordingWorld(case)
        worlds.append(world)
        return world

    async def crash(_case: TestCase, world: RecordingWorld) -> AgentRun:
        writes = world.state["writes"]
        assert isinstance(writes, list)
        writes.append("committed-before-crash")
        raise LookupError("subject failed")

    result = asyncio.run(
        TrialRunner().run(
            case=TestCase(id="crash"),
            world_factory=factory,
            agent=CallableAgentAdapter("crashing-agent", crash),
            contracts=(),
            write_failure=False,
        )
    )

    assert result.agent_run is not None
    assert result.agent_run.status == "error"
    assert result.agent_run.error_type == "LookupError"
    assert result.final_state == {"writes": ["committed-before-crash"]}
    assert result.signature == ("agent_error",)
    assert worlds[0].close_count == 1


def test_runner_writes_failed_contract_bundle(tmp_path: Path) -> None:
    agent: CallableAgentAdapter[RecordingWorld] = CallableAgentAdapter(
        "string-agent", lambda _case, _world: "done"
    )
    failing = PredicateContract(
        name="always fails",
        code="expected_failure",
        message="intentional",
        predicate=lambda _context: False,
    )

    result = asyncio.run(
        TrialRunner(artifact_dir=tmp_path).run(
            case=TestCase(id="auto-artifact"),
            world_factory=RecordingWorld,
            agent=agent,
            contracts=(failing,),
        )
    )

    assert result.artifact_path is not None
    assert Path(result.artifact_path, "manifest.json").is_file()


def test_run_sync_outside_and_inside_event_loop() -> None:
    runner = TrialRunner()
    agent: CallableAgentAdapter[RecordingWorld] = CallableAgentAdapter(
        "sync", lambda _case, _world: "ok"
    )
    case = TestCase(id="sync")

    assert runner.run_sync(
        case=case,
        world_factory=RecordingWorld,
        agent=agent,
        contracts=(),
        write_failure=False,
    ).passed

    async def inside_loop() -> None:
        with pytest.raises(RuntimeError, match="active event loop"):
            runner.run_sync(
                case=case,
                world_factory=RecordingWorld,
                agent=agent,
                contracts=(),
                write_failure=False,
            )

    asyncio.run(inside_loop())
