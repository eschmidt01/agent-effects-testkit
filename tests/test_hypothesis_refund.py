from __future__ import annotations

import asyncio

import pytest

from agent_effects.examples.refund import (
    AGENTS,
    REFUND_CONTRACTS,
    RefundWorld,
    make_refund_case,
)
from agent_effects.models import FaultMode
from agent_effects.runner import TrialRunner

hypothesis = pytest.importorskip("hypothesis")
given = hypothesis.given
settings = hypothesis.settings
st = hypothesis.strategies


# Hypothesis is imported dynamically so this optional test can skip cleanly.
@given(  # type: ignore[untyped-decorator]
    mode=st.sampled_from([None, FaultMode.TIMEOUT_BEFORE, FaultMode.TIMEOUT_AFTER_COMMIT]),
    approved=st.booleans(),
    authorized=st.booleans(),
    noise=st.integers(min_value=0, max_value=25),
)
@settings(max_examples=60, deadline=None)  # type: ignore[untyped-decorator]
def test_idempotent_agent_preserves_refund_contracts(
    mode: FaultMode | None,
    approved: bool,
    authorized: bool,
    noise: int,
) -> None:
    case = make_refund_case(
        fault_mode=mode,
        approved=approved,
        authorized=authorized,
        noise_records=noise,
    )
    result = asyncio.run(
        TrialRunner().run(
            case=case,
            world_factory=RefundWorld,
            agent=AGENTS["idempotent"],
            contracts=REFUND_CONTRACTS,
            write_failure=False,
        )
    )
    assert result.passed, result.contracts.violations
