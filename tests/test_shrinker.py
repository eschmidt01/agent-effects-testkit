from __future__ import annotations

import asyncio

from agent_effects.examples.refund import (
    AGENTS,
    REFUND_CONTRACTS,
    RefundWorld,
    is_valid_refund_case,
    make_refund_case,
)
from agent_effects.models import FaultMode, FaultRule, TestCase
from agent_effects.runner import TrialRunner
from agent_effects.shrink import (
    GreedyShrinker,
    ReduceWorldListReducer,
    RemoveFaultReducer,
)


def test_shrinker_removes_irrelevant_world_and_faults() -> None:
    case = make_refund_case(
        fault_mode=FaultMode.TIMEOUT_AFTER_COMMIT,
        noise_records=20,
        extra_faults=(FaultRule(operation="unused_lookup", mode=FaultMode.TIMEOUT_BEFORE),),
    )
    runner = TrialRunner()

    async def scenario() -> None:
        original = await runner.run(
            case=case,
            world_factory=RefundWorld,
            agent=AGENTS["naive"],
            contracts=REFUND_CONTRACTS,
            write_failure=False,
        )
        assert not original.passed
        target = original.signature

        async def still_fails(candidate: TestCase) -> bool:
            result = await runner.run(
                case=candidate,
                world_factory=RefundWorld,
                agent=AGENTS["naive"],
                contracts=REFUND_CONTRACTS,
                write_failure=False,
            )
            return set(target).issubset(result.signature)

        report = await GreedyShrinker().shrink(
            case=case,
            target_signature=target,
            still_fails=still_fails,
            reducers=(RemoveFaultReducer(), ReduceWorldListReducer(("noise",))),
            is_valid=is_valid_refund_case,
        )
        assert report.minimized.world["noise"] == []
        assert report.minimized.faults == (
            FaultRule(operation="issue_refund", mode=FaultMode.TIMEOUT_AFTER_COMMIT),
        )
        assert report.accepted_steps

    asyncio.run(scenario())


def test_shrinker_rejects_invalid_configuration_and_initial_cases() -> None:
    import pytest

    with pytest.raises(ValueError, match="positive"):
        GreedyShrinker(max_evaluations=0)

    case = make_refund_case(fault_mode=None)

    async def scenario() -> None:
        with pytest.raises(ValueError, match="initial case is invalid"):
            await GreedyShrinker().shrink(
                case=case,
                target_signature=("failure",),
                still_fails=lambda _candidate: _return_bool(True),
                reducers=(),
                is_valid=lambda _candidate: False,
            )

        with pytest.raises(ValueError, match="does not satisfy"):
            await GreedyShrinker().shrink(
                case=case,
                target_signature=("failure",),
                still_fails=lambda _candidate: _return_bool(False),
                reducers=(),
            )

    async def _return_bool(value: bool) -> bool:
        return value

    asyncio.run(scenario())


def test_world_reducers_validate_paths_and_only_emit_changes() -> None:
    import pytest

    from agent_effects.shrink import SetWorldValueReducer

    case = make_refund_case(fault_mode=None, noise_records=1)
    values = list(SetWorldValueReducer(("approvals", "pay-001"), (True, False)).candidates(case))
    assert len(values) == 1
    approvals = values[0].world["approvals"]
    assert isinstance(approvals, dict)
    assert approvals["pay-001"] is False

    with pytest.raises(TypeError, match="is not a list"):
        list(ReduceWorldListReducer(("approvals",)).candidates(case))
