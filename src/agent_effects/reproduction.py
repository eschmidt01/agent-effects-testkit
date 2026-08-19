"""Safe resolution of installed bundle reproducers by registered identifier."""

from __future__ import annotations

import inspect
from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from importlib.metadata import entry_points
from typing import cast

from .artifacts import FailureBundle
from .models import FailureSignature, TestCase, TrialResult
from .signatures import extract_failure_signature

Reproducer = Callable[[TestCase], TrialResult | Awaitable[TrialResult]]
REFUND_REPRODUCER_PREFIX = "agent-effects.examples.refund/"
BUILTIN_REFUND_REPRODUCERS = frozenset(
    f"{REFUND_REPRODUCER_PREFIX}{name}/v1"
    for name in ("naive", "idempotent", "reconcile", "overreading")
)


class ReproductionError(RuntimeError):
    """Raised when an integrity-checked bundle has no usable installed reproducer."""


@dataclass(frozen=True, slots=True)
class ReproductionOutcome:
    """Comparison between the bundled failure and a fresh minimized-case run."""

    expected_signature: tuple[str, ...]
    actual_signature: tuple[str, ...]
    expected_primary_category: str
    actual_primary_category: str
    expected_failure_signature: FailureSignature
    actual_failure_signature: FailureSignature
    matched: bool
    result: TrialResult


async def _run_callable(reproducer: Reproducer, case: TestCase) -> TrialResult:
    value = reproducer(case)
    if inspect.isawaitable(value):
        value = await value
    if not isinstance(value, TrialResult):
        raise ReproductionError(
            f"registered reproducer returned {type(value).__name__}, not TrialResult"
        )
    return value


async def _run_refund_reproducer(identifier: str, case: TestCase) -> TrialResult:
    from .examples.refund import AGENTS, REFUND_CONTRACTS, RefundWorld
    from .runner import TrialRunner

    agent_name = identifier.removeprefix(REFUND_REPRODUCER_PREFIX).removesuffix("/v1")
    try:
        agent = AGENTS[agent_name]
    except KeyError as exc:
        raise ReproductionError(f"unknown built-in refund reproducer: {identifier}") from exc
    return await TrialRunner().run(
        case=case,
        world_factory=RefundWorld,
        agent=agent,
        contracts=REFUND_CONTRACTS,
        write_failure=False,
        reproducer_id=identifier,
    )


async def run_registered_reproducer(identifier: str, case: TestCase) -> TrialResult:
    """Run a built-in or installed entry-point reproducer without importing a path from data."""

    if identifier.startswith(REFUND_REPRODUCER_PREFIX):
        return await _run_refund_reproducer(identifier, case)

    matches = [
        entry
        for entry in entry_points(group="agent_effects.reproducers")
        if entry.name == identifier
    ]
    if len(matches) != 1:
        raise ReproductionError(
            f"no unique installed reproducer is registered as {identifier!r}; "
            "install the adapter package that created this bundle"
        )
    loaded = matches[0].load()
    if not callable(loaded):
        raise ReproductionError(f"registered reproducer {identifier!r} is not callable")
    return await _run_callable(cast(Reproducer, loaded), case)


def inspect_registered_reproducer(identifier: str) -> str:
    """Identify registered code without importing or executing the entry point."""

    if identifier in BUILTIN_REFUND_REPRODUCERS:
        return f"built-in reproducer {identifier!r}"
    matches = [
        entry
        for entry in entry_points(group="agent_effects.reproducers")
        if entry.name == identifier
    ]
    if len(matches) != 1:
        raise ReproductionError(
            f"no unique installed reproducer is registered as {identifier!r}; "
            "install the adapter package that created this bundle"
        )
    entry = matches[0]
    return f"installed entry point {entry.name!r} from group 'agent_effects.reproducers'"


async def reproduce_bundle(bundle: FailureBundle) -> ReproductionOutcome:
    """Rerun an integrity-checked bundle and compare the exact failure identity."""

    identifier = bundle.manifest.reproducer_id
    if identifier is None:
        raise ReproductionError(
            "bundle does not declare a reproducer; rerun the originating test with "
            "a registered reproducer_id"
        )
    result = await run_registered_reproducer(identifier, bundle.minimized_case)
    expected_category = bundle.manifest.primary_failure_category
    actual_category = result.primary_failure_category or "unknown"
    expected_failure_signature = (
        bundle.manifest.failure_signature
        if bundle.manifest.failure_signature is not None
        else extract_failure_signature(bundle.result)
    )
    actual_failure_signature = extract_failure_signature(result)
    if bundle.manifest.failure_signature is None:
        matched = (
            result.signature == bundle.manifest.signature and actual_category == expected_category
        )
    else:
        matched = actual_failure_signature == expected_failure_signature
    return ReproductionOutcome(
        expected_signature=bundle.manifest.signature,
        actual_signature=result.signature,
        expected_primary_category=expected_category,
        actual_primary_category=actual_category,
        expected_failure_signature=expected_failure_signature,
        actual_failure_signature=actual_failure_signature,
        matched=matched,
        result=result,
    )
