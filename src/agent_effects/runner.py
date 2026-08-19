"""Trial orchestration from isolated world to deterministic outcome contracts."""

from __future__ import annotations

import asyncio
import inspect
import time
from collections.abc import Awaitable, Callable, Sequence
from pathlib import Path
from typing import TypeVar, cast

from .contracts import evaluate_contracts
from .models import (
    AdapterInfo,
    AgentRun,
    ContractReport,
    ContractViolation,
    EvaluationContext,
    EventKind,
    FailureCategory,
    FailureStage,
    JsonValue,
    LifecycleFailure,
    TestCase,
    TraceEvent,
    TrialResult,
)
from .protocols import AgentAdapter, Contract, World, WorldFactory

T = TypeVar("T")
Clock = Callable[[], float]


async def _resolve(value: T | Awaitable[T]) -> T:
    """Resolve a value that may come from a synchronous or asynchronous adapter."""

    if inspect.isawaitable(value):
        return await cast(Awaitable[T], value)
    return value


def _adapter_info(agent: AgentAdapter) -> AdapterInfo:
    adapter_type = type(agent)
    return AdapterInfo(
        name=agent.name,
        module=adapter_type.__module__,
        qualname=adapter_type.__qualname__,
    )


def _failure_violation(failure: LifecycleFailure) -> ContractViolation:
    if failure.stage is FailureStage.FINAL_SNAPSHOT:
        message = (
            f"Final snapshot was unavailable ({failure.exception_type}: {failure.message}); "
            "contracts requiring final state were skipped. Fix world.snapshot() and rerun."
        )
    elif failure.stage is FailureStage.CLEANUP and not failure.primary:
        message = (
            f"Cleanup also failed after the primary agent or contract failure "
            f"({failure.exception_type}: {failure.message}); the earlier failure remains primary. "
            "Fix world.close() so test resources are reliably released."
        )
    else:
        message = f"{failure.stage.value} failed with {failure.exception_type}: {failure.message}"
    return ContractViolation(
        code=f"runner_{failure.stage.value}",
        message=message,
        contract="runner",
        details={
            "stage": failure.stage.value,
            "category": failure.category.value,
            "primary": failure.primary,
        },
    )


def _missing_fault_diagnostic(
    case: TestCase, events: tuple[TraceEvent, ...]
) -> ContractViolation | None:
    if not case.faults or any(event.kind is EventKind.FAULT for event in events):
        return None
    observed_operations = sorted(
        {event.operation for event in events if event.kind is EventKind.TOOL_CALL}
    )
    configured_operations = sorted({rule.operation for rule in case.faults})
    matching_calls = [
        event
        for event in events
        if event.kind is EventKind.TOOL_CALL and event.operation in configured_operations
    ]
    missing_commits = [
        rule.operation
        for rule in case.faults
        if rule.mode.value == "timeout_after_commit"
        and any(
            event.operation == rule.operation and event.data.get("occurrence") == rule.occurrence
            for event in matching_calls
        )
        and not any(
            event.kind is EventKind.COMMIT
            and event.operation == rule.operation
            and event.data.get("occurrence") == rule.occurrence
            for event in events
        )
    ]
    if missing_commits:
        message = (
            f"Targeted operation(s) {sorted(set(missing_commits))!r} executed but never "
            "called mark_committed() at the targeted occurrence. Place the marker "
            "immediately after the durable business write."
        )
    elif observed_operations:
        message = (
            f"No configured fault target was observed. Configured operations: "
            f"{configured_operations!r}; observed instrumented operations: "
            f"{observed_operations!r}. Check the operation name and occurrence."
        )
    else:
        message = (
            f"Targeted operation(s) {configured_operations!r} never executed, or the "
            "world operation is not instrumented with faults.operation(). Confirm the "
            "agent reached the operation and that instrumentation is installed."
        )
    configured_values: list[JsonValue] = list(configured_operations)
    observed_values: list[JsonValue] = list(observed_operations)
    return ContractViolation(
        code="fault_target_not_observed",
        message=message,
        contract="fault schedule",
        details={
            "configured_operations": configured_values,
            "observed_operations": observed_values,
        },
    )


