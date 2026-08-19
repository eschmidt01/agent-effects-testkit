from __future__ import annotations

import asyncio
from collections.abc import Sequence
from pathlib import Path

import pytest

from agent_effects.adapters import CallableAgentAdapter
from agent_effects.artifacts import FailureStore
from agent_effects.contracts import PredicateContract
from agent_effects.models import (
    AgentRun,
    ContractViolation,
    EvaluationContext,
    FailureStage,
    JsonObject,
    TestCase,
    TrialResult,
)
from agent_effects.protocols import AgentAdapter, Contract, World, WorldFactory
from agent_effects.runner import TrialRunner
from agent_effects.trace import EventRecorder


class MatrixWorld:
    def __init__(
        self,
        *,
        fail_snapshot: int | None = None,
        fail_close: bool = False,
    ) -> None:
        self.recorder = EventRecorder()
        self.fail_snapshot = fail_snapshot
        self.fail_close = fail_close
        self.snapshot_count = 0
        self.close_count = 0

    async def snapshot(self) -> JsonObject:
        self.snapshot_count += 1
        if self.snapshot_count == self.fail_snapshot:
            raise RuntimeError(f"snapshot {self.snapshot_count} failed")
        return {"snapshot": self.snapshot_count}

    async def close(self) -> None:
        self.close_count += 1
        if self.fail_close:
            raise RuntimeError("close failed")


def _completed_agent() -> CallableAgentAdapter[MatrixWorld]:
    return CallableAgentAdapter(
        "completed",
        lambda _case, _world: AgentRun(status="completed", output="done"),
    )


def _run(
    world_factory: WorldFactory,
    *,
    agent: AgentAdapter | None = None,
    contracts: Sequence[Contract] = (),
    artifact_dir: Path | None = None,
) -> TrialResult:
    return asyncio.run(
        TrialRunner(artifact_dir=artifact_dir).run(
            case=TestCase(id="lifecycle"),
            world_factory=world_factory,
            agent=agent or _completed_agent(),
            contracts=contracts,
            write_failure=artifact_dir is not None,
        )
    )


def test_world_creation_failure_returns_explicit_partial_result() -> None:
    def broken_factory(_case: TestCase) -> World:
        raise RuntimeError("world unavailable")

    result = _run(broken_factory)

    assert result.initial_state is None
    assert result.final_state is None
    assert result.agent_run is None
    assert result.primary_failure is not None
    assert result.primary_failure.stage is FailureStage.WORLD_CREATION
    assert result.signature == ("runner_world_creation",)


@pytest.mark.parametrize(
    ("snapshot_number", "stage"),
    [
        (1, FailureStage.INITIAL_SNAPSHOT),
        (2, FailureStage.FINAL_SNAPSHOT),
    ],
)
def test_snapshot_failures_are_distinct(snapshot_number: int, stage: FailureStage) -> None:
    worlds: list[MatrixWorld] = []

    def factory(_case: TestCase) -> MatrixWorld:
        world = MatrixWorld(fail_snapshot=snapshot_number)
        worlds.append(world)
        return world

    result = _run(factory)

    assert result.primary_failure is not None
    assert result.primary_failure.stage is stage
    assert worlds[0].close_count == 1
    if snapshot_number == 1:
        assert result.initial_state is None
        assert result.agent_run is None
        assert result.final_state == {"snapshot": 2}
    else:
        assert result.initial_state == {"snapshot": 1}
        assert result.final_state is None
        assert "Final snapshot was unavailable" in result.contracts.violations[0].message


