# Model a commit boundary

The commit marker means “the durable business effect can no longer be assumed
absent.” It does not mean a request was sent or a tool started.

```python
async with self.faults.operation(
    "issue_refund",
    payment_id=payment_id,
    idempotency_key=idempotency_key,
) as effect:
    refund = await repository.insert_refund(...)
    effect.mark_committed(refund_id=refund.id)
    return refund
```

For a local transaction, mark after the transaction commits. For an external API,
mark only when the test double or sandbox has durably recorded the business
effect. A generic transport timeout cannot establish this distinction by itself.

`timeout_before` is raised before user operation code can reach the marker.
`timeout_after_commit` is raised only after exactly one marker. If a targeted
operation exits without the marker, the runner explains where to put it. If no
targeted operation appears, diagnostics show configured and observed operation
names and suggest checking instrumentation, the configured name, and control
flow.
