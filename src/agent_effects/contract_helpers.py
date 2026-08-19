"""Small deterministic helpers for common state and trace invariants."""

from __future__ import annotations

import json
from collections import Counter
from collections.abc import Callable, Iterable
from typing import TypeAlias, cast

from .contracts import FunctionContract
from .models import ContractViolation, EvaluationContext, EventKind, JsonObject, JsonValue

RecordPredicate: TypeAlias = Callable[[JsonObject], bool]


def _records(context: EvaluationContext, collection: str) -> list[JsonObject] | None:
    value = context.final_state.get(collection)
    if not isinstance(value, list) or not all(isinstance(item, dict) for item in value):
        return None
    return cast(list[JsonObject], value)


def _violation(
    *,
    code: str,
    message: str,
    contract_id: str,
    path: str | None = None,
    details: JsonObject | None = None,
) -> ContractViolation:
    return ContractViolation(
        code=code,
        message=message,
        contract=contract_id,
        path=path,
        details=details or {},
    )


def _cardinality_contract(
    collection: str,
    *,
    maximum: int,
    exact: bool,
    predicate: RecordPredicate | None,
    contract_id: str | None,
) -> FunctionContract:
    mode = "exactly_one" if exact else "at_most_one"
    stable_id = contract_id or f"{mode}:{collection}"
    code = f"effect_cardinality_{mode}"

    def evaluate(context: EvaluationContext) -> Iterable[ContractViolation]:
        records = _records(context, collection)
        if records is None:
            yield _violation(
                code="effect_collection_invalid",
                message=f"Final state collection {collection!r} must be a list of objects.",
                contract_id=stable_id,
                path=f"$.{collection}",
            )
            return
        selected = records if predicate is None else [item for item in records if predicate(item)]
        valid = len(selected) == maximum if exact else len(selected) <= maximum
        if not valid:
            expectation = "exactly one" if exact else "at most one"
            yield _violation(
                code=code,
                message=(
                    f"Expected {expectation} matching effect in {collection!r}; "
                    f"observed {len(selected)}."
                ),
                contract_id=stable_id,
                path=f"$.{collection}",
                details={"actual": len(selected), "expected_maximum": maximum},
            )

    return FunctionContract(name=stable_id, function=evaluate)


def exactly_one_effect(
    collection: str,
    *,
    predicate: RecordPredicate | None = None,
    contract_id: str | None = None,
) -> FunctionContract:
    """Require exactly one matching record in a final-state collection."""

    return _cardinality_contract(
        collection,
        maximum=1,
        exact=True,
        predicate=predicate,
        contract_id=contract_id,
    )


def at_most_one_effect(
    collection: str,
    *,
    predicate: RecordPredicate | None = None,
    contract_id: str | None = None,
) -> FunctionContract:
    """Require no more than one matching record in a final-state collection."""

    return _cardinality_contract(
        collection,
        maximum=1,
        exact=False,
        predicate=predicate,
        contract_id=contract_id,
    )


def unique_business_key(
    collection: str,
    fields: tuple[str, ...],
    *,
    contract_id: str | None = None,
) -> FunctionContract:
    """Require a unique composite business key across final-state records."""

    normalized_fields = tuple(sorted(fields))
    if not normalized_fields:
        raise ValueError("fields must contain at least one business-key field")
    stable_id = contract_id or f"unique_business_key:{collection}:{','.join(normalized_fields)}"

    def evaluate(context: EvaluationContext) -> Iterable[ContractViolation]:
        records = _records(context, collection)
        if records is None:
            yield _violation(
                code="effect_collection_invalid",
                message=f"Final state collection {collection!r} must be a list of objects.",
                contract_id=stable_id,
                path=f"$.{collection}",
            )
            return
        keys = [
            json.dumps(
                [record.get(field) for field in normalized_fields],
                sort_keys=True,
                separators=(",", ":"),
            )
            for record in records
        ]
        duplicate_count = sum(count - 1 for count in Counter(keys).values() if count > 1)
        if duplicate_count:
            yield _violation(
                code="duplicate_business_key",
                message=(
                    f"Collection {collection!r} contains {duplicate_count} duplicate "
                    f"record(s) for business key {normalized_fields!r}."
                ),
                contract_id=stable_id,
                path=f"$.{collection}",
                details={"duplicate_count": duplicate_count, "fields": list(normalized_fields)},
            )

    return FunctionContract(name=stable_id, function=evaluate)


