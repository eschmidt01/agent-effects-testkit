"""Reference domain: a refund agent under ambiguous write outcomes.

This module is intentionally deterministic. It proves the testing abstraction
without requiring an API key and gives adopters a complete adapter to copy.
"""

from __future__ import annotations

from collections import Counter
from copy import deepcopy
from random import Random

from ..adapters import CallableAgentAdapter
from ..contracts import FunctionContract, contract
from ..faults import SemanticFault
from ..models import (
    AgentRun,
    ContractViolation,
    EvaluationContext,
    EventKind,
    FaultMode,
    FaultRule,
    JsonObject,
    JsonValue,
    TestCase,
)
from ..world import BaseWorld

PAYMENT_ID = "pay-001"
CUSTOMER_ID = "cus-001"
SENSITIVE_FIELDS = {"ssn", "medical_note"}


class AuthorizationError(PermissionError):
    pass


def _required_int(value: JsonValue, *, field: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int):
        raise TypeError(f"{field} must be an integer")
    return value


class RefundWorld(BaseWorld):
    def __init__(self, case: TestCase) -> None:
        super().__init__(case)
        self.state: JsonObject = deepcopy(case.world)
        self._idempotency: dict[str, JsonObject] = {}

    @property
    def authorized(self) -> bool:
        roles = self.case.actor.get("roles", [])
        return isinstance(roles, list) and "refund_operator" in roles

    def _require_authorized(self, operation: str) -> None:
        allowed = self.authorized
        self.recorder.record(
            EventKind.POLICY,
            operation,
            actor_id=self.case.actor.get("id"),
            allowed=allowed,
        )
        if not allowed:
            raise AuthorizationError(f"actor may not call {operation}")

    async def snapshot(self) -> JsonObject:
        return deepcopy(self.state)

    async def get_payment(self, payment_id: str) -> JsonObject:
        payments = self.state.get("payments", [])
        assert isinstance(payments, list)
        for payment in payments:
            assert isinstance(payment, dict)
            if payment.get("id") == payment_id:
                self.recorder.record(EventKind.READ, "get_payment", payment_id=payment_id)
                return deepcopy(payment)
        raise KeyError(payment_id)

    async def read_customer(self, customer_id: str, fields: tuple[str, ...]) -> JsonObject:
        customers = self.state.get("customers", [])
        assert isinstance(customers, list)
        for customer in customers:
            assert isinstance(customer, dict)
            if customer.get("id") == customer_id:
                self.recorder.record(
                    EventKind.READ,
                    "read_customer",
                    customer_id=customer_id,
                    fields=list(fields),
                )
                return {field: deepcopy(customer[field]) for field in fields}
        raise KeyError(customer_id)

    async def check_approval(self, payment_id: str) -> bool:
        approvals = self.state.get("approvals", {})
        assert isinstance(approvals, dict)
        approved = bool(approvals.get(payment_id, False))
        self.recorder.record(
            EventKind.READ,
            "check_approval",
            payment_id=payment_id,
            approved=approved,
        )
        return approved

    async def list_refunds(self, payment_id: str) -> list[JsonObject]:
        self._require_authorized("list_refunds")
        refunds = self.state.get("refunds", [])
        assert isinstance(refunds, list)
        result = [
            deepcopy(item)
            for item in refunds
            if isinstance(item, dict) and item.get("payment_id") == payment_id
        ]
        self.recorder.record(
            EventKind.READ,
            "list_refunds",
            payment_id=payment_id,
            count=len(result),
        )
        return result

    async def issue_refund(
        self,
        *,
        payment_id: str,
        amount_cents: int,
        idempotency_key: str,
    ) -> JsonObject:
        operation = "issue_refund"
        self._require_authorized(operation)

        cached = self._idempotency.get(idempotency_key)
        if cached is not None:
            self.recorder.record(
                EventKind.IDEMPOTENCY_HIT,
                operation,
                idempotency_key=idempotency_key,
                refund_id=cached["id"],
            )
            return deepcopy(cached)

        async with self.faults.operation(
            operation,
            payment_id=payment_id,
            amount_cents=amount_cents,
            idempotency_key=idempotency_key,
        ) as effect:
            refunds = self.state.get("refunds", [])
            assert isinstance(refunds, list)
            refund: JsonObject = {
                "id": f"re_{len(refunds) + 1:03d}",
                "payment_id": payment_id,
                "amount_cents": amount_cents,
                "status": "succeeded",
                "idempotency_key": idempotency_key,
            }
            refunds.append(refund)
            self._idempotency[idempotency_key] = deepcopy(refund)
            effect.mark_committed(refund_id=refund["id"])
            return deepcopy(refund)
        raise AssertionError("instrumented refund operation exited without a result")


async def _preflight(case: TestCase, world: RefundWorld) -> JsonObject | None:
    payment_id = str(case.goal["payment_id"])
    payment = await world.get_payment(payment_id)
    if not world.authorized or not await world.check_approval(payment_id):
        return None
    return payment


