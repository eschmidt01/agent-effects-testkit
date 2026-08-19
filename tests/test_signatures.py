from __future__ import annotations

from agent_effects.models import (
    AdapterInfo,
    AgentRun,
    ContractReport,
    ContractViolation,
    FailureCategory,
    FailureStage,
    LifecycleFailure,
    TestCase,
    TrialResult,
)
from agent_effects.signatures import extract_failure_signature


def _result(
    violations: tuple[ContractViolation, ...],
    lifecycle: tuple[LifecycleFailure, ...] = (),
) -> TrialResult:
    return TrialResult(
        case=TestCase(id="signature"),
        agent_name="test",
        adapter=AdapterInfo(name="test"),
        initial_state={},
        final_state={},
        events=(),
        agent_run=AgentRun(status="completed"),
        contracts=ContractReport(passed=False, violations=violations),
        lifecycle_failures=lifecycle,
        elapsed_ms=0,
    )


def test_contract_signature_is_sorted_and_preserves_multiplicity() -> None:
    result = _result(
        (
            ContractViolation(code="z", message="dynamic 1", contract="b"),
            ContractViolation(code="a", message="dynamic 2", contract="a"),
            ContractViolation(code="a", message="dynamic 3", contract="a"),
        )
    )
    signature = extract_failure_signature(result)
    assert signature.primary_category == "contract"
    assert [
        (item.contract_id, item.violation_code, item.count) for item in signature.contract_failures
    ] == [("a", "a", 2), ("b", "z", 1)]
    assert "dynamic" not in signature.model_dump_json()


def test_lifecycle_signature_excludes_message_and_contract_noise() -> None:
    lifecycle = LifecycleFailure(
        stage=FailureStage.FINAL_SNAPSHOT,
        category=FailureCategory.INFRASTRUCTURE,
        exception_type="ConnectionError",
        message="/machine/specific/path and dynamic value 42",
        primary=True,
    )
    signature = extract_failure_signature(
        _result(
            (
                ContractViolation(
                    code="runner_final_snapshot", message="ignored", contract="runner"
                ),
            ),
            (lifecycle,),
        )
    )
    assert signature.primary_stage is FailureStage.FINAL_SNAPSHOT
    assert signature.primary_category == "infrastructure"
    assert signature.exception_type == "ConnectionError"
    assert signature.contract_failures == ()
    assert "machine" not in signature.model_dump_json()
