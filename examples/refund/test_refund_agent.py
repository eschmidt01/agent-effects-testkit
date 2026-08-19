"""Copyable pytest example using the public API."""

from agent_effects.examples.refund import (
    AGENTS,
    REFUND_CONTRACTS,
    RefundWorld,
    make_refund_case,
)
from agent_effects.models import FaultMode
from agent_effects.pytest_plugin import assert_contracts


def test_refund_agent_survives_lost_ack(agent_effects_runner) -> None:
    result = agent_effects_runner.run_sync(
        case=make_refund_case(fault_mode=FaultMode.TIMEOUT_AFTER_COMMIT),
        world_factory=RefundWorld,
        agent=AGENTS["idempotent"],
        contracts=REFUND_CONTRACTS,
    )
    assert_contracts(result)
