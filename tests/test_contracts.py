from __future__ import annotations

from agent_effects.contracts import PredicateContract, evaluate_contracts
from agent_effects.models import AgentRun, EvaluationContext, TestCase


def context() -> EvaluationContext:
    return EvaluationContext(
        case=TestCase(id="case"),
        agent_name="agent",
        agent_run=AgentRun(status="completed"),
        initial_state={},
        final_state={},
        events=(),
    )


def test_predicate_contract_passes_and_fails_deterministically() -> None:
    passing = PredicateContract("pass", "bad", "should pass", lambda _: True)
    failing = PredicateContract("fail", "expected_failure", "failed", lambda _: False)
    report = evaluate_contracts((passing, failing), context())
    assert report.passed is False
    assert report.codes == ("expected_failure",)


def test_contract_exception_fails_closed() -> None:
    broken = PredicateContract(
        "broken",
        "unused",
        "unused",
        lambda _: (_ for _ in ()).throw(RuntimeError("oracle bug")),
    )
    report = evaluate_contracts((broken,), context())
    assert report.codes == ("contract_error",)
