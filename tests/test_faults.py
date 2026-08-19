from __future__ import annotations

import asyncio

import pytest

from agent_effects.faults import FaultInjector, SemanticFault
from agent_effects.models import EventKind, FaultMode, FaultRule
from agent_effects.trace import EventRecorder


def test_timeout_before_never_reaches_commit() -> None:
    recorder = EventRecorder()
    injector = FaultInjector(
        (FaultRule(operation="charge", mode=FaultMode.TIMEOUT_BEFORE),),
        recorder,
    )

    async def run() -> None:
        with pytest.raises(SemanticFault) as captured:
            async with injector.operation("charge") as effect:
                effect.mark_committed()
        assert captured.value.committed is False

    asyncio.run(run())
    assert [event.kind for event in recorder.events] == [
        EventKind.TOOL_CALL,
        EventKind.FAULT,
    ]


def test_timeout_after_commit_records_commit_before_fault() -> None:
    recorder = EventRecorder()
    injector = FaultInjector(
        (FaultRule(operation="charge", mode=FaultMode.TIMEOUT_AFTER_COMMIT),),
        recorder,
    )

    async def run() -> None:
        with pytest.raises(SemanticFault) as captured:
            async with injector.operation("charge") as effect:
                effect.mark_committed(receipt_id="r-1")
        assert captured.value.committed is True

    asyncio.run(run())
    assert [event.kind for event in recorder.events] == [
        EventKind.TOOL_CALL,
        EventKind.COMMIT,
        EventKind.FAULT,
    ]


def test_regular_operation_error_is_traced_and_propagated() -> None:
    recorder = EventRecorder()
    injector = FaultInjector((), recorder)

    async def run() -> None:
        with pytest.raises(ValueError, match="application failure"):
            async with injector.operation("write"):
                raise ValueError("application failure")

    asyncio.run(run())
    assert [event.kind for event in recorder.events] == [
        EventKind.TOOL_CALL,
        EventKind.ERROR,
    ]
    assert recorder.events[-1].data["error_type"] == "ValueError"
    assert injector.attempts("write") == 1


def test_timeout_after_commit_requires_commit_marker() -> None:
    recorder = EventRecorder()
    injector = FaultInjector(
        (FaultRule(operation="write", mode=FaultMode.TIMEOUT_AFTER_COMMIT),),
        recorder,
    )

    async def run() -> None:
        with pytest.raises(RuntimeError, match="requires mark_committed"):
            async with injector.operation("write"):
                pass

    asyncio.run(run())


def test_operation_cannot_be_marked_committed_twice() -> None:
    recorder = EventRecorder()
    injector = FaultInjector((), recorder)

    async def run() -> None:
        with pytest.raises(RuntimeError, match="more than once"):
            async with injector.operation("write") as effect:
                effect.mark_committed()
                effect.mark_committed()

    asyncio.run(run())
    assert recorder.events[-1].kind is EventKind.ERROR


def test_fault_injector_rejects_duplicate_operation_occurrences() -> None:
    recorder = EventRecorder()
    rule = FaultRule(operation="write", mode=FaultMode.TIMEOUT_BEFORE)
    with pytest.raises(ValueError, match="only one fault"):
        FaultInjector((rule, rule), recorder)