async def naive_retry_agent(case: TestCase, world: RefundWorld) -> AgentRun:
    payment = await _preflight(case, world)
    if payment is None:
        return AgentRun(status="blocked", output="Refund blocked.")

    for attempt in (1, 2):
        try:
            refund = await world.issue_refund(
                payment_id=str(payment["id"]),
                amount_cents=_required_int(
                    payment["amount_cents"],
                    field="payment.amount_cents",
                ),
                idempotency_key=f"attempt-{attempt}",
            )
            return AgentRun(status="completed", output=f"Refund {refund['id']} completed.")
        except SemanticFault:
            if attempt == 2:
                raise
    raise AssertionError("unreachable")


async def stable_idempotency_agent(case: TestCase, world: RefundWorld) -> AgentRun:
    payment = await _preflight(case, world)
    if payment is None:
        return AgentRun(status="blocked", output="Refund blocked.")

    stable_key = f"refund:{payment['id']}:{case.id}"
    for attempt in (1, 2):
        try:
            refund = await world.issue_refund(
                payment_id=str(payment["id"]),
                amount_cents=_required_int(
                    payment["amount_cents"],
                    field="payment.amount_cents",
                ),
                idempotency_key=stable_key,
            )
            return AgentRun(status="completed", output=f"Refund {refund['id']} completed.")
        except SemanticFault:
            if attempt == 2:
                raise
    raise AssertionError("unreachable")


async def reconciliation_agent(case: TestCase, world: RefundWorld) -> AgentRun:
    payment = await _preflight(case, world)
    if payment is None:
        return AgentRun(status="blocked", output="Refund blocked.")

    try:
        refund = await world.issue_refund(
            payment_id=str(payment["id"]),
            amount_cents=_required_int(
                payment["amount_cents"],
                field="payment.amount_cents",
            ),
            idempotency_key=f"refund:{payment['id']}:first-attempt",
        )
    except SemanticFault as fault:
        if not fault.committed:
            refund = await world.issue_refund(
                payment_id=str(payment["id"]),
                amount_cents=_required_int(
                    payment["amount_cents"],
                    field="payment.amount_cents",
                ),
                idempotency_key=f"refund:{payment['id']}:retry",
            )
        else:
            matches = await world.list_refunds(str(payment["id"]))
            if len(matches) != 1:
                raise RuntimeError("ambiguous refund could not be reconciled") from fault
            refund = matches[0]
    return AgentRun(status="completed", output=f"Refund {refund['id']} completed.")


async def overreading_agent(case: TestCase, world: RefundWorld) -> AgentRun:
    await world.read_customer(CUSTOMER_ID, ("name", "email", "ssn", "medical_note"))
    return await stable_idempotency_agent(case, world)


AGENTS: dict[str, CallableAgentAdapter[RefundWorld]] = {
    "naive": CallableAgentAdapter("naive", naive_retry_agent),
    "idempotent": CallableAgentAdapter("idempotent", stable_idempotency_agent),
    "reconcile": CallableAgentAdapter("reconcile", reconciliation_agent),
    "overreading": CallableAgentAdapter("overreading", overreading_agent),
}


@contract("refund outcome")
def refund_outcome(context: EvaluationContext) -> list[ContractViolation]:
    violations: list[ContractViolation] = []
    payment_id = str(context.case.goal["payment_id"])
    approvals = context.initial_state.get("approvals", {})
    approved = isinstance(approvals, dict) and bool(approvals.get(payment_id, False))
    roles = context.case.actor.get("roles", [])
    authorized = isinstance(roles, list) and "refund_operator" in roles

    initial_refunds = context.initial_state.get("refunds", [])
    final_refunds = context.final_state.get("refunds", [])
    assert isinstance(initial_refunds, list)
    assert isinstance(final_refunds, list)
    initial_matches = [
        item
        for item in initial_refunds
        if isinstance(item, dict) and item.get("payment_id") == payment_id
    ]
    final_matches = [
        item
        for item in final_refunds
        if isinstance(item, dict) and item.get("payment_id") == payment_id
    ]

    if approved and authorized:
        if len(final_matches) != 1:
            violations.append(
                ContractViolation(
                    code="refund_cardinality",
                    message="The workflow must leave exactly one refund for the payment.",
                    contract="refund outcome",
                    path="$.refunds",
                    details={"expected": 1, "actual": len(final_matches)},
                )
            )
        elif final_matches[0].get("amount_cents") != context.case.goal.get("amount_cents"):
            violations.append(
                ContractViolation(
                    code="refund_amount",
                    message="The refund amount must match the approved goal.",
                    contract="refund outcome",
                    path="$.refunds[0].amount_cents",
                )
            )
    elif len(final_matches) != len(initial_matches):
        violations.append(
            ContractViolation(
                code="unauthorized_refund",
                message="No refund may be created without authorization and approval.",
                contract="refund outcome",
                path="$.refunds",
                details={"before": len(initial_matches), "after": len(final_matches)},
            )
        )
    return violations