class TrialRunner:
    """Execute one isolated trial while preserving structured lifecycle failures."""

    def __init__(
        self,
        *,
        artifact_dir: Path | None = None,
        clock: Clock = time.perf_counter,
    ) -> None:
        self.artifact_dir = artifact_dir
        self._clock = clock

    async def run(
        self,
        *,
        case: TestCase,
        world_factory: WorldFactory,
        agent: AgentAdapter,
        contracts: Sequence[Contract],
        write_failure: bool = True,
        reproducer_id: str | None = None,
    ) -> TrialResult:
        """Run a case and return a result even when an ordinary lifecycle stage fails."""

        started = self._clock()
        failures: list[LifecycleFailure] = []
        violations: list[ContractViolation] = []
        root_claimed = False
        world: World | None = None
        initial_state = None
        final_state = None
        agent_run: AgentRun | None = None
        events: tuple[TraceEvent, ...] = ()
        contract_ids: tuple[str, ...] = ()

        def capture(
            stage: FailureStage,
            category: FailureCategory,
            exception: Exception | asyncio.CancelledError,
            *,
            include_violation: bool = True,
        ) -> LifecycleFailure:
            nonlocal root_claimed
            failure = LifecycleFailure(
                stage=stage,
                category=category,
                exception_type=type(exception).__name__,
                message=str(exception),
                primary=not root_claimed,
            )
            failures.append(failure)
            if include_violation:
                violations.append(_failure_violation(failure))
            root_claimed = True
            return failure

        try:
            world = await _resolve(world_factory(case))
            if world is None:
                raise TypeError("world factory returned None")
        except (Exception, asyncio.CancelledError) as exc:
            capture(FailureStage.WORLD_CREATION, FailureCategory.INFRASTRUCTURE, exc)

        if world is not None:
            try:
                initial_state = await _resolve(world.snapshot())
            except (Exception, asyncio.CancelledError) as exc:
                capture(FailureStage.INITIAL_SNAPSHOT, FailureCategory.INFRASTRUCTURE, exc)

            if initial_state is not None:
                try:
                    resolved_run = await _resolve(agent.run(case, world))
                    if not isinstance(resolved_run, AgentRun):
                        raise TypeError(
                            "agent adapter must return AgentRun; "
                            f"received {type(resolved_run).__name__}"
                        )
                    agent_run = resolved_run
                except (Exception, asyncio.CancelledError) as exc:
                    capture(
                        FailureStage.AGENT_EXECUTION,
                        FailureCategory.AGENT,
                        exc,
                        include_violation=False,
                    )
                    agent_run = AgentRun(
                        status="error",
                        error_type=type(exc).__name__,
                        error_message=str(exc),
                    )

            try:
                final_state = await _resolve(world.snapshot())
            except (Exception, asyncio.CancelledError) as exc:
                capture(FailureStage.FINAL_SNAPSHOT, FailureCategory.INFRASTRUCTURE, exc)

            events = world.recorder.events

            fault_diagnostic = (
                _missing_fault_diagnostic(case, events)
                if agent_run is None or agent_run.status != "blocked"
                else None
            )
            if fault_diagnostic is not None:
                violations.append(fault_diagnostic)
                root_claimed = True

            if initial_state is not None and final_state is not None and agent_run is not None:
                try:
                    contract_ids = tuple(item.name for item in contracts)
                    context = EvaluationContext(
                        case=case,
                        agent_name=agent.name,
                        agent_run=agent_run,
                        initial_state=initial_state,
                        final_state=final_state,
                        events=events,
                    )
                    evaluated = evaluate_contracts(contracts, context)
                    violations.extend(evaluated.violations)
                    if evaluated.violations:
                        root_claimed = True
                except (Exception, asyncio.CancelledError) as exc:
                    capture(
                        FailureStage.CONTRACT_EVALUATION,
                        FailureCategory.CONTRACT,
                        exc,
                    )

            if agent_run is not None and agent_run.status == "error":
                violations.append(
                    ContractViolation(
                        code="agent_error",
                        message=(f"Agent raised {agent_run.error_type}: {agent_run.error_message}"),
                        contract="runner",
                    )
                )

            try:
                await _resolve(world.close())
            except (Exception, asyncio.CancelledError) as exc:
                capture(FailureStage.CLEANUP, FailureCategory.INFRASTRUCTURE, exc)

        report = ContractReport(passed=not violations, violations=tuple(violations))
        result = TrialResult(
            case=case,
            agent_name=agent.name,
            adapter=_adapter_info(agent),
            contract_ids=contract_ids,
            reproducer_id=reproducer_id,
            initial_state=initial_state,
            final_state=final_state,
            events=events,
            agent_run=agent_run,
            contracts=report,
            lifecycle_failures=tuple(failures),
            elapsed_ms=max(0.0, (self._clock() - started) * 1000),
        )

        if not result.passed and write_failure and self.artifact_dir is not None:
            try:
                from .artifacts import FailureStore

                path = FailureStore(self.artifact_dir).write(result)
                result = result.model_copy(update={"artifact_path": str(path)})
            except (Exception, asyncio.CancelledError) as exc:
                failure = capture(
                    FailureStage.ARTIFACT_GENERATION,
                    FailureCategory.ARTIFACT,
                    exc,
                    include_violation=False,
                )
                report = ContractReport(
                    passed=False,
                    violations=(*result.contracts.violations, _failure_violation(failure)),
                )
                result = result.model_copy(
                    update={
                        "contracts": report,
                        "lifecycle_failures": tuple(failures),
                    }
                )
        return result

    def run_sync(
        self,
        *,
        case: TestCase,
        world_factory: WorldFactory,
        agent: AgentAdapter,
        contracts: Sequence[Contract],
        write_failure: bool = True,
        reproducer_id: str | None = None,
    ) -> TrialResult:
        """Run a trial from synchronous code."""

        try:
            asyncio.get_running_loop()
        except RuntimeError:
            return asyncio.run(
                self.run(
                    case=case,
                    world_factory=world_factory,
                    agent=agent,
                    contracts=contracts,
                    write_failure=write_failure,
                    reproducer_id=reproducer_id,
                )
            )
        raise RuntimeError("run_sync() cannot be used inside an active event loop; await run()")
