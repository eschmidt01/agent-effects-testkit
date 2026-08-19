from __future__ import annotations

import asyncio

from agent_effects import (
    AgentRun,
    CallableAgentAdapter,
    FaultMode,
    FaultRule,
    TestCase,
    TrialResult,
    TrialRunner,
)
from agent_effects.models import JsonObject
from agent_effects.world import BaseWorld


class DiagnosticWorld(BaseWorld):
    async def snapshot(self) -> JsonObject:
        return {"ok": True}

    async def call_without_commit(self, operation: str) -> None:
        async with self.faults.operation(operation):
            pass


def _run(case: TestCase, operation: str | None) -> TrialResult:
    async def agent(_case: TestCase, world: DiagnosticWorld) -> AgentRun:
        if operation is not None:
            await world.call_without_commit(operation)
        return AgentRun(status="completed")

    return asyncio.run(
        TrialRunner().run(
            case=case,
            world_factory=DiagnosticWorld,
            agent=CallableAgentAdapter("diagnostic", agent),
            contracts=(),
            write_failure=False,
        )
    )


def test_diagnostic_explains_operation_never_executed_or_instrumented() -> None:
    case = TestCase(
        id="never",
        faults=(FaultRule(operation="expected_write", mode=FaultMode.TIMEOUT_BEFORE),),
    )
    result = _run(case, None)
    violation = result.contracts.violations[0]
    assert violation.code == "fault_target_not_observed"
    assert "never executed" in violation.message
    assert "instrumented" in violation.message


def test_diagnostic_reports_operation_name_mismatch_with_observed_names() -> None:
    case = TestCase(
        id="mismatch",
        faults=(FaultRule(operation="expected_write", mode=FaultMode.TIMEOUT_BEFORE),),
    )
    result = _run(case, "actual_write")
    message = result.contracts.violations[0].message
    assert "expected_write" in message
    assert "actual_write" in message
    assert "operation name" in message


def test_diagnostic_explains_missing_commit_marker() -> None:
    case = TestCase(
        id="missing-commit",
        faults=(FaultRule(operation="expected_write", mode=FaultMode.TIMEOUT_AFTER_COMMIT),),
    )
    result = _run(case, "expected_write")
    messages = [item.message for item in result.contracts.violations]
    assert any("never called mark_committed" in message for message in messages)
    assert any("durable business write" in message for message in messages)