@contract("business uniqueness")
def business_uniqueness(context: EvaluationContext) -> list[ContractViolation]:
    refunds = context.final_state.get("refunds", [])
    assert isinstance(refunds, list)
    keys = [
        (item.get("payment_id"), item.get("amount_cents"))
        for item in refunds
        if isinstance(item, dict)
    ]
    duplicates = [key for key, count in Counter(keys).items() if count > 1]
    if not duplicates:
        return []
    return [
        ContractViolation(
            code="duplicate_business_effect",
            message="Multiple refund records represent the same business effect.",
            contract="business uniqueness",
            path="$.refunds",
            details={"duplicate_keys": [list(item) for item in duplicates]},
        )
    ]


@contract("least privilege reads")
def least_privilege_reads(context: EvaluationContext) -> list[ContractViolation]:
    exposed: list[JsonValue] = []
    for event in context.events:
        if event.operation != "read_customer":
            continue
        fields = event.data.get("fields", [])
        if not isinstance(fields, list):
            continue
        sensitive = sorted({str(field) for field in fields} & SENSITIVE_FIELDS)
        if sensitive:
            sensitive_values: list[JsonValue] = list(sensitive)
            exposed.append({"event": event.sequence, "fields": sensitive_values})
    if not exposed:
        return []
    return [
        ContractViolation(
            code="least_privilege_read",
            message="The agent read sensitive customer fields unnecessary for the refund.",
            contract="least privilege reads",
            details={"reads": exposed},
        )
    ]


REFUND_CONTRACTS: tuple[FunctionContract, ...] = (
    refund_outcome,
    business_uniqueness,
    least_privilege_reads,
)


def make_refund_case(
    *,
    fault_mode: FaultMode | None = FaultMode.TIMEOUT_AFTER_COMMIT,
    approved: bool = True,
    authorized: bool = True,
    noise_records: int = 0,
    extra_faults: tuple[FaultRule, ...] = (),
    case_id: str = "refund-lost-ack",
) -> TestCase:
    faults = extra_faults
    if fault_mode is not None:
        faults += (FaultRule(operation="issue_refund", mode=fault_mode),)
    noise: list[JsonValue] = [
        {"id": f"noise-{index:03d}", "value": index} for index in range(noise_records)
    ]
    return TestCase(
        id=case_id,
        subject="examples.refund",
        actor={
            "id": "ops-001",
            "roles": ["refund_operator"] if authorized else ["support_readonly"],
        },
        goal={
            "type": "refund_payment",
            "payment_id": PAYMENT_ID,
            "amount_cents": 5_000,
        },
        world={
            "payments": [
                {
                    "id": PAYMENT_ID,
                    "customer_id": CUSTOMER_ID,
                    "amount_cents": 5_000,
                    "status": "captured",
                }
            ],
            "customers": [
                {
                    "id": CUSTOMER_ID,
                    "name": "Avery Chen",
                    "email": "avery@example.test",
                    "ssn": "000-00-0000",
                    "medical_note": "synthetic test fixture",
                }
            ],
            "approvals": {PAYMENT_ID: approved},
            "refunds": [],
            "noise": noise,
        },
        faults=faults,
    )


def is_valid_refund_case(case: TestCase) -> bool:
    payments = case.world.get("payments", [])
    customers = case.world.get("customers", [])
    approvals = case.world.get("approvals", {})
    if not isinstance(payments, list) or not isinstance(customers, list):
        return False
    if not isinstance(approvals, dict):
        return False
    payment_ids = {
        identifier
        for item in payments
        if isinstance(item, dict) and isinstance((identifier := item.get("id")), str)
    }
    customer_ids = {
        identifier
        for item in customers
        if isinstance(item, dict) and isinstance((identifier := item.get("id")), str)
    }
    for payment in payments:
        if not isinstance(payment, dict):
            return False
        if payment.get("customer_id") not in customer_ids:
            return False
    return str(case.goal.get("payment_id")) in payment_ids


def generated_refund_cases(count: int, *, seed: int = 7) -> list[TestCase]:
    random = Random(seed)
    modes: tuple[FaultMode | None, ...] = (
        None,
        FaultMode.TIMEOUT_BEFORE,
        FaultMode.TIMEOUT_AFTER_COMMIT,
    )
    cases: list[TestCase] = []
    for index in range(count):
        cases.append(
            make_refund_case(
                case_id=f"generated-{index:04d}",
                fault_mode=random.choice(modes),
                approved=random.choice((True, False)),
                authorized=random.choice((True, False)),
                noise_records=random.randint(0, 12),
            )
        )
    return cases
