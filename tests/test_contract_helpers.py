from __future__ import annotations

from agent_effects.contract_helpers import (
    at_most_one_effect,
    events_must_precede,
    exactly_one_effect,
    forbid_field_reads,
    no_effects_after_cancellation,
    records_must_link,
    requires_authorization_for_writes,
    unique_business_key,
)
from agent_effects.contracts import evaluate_contracts
from agent_effects.models import (
    AgentRun,
    EvaluationContext,
    EventKind,
    JsonObject,
    TestCase,
    TraceEvent,
)
from agent_effects.protocols import Contract


def _context(
    final_state: JsonObject,
    events: tuple[TraceEvent, ...] = (),
) -> EvaluationContext:
    return EvaluationContext(
        case=TestCase(id="helpers"),
        agent_name="helper-test",
        agent_run=AgentRun(status="completed"),
        initial_state={},
        final_state=final_state,
        events=events,
    )


def _codes(contract: Contract, context: EvaluationContext) -> tuple[str, ...]:
    return evaluate_contracts((contract,), context).codes


def test_cardinality_helpers_pass_and_fail_with_stable_codes() -> None:
    one = exactly_one_effect("effects")
    maximum = at_most_one_effect("effects")

    assert _codes(one, _context({"effects": [{"id": "one"}]})) == ()
    assert _codes(maximum, _context({"effects": []})) == ()
    duplicate = _context({"effects": [{"id": "one"}, {"id": "two"}]})
    assert _codes(one, duplicate) == ("effect_cardinality_exactly_one",)
    assert _codes(maximum, duplicate) == ("effect_cardinality_at_most_one",)
    assert one.name == "exactly_one:effects"


def test_unique_business_key_and_record_link_helpers() -> None:
    unique = unique_business_key("refunds", ("payment_id", "amount"))
    links = records_must_link("refunds", "payment_id", "payments")
    valid = _context(
        {
            "payments": [{"id": "p1"}, {"id": "p2"}],
            "refunds": [
                {"payment_id": "p1", "amount": 10},
                {"payment_id": "p2", "amount": 10},
            ],
        }
    )
    invalid = _context(
        {
            "payments": [{"id": "p1"}],
            "refunds": [
                {"payment_id": "missing", "amount": 10},
                {"payment_id": "missing", "amount": 10},
            ],
        }
    )
    assert _codes(unique, valid) == ()
    assert _codes(links, valid) == ()
    assert _codes(unique, invalid) == ("duplicate_business_key",)
    assert _codes(links, invalid) == ("missing_record_link",)


def test_authorization_and_forbidden_read_helpers() -> None:
    authorization = requires_authorization_for_writes(("issue_refund",))
    privacy = forbid_field_reads(("ssn",), operations=("read_customer",))
    allowed_events = (
        TraceEvent(
            sequence=0,
            kind=EventKind.POLICY,
            operation="issue_refund",
            data={"allowed": True},
        ),
        TraceEvent(sequence=1, kind=EventKind.COMMIT, operation="issue_refund"),
        TraceEvent(
            sequence=2,
            kind=EventKind.READ,
            operation="read_customer",
            data={"fields": ["name"]},
        ),
    )
    denied_events = (
        TraceEvent(sequence=0, kind=EventKind.COMMIT, operation="issue_refund"),
        TraceEvent(
            sequence=1,
            kind=EventKind.READ,
            operation="read_customer",
            data={"fields": ["name", "ssn"]},
        ),
    )
    assert _codes(authorization, _context({}, allowed_events)) == ()
    assert _codes(privacy, _context({}, allowed_events)) == ()
    assert _codes(authorization, _context({}, denied_events)) == ("write_without_authorization",)
    assert _codes(privacy, _context({}, denied_events)) == ("forbidden_field_read",)


def test_cancellation_and_event_order_helpers() -> None:
    cancellation = no_effects_after_cancellation(
        "cancel",
        effect_operations=("send",),
    )
    ordering = events_must_precede("authorize", "send")
    valid = (
        TraceEvent(sequence=0, kind=EventKind.POLICY, operation="authorize"),
        TraceEvent(sequence=1, kind=EventKind.COMMIT, operation="send"),
        TraceEvent(sequence=2, kind=EventKind.AGENT, operation="cancel"),
    )
    invalid = (
        TraceEvent(sequence=0, kind=EventKind.AGENT, operation="cancel"),
        TraceEvent(sequence=1, kind=EventKind.COMMIT, operation="send"),
    )
    assert _codes(cancellation, _context({}, valid)) == ()
    assert _codes(ordering, _context({}, valid)) == ()
    assert _codes(cancellation, _context({}, invalid)) == ("effect_after_cancellation",)
    assert _codes(ordering, _context({}, invalid)) == ("event_order_violation",)
