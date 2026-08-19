# Write state and trace contracts

Contracts are deterministic, fail-closed Python checks over the case, initial
state, final state, agent result, and trace. They describe acceptable outcomes;
they should not prescribe one exact safe trajectory.

For custom domain logic, use `@contract` and stable contract/violation IDs:

```python
from agent_effects import ContractViolation, contract


@contract("refund outcome")
def one_refund(context):
    matches = [
        row
        for row in context.final_state["refunds"]
        if row["payment_id"] == context.case.goal["payment_id"]
    ]
    if len(matches) == 1:
        return []
    return [
        ContractViolation(
            code="refund_cardinality",
            message="Expected exactly one refund for the approved payment.",
            contract="refund outcome",
            path="$.refunds",
        )
    ]
```

The small helper library covers recurring invariants without introducing a DSL:

```python
from agent_effects import (
    at_most_one_effect,
    events_must_precede,
    exactly_one_effect,
    forbid_field_reads,
    no_effects_after_cancellation,
    records_must_link,
    requires_authorization_for_writes,
    unique_business_key,
)

contracts = (
    exactly_one_effect("refunds"),
    unique_business_key("refunds", ("payment_id", "amount_cents")),
    requires_authorization_for_writes(("issue_refund",)),
    forbid_field_reads(("ssn", "medical_note")),
    records_must_link("refunds", "payment_id", "payments"),
    no_effects_after_cancellation("cancel", effect_operations=("issue_refund",)),
    events_must_precede("check_approval", "issue_refund"),
    at_most_one_effect("notifications"),
)
```

Every helper has a stable default contract ID and violation code. Supply an
explicit `contract_id` when multiple uses would otherwise share an identity.