def requires_authorization_for_writes(
    write_operations: tuple[str, ...],
    *,
    contract_id: str = "authorization_required_before_write",
) -> FunctionContract:
    """Require an allowed policy event before every matching commit event."""

    selected = frozenset(write_operations)

    def evaluate(context: EvaluationContext) -> Iterable[ContractViolation]:
        allowed: set[str] = set()
        for event in context.events:
            if event.kind is EventKind.POLICY and event.data.get("allowed") is True:
                allowed.add(event.operation)
            if (
                event.kind is EventKind.COMMIT
                and event.operation in selected
                and event.operation not in allowed
            ):
                yield _violation(
                    code="write_without_authorization",
                    message=(
                        f"Operation {event.operation!r} committed without a preceding "
                        "allowed authorization event."
                    ),
                    contract_id=contract_id,
                    details={"operation": event.operation, "sequence": event.sequence},
                )

    return FunctionContract(name=contract_id, function=evaluate)


def forbid_field_reads(
    fields: tuple[str, ...],
    *,
    operations: tuple[str, ...] = (),
    contract_id: str = "forbidden_field_reads",
) -> FunctionContract:
    """Reject trace read events whose ``fields`` data includes forbidden names."""

    forbidden = frozenset(fields)
    selected_operations = frozenset(operations)

    def evaluate(context: EvaluationContext) -> Iterable[ContractViolation]:
        for event in context.events:
            if event.kind is not EventKind.READ:
                continue
            if selected_operations and event.operation not in selected_operations:
                continue
            read_fields = event.data.get("fields", [])
            if not isinstance(read_fields, list):
                continue
            exposed = sorted(forbidden & {str(field) for field in read_fields})
            if exposed:
                exposed_values: list[JsonValue] = list(exposed)
                yield _violation(
                    code="forbidden_field_read",
                    message=(
                        f"Read operation {event.operation!r} accessed forbidden fields {exposed!r}."
                    ),
                    contract_id=contract_id,
                    details={"fields": exposed_values, "sequence": event.sequence},
                )

    return FunctionContract(name=contract_id, function=evaluate)


def records_must_link(
    source_collection: str,
    source_field: str,
    target_collection: str,
    *,
    target_field: str = "id",
    contract_id: str | None = None,
) -> FunctionContract:
    """Require every source reference to resolve to a target record."""

    stable_id = contract_id or (
        f"records_link:{source_collection}.{source_field}:{target_collection}.{target_field}"
    )

    def evaluate(context: EvaluationContext) -> Iterable[ContractViolation]:
        sources = _records(context, source_collection)
        targets = _records(context, target_collection)
        if sources is None or targets is None:
            yield _violation(
                code="link_collection_invalid",
                message="Both linked collections must be lists of objects.",
                contract_id=stable_id,
            )
            return
        target_values = [item.get(target_field) for item in targets]
        missing = [
            item.get(source_field)
            for item in sources
            if item.get(source_field) not in target_values
        ]
        if missing:
            yield _violation(
                code="missing_record_link",
                message=(
                    f"{len(missing)} record(s) in {source_collection!r} do not link "
                    f"to {target_collection!r}."
                ),
                contract_id=stable_id,
                path=f"$.{source_collection}",
                details={"missing_count": len(missing)},
            )

    return FunctionContract(name=stable_id, function=evaluate)


def no_effects_after_cancellation(
    cancellation_operation: str,
    *,
    effect_operations: tuple[str, ...] = (),
    contract_id: str = "no_effects_after_cancellation",
) -> FunctionContract:
    """Reject commit events after the first matching cancellation event."""

    selected = frozenset(effect_operations)

    def evaluate(context: EvaluationContext) -> Iterable[ContractViolation]:
        cancellation = next(
            (
                event.sequence
                for event in context.events
                if event.operation == cancellation_operation
            ),
            None,
        )
        if cancellation is None:
            return
        for event in context.events:
            if event.sequence <= cancellation or event.kind is not EventKind.COMMIT:
                continue
            if selected and event.operation not in selected:
                continue
            yield _violation(
                code="effect_after_cancellation",
                message=(
                    f"Operation {event.operation!r} committed after cancellation "
                    f"at sequence {cancellation}."
                ),
                contract_id=contract_id,
                details={"operation": event.operation, "sequence": event.sequence},
            )

    return FunctionContract(name=contract_id, function=evaluate)


def events_must_precede(
    before_operation: str,
    after_operation: str,
    *,
    contract_id: str | None = None,
) -> FunctionContract:
    """Require at least one ``before`` event ahead of each ``after`` event."""

    stable_id = contract_id or f"event_order:{before_operation}:{after_operation}"

    def evaluate(context: EvaluationContext) -> Iterable[ContractViolation]:
        before_sequences = [
            event.sequence for event in context.events if event.operation == before_operation
        ]
        for event in context.events:
            if event.operation != after_operation:
                continue
            if not any(sequence < event.sequence for sequence in before_sequences):
                yield _violation(
                    code="event_order_violation",
                    message=(
                        f"Event {before_operation!r} must precede {after_operation!r} "
                        f"at sequence {event.sequence}."
                    ),
                    contract_id=stable_id,
                    details={"after_sequence": event.sequence},
                )

    return FunctionContract(name=stable_id, function=evaluate)
