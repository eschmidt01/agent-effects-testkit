from __future__ import annotations

import asyncio

from agent_effects.examples.refund import (
    AGENTS,
    REFUND_CONTRACTS,
    RefundWorld,
    generated_refund_cases,
    make_refund_case,
)
from agent_effects.models import FaultMode, JsonValue, TrialResult
from agent_effects.runner import TrialRunner


def run(
    agent: str,
    *,
    fault_mode: FaultMode | None = FaultMode.TIMEOUT_AFTER_COMMIT,
    approved: bool = True,
    authorized: bool = True,
) -> TrialResult:
    return asyncio.run(
        TrialRunner().run(
            case=make_refund_case(
                fault_mode=fault_mode,
                approved=approved,
                authorized=authorized,
            ),
            world_factory=RefundWorld,
            agent=AGENTS[agent],
            contracts=REFUND_CONTRACTS,
            write_failure=False,
        )
    )


def refunds(result: TrialResult) -> list[JsonValue]:
    assert result.final_state is not None
    value = result.final_state["refunds"]
    assert isinstance(value, list)
    return value


def test_naive_retry_looks_successful_but_duplicates_refund() -> None:
    result = run("naive", fault_mode=FaultMode.TIMEOUT_AFTER_COMMIT)
    assert result.agent_run is not None
    assert result.agent_run.status == "completed"
    assert "completed" in result.agent_run.output.lower()
    assert result.passed is False
    assert "refund_cardinality" in result.signature
    assert "duplicate_business_effect" in result.signature
    assert len(refunds(result)) == 2


def test_stable_idempotency_survives_each_initial_fault_mode() -> None:
    for mode in (None, FaultMode.TIMEOUT_BEFORE, FaultMode.TIMEOUT_AFTER_COMMIT):
        result = run("idempotent", fault_mode=mode)
        assert result.passed, result.contracts.violations
        assert len(refunds(result)) == 1


def test_reconciliation_is_a_different_valid_trajectory() -> None:
    stable = run("idempotent", fault_mode=FaultMode.TIMEOUT_AFTER_COMMIT)
    reconciled = run("reconcile", fault_mode=FaultMode.TIMEOUT_AFTER_COMMIT)
    assert stable.passed
    assert reconciled.passed
    stable_ops = [(event.kind, event.operation) for event in stable.events]
    reconciled_ops = [(event.kind, event.operation) for event in reconciled.events]
    assert stable_ops != reconciled_ops


def test_least_privilege_contract_catches_overreading() -> None:
    result = run("overreading", fault_mode=None)
    assert result.agent_run is not None
    assert result.agent_run.status == "completed"
    assert result.passed is False
    assert result.signature == ("least_privilege_read",)


def test_no_refund_without_approval_or_authorization() -> None:
    for approved, authorized in ((False, True), (True, False), (False, False)):
        result = run(
            "idempotent",
            fault_mode=None,
            approved=approved,
            authorized=authorized,
        )
        assert result.passed, result.contracts.violations
        assert result.agent_run is not None
        assert result.agent_run.status == "blocked"
        assert refunds(result) == []


def test_generated_worlds_are_valid_and_robust_agent_passes() -> None:
    for case in generated_refund_cases(100):
        result = asyncio.run(
            TrialRunner().run(
                case=case,
                world_factory=RefundWorld,
                agent=AGENTS["idempotent"],
                contracts=REFUND_CONTRACTS,
                write_failure=False,
            )
        )
        assert result.passed, (case, result.contracts.violations)
