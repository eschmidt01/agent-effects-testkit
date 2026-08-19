from __future__ import annotations

import asyncio
from dataclasses import dataclass
from pathlib import Path
from typing import cast

import pytest

import agent_effects.reproduction as reproduction
from agent_effects.artifacts import FailureBundle, FailureStore
from agent_effects.examples.refund import (
    AGENTS,
    REFUND_CONTRACTS,
    RefundWorld,
    make_refund_case,
)
from agent_effects.models import FaultMode, TestCase, TrialResult
from agent_effects.reproduction import Reproducer, ReproductionError
from agent_effects.runner import TrialRunner


def _trial(agent: str = "naive", *, reproducer_id: str | None = None) -> TrialResult:
    return TrialRunner().run_sync(
        case=make_refund_case(fault_mode=FaultMode.TIMEOUT_AFTER_COMMIT),
        world_factory=RefundWorld,
        agent=AGENTS[agent],
        contracts=REFUND_CONTRACTS,
        write_failure=False,
        reproducer_id=reproducer_id,
    )


def test_callable_reproducer_accepts_sync_result_and_rejects_wrong_type() -> None:
    expected = _trial()
    actual = asyncio.run(reproduction._run_callable(lambda _case: expected, expected.case))
    assert actual == expected

    invalid = cast(Reproducer, lambda _case: "not a result")
    with pytest.raises(ReproductionError, match="not TrialResult"):
        asyncio.run(reproduction._run_callable(invalid, expected.case))


def test_unknown_builtin_and_missing_registered_reproducers_fail_actionably() -> None:
    case = make_refund_case()
    with pytest.raises(ReproductionError, match="unknown built-in"):
        asyncio.run(
            reproduction.run_registered_reproducer(
                "agent-effects.examples.refund/missing/v1",
                case,
            )
        )
    with pytest.raises(ReproductionError, match="no unique installed reproducer"):
        asyncio.run(reproduction.run_registered_reproducer("missing-plugin", case))


@dataclass(frozen=True)
class FakeEntryPoint:
    name: str
    loaded: object

    def load(self) -> object:
        return self.loaded


def test_dry_run_inspection_does_not_load_entry_point(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    entry = FakeEntryPoint("fake", object())
    monkeypatch.setattr(reproduction, "entry_points", lambda **_kwargs: [entry])
    monkeypatch.setattr(
        FakeEntryPoint,
        "load",
        lambda _self: pytest.fail("dry-run inspection loaded reproducer code"),
    )

    description = reproduction.inspect_registered_reproducer("fake")
    assert "installed entry point" in description


def test_entry_point_reproducer_must_be_callable(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        reproduction,
        "entry_points",
        lambda **_kwargs: [FakeEntryPoint("fake", object())],
    )
    with pytest.raises(ReproductionError, match="not callable"):
        asyncio.run(reproduction.run_registered_reproducer("fake", make_refund_case()))


def test_entry_point_reproducer_can_return_a_trial_result(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    expected = _trial()
    monkeypatch.setattr(
        reproduction,
        "entry_points",
        lambda **_kwargs: [FakeEntryPoint("fake", lambda _case: expected)],
    )
    actual = asyncio.run(reproduction.run_registered_reproducer("fake", make_refund_case()))
    assert actual == expected


def test_bundle_without_reproducer_cannot_execute(tmp_path: Path) -> None:
    bundle = FailureBundle.load(FailureStore(tmp_path).write(_trial()))
    with pytest.raises(ReproductionError, match="does not declare"):
        asyncio.run(reproduction.reproduce_bundle(bundle))


def test_reproduction_reports_signature_mismatch(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    identifier = "agent-effects.examples.refund/naive/v1"
    bundle = FailureBundle.load(FailureStore(tmp_path).write(_trial(reproducer_id=identifier)))

    async def different_result(_identifier: str, _case: TestCase) -> TrialResult:
        return await TrialRunner().run(
            case=make_refund_case(fault_mode=FaultMode.TIMEOUT_AFTER_COMMIT),
            world_factory=RefundWorld,
            agent=AGENTS["idempotent"],
            contracts=REFUND_CONTRACTS,
            write_failure=False,
            reproducer_id=identifier,
        )

    monkeypatch.setattr(reproduction, "run_registered_reproducer", different_result)
    outcome = asyncio.run(reproduction.reproduce_bundle(bundle))

    assert outcome.matched is False
    assert outcome.expected_signature != outcome.actual_signature