def test_agent_failure_remains_primary_when_cleanup_also_fails() -> None:
    worlds: list[MatrixWorld] = []

    def factory(_case: TestCase) -> MatrixWorld:
        world = MatrixWorld(fail_close=True)
        worlds.append(world)
        return world

    async def broken_agent(_case: TestCase, _world: MatrixWorld) -> AgentRun:
        raise LookupError("agent failed")

    result = _run(factory, agent=CallableAgentAdapter("broken", broken_agent))

    assert [failure.stage for failure in result.lifecycle_failures] == [
        FailureStage.AGENT_EXECUTION,
        FailureStage.CLEANUP,
    ]
    assert [failure.primary for failure in result.lifecycle_failures] == [True, False]
    assert result.agent_run is not None
    assert result.agent_run.error_type == "LookupError"
    assert worlds[0].close_count == 1
    assert "earlier failure remains primary" in result.contracts.violations[-1].message


def test_agent_cancellation_becomes_a_structured_result() -> None:
    async def cancelled(_case: TestCase, _world: MatrixWorld) -> AgentRun:
        raise asyncio.CancelledError("cancelled by test")

    result = _run(
        lambda _case: MatrixWorld(),
        agent=CallableAgentAdapter("cancelled", cancelled),
    )

    assert result.primary_failure is not None
    assert result.primary_failure.stage is FailureStage.AGENT_EXECUTION
    assert result.primary_failure.exception_type == "CancelledError"


class BrokenContract:
    @property
    def name(self) -> str:
        raise RuntimeError("contract registry failed")

    def evaluate(self, _context: EvaluationContext) -> Sequence[ContractViolation]:
        return ()


def test_contract_orchestration_failure_is_structured() -> None:
    result = _run(lambda _case: MatrixWorld(), contracts=(BrokenContract(),))

    assert result.primary_failure is not None
    assert result.primary_failure.stage is FailureStage.CONTRACT_EVALUATION
    assert result.primary_failure.category.value == "contract"


def test_cleanup_failure_is_primary_after_successful_contracts() -> None:
    result = _run(lambda _case: MatrixWorld(fail_close=True))

    assert result.primary_failure is not None
    assert result.primary_failure.stage is FailureStage.CLEANUP
    assert result.agent_run is not None
    assert result.agent_run.status == "completed"


def test_artifact_failure_does_not_destroy_contract_result(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def broken_write(_store: FailureStore, _result: TrialResult) -> Path:
        raise OSError("artifact disk unavailable")

    monkeypatch.setattr(FailureStore, "write", broken_write)
    failing = PredicateContract(
        name="expected contract",
        code="expected_failure",
        message="expected",
        predicate=lambda _context: False,
    )

    result = _run(
        lambda _case: MatrixWorld(),
        contracts=(failing,),
        artifact_dir=tmp_path,
    )

    assert "expected_failure" in result.signature
    artifact_failure = result.lifecycle_failures[-1]
    assert artifact_failure.stage is FailureStage.ARTIFACT_GENERATION
    assert artifact_failure.primary is False
    assert result.artifact_path is None


class SyncWorld:
    def __init__(self) -> None:
        self.recorder = EventRecorder()
        self.closed = False

    def snapshot(self) -> JsonObject:
        return {"closed": self.closed}

    def close(self) -> None:
        self.closed = True


class SyncAgent:
    @property
    def name(self) -> str:
        return "sync-agent"

    def run(self, _case: TestCase, _world: World) -> AgentRun:
        return AgentRun(status="completed", output="sync")


def test_synchronous_world_factory_world_and_agent_are_supported() -> None:
    world = SyncWorld()
    result = _run(lambda _case: world, agent=SyncAgent())

    assert result.passed
    assert result.initial_state == {"closed": False}
    assert result.final_state == {"closed": False}
    assert world.closed is True


def test_monotonic_clock_is_injectable() -> None:
    readings = iter((10.0, 10.25))
    result = asyncio.run(
        TrialRunner(clock=lambda: next(readings)).run(
            case=TestCase(id="clock"),
            world_factory=lambda _case: MatrixWorld(),
            agent=_completed_agent(),
            contracts=(),
            write_failure=False,
        )
    )

    assert result.elapsed_ms == 250.0
