"""Commit-aware semantic fault injection.

Transport chaos tools can make an HTTP request fail. This module captures the
business-semantic distinction that matters for retries: whether the effect was
known not to happen, or happened but its acknowledgement was lost.
"""

from __future__ import annotations

from collections import Counter
from types import TracebackType

from .models import EventKind, FaultMode, FaultRule, JsonValue
from .trace import EventRecorder


class SemanticFault(TimeoutError):
    def __init__(self, rule: FaultRule, *, committed: bool) -> None:
        self.rule = rule
        self.committed = committed
        position = "after commit" if committed else "before commit"
        super().__init__(
            f"{rule.operation} simulated {rule.mode.value} on occurrence "
            f"{rule.occurrence} ({position})"
        )


class EffectScope:
    """One instrumented operation attempt.

    Domain adapters call ``mark_committed`` immediately after the durable
    business state change. The context manager then injects a lost
    acknowledgement when the configured rule is ``timeout_after_commit``.
    """

    def __init__(
        self,
        *,
        operation: str,
        occurrence: int,
        rule: FaultRule | None,
        recorder: EventRecorder,
        call_data: dict[str, JsonValue],
    ) -> None:
        self.operation = operation
        self.occurrence = occurrence
        self.rule = rule
        self.recorder = recorder
        self.call_data = call_data
        self.committed = False

    async def __aenter__(self) -> EffectScope:
        self.recorder.record(
            EventKind.TOOL_CALL,
            self.operation,
            occurrence=self.occurrence,
            **self.call_data,
        )
        if self.rule and self.rule.mode is FaultMode.TIMEOUT_BEFORE:
            self.recorder.record(
                EventKind.FAULT,
                self.operation,
                mode=self.rule.mode.value,
                occurrence=self.occurrence,
                committed=False,
            )
            raise SemanticFault(self.rule, committed=False)
        return self

    def mark_committed(self, **data: JsonValue) -> None:
        if self.committed:
            raise RuntimeError(f"{self.operation} was marked committed more than once")
        self.committed = True
        self.recorder.record(
            EventKind.COMMIT,
            self.operation,
            occurrence=self.occurrence,
            **data,
        )

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        traceback: TracebackType | None,
    ) -> bool:
        del exc_type, traceback
        if exc is not None:
            if not isinstance(exc, SemanticFault):
                self.recorder.record(
                    EventKind.ERROR,
                    self.operation,
                    occurrence=self.occurrence,
                    error_type=type(exc).__name__,
                    message=str(exc),
                )
            return False

        if self.rule and self.rule.mode is FaultMode.TIMEOUT_AFTER_COMMIT:
            if not self.committed:
                raise RuntimeError(
                    f"timeout_after_commit targeted {self.operation!r} occurrence "
                    f"{self.occurrence} requires mark_committed(), but the operation "
                    "exited without it; "
                    "place mark_committed() immediately after the durable business write"
                )
            self.recorder.record(
                EventKind.FAULT,
                self.operation,
                mode=self.rule.mode.value,
                occurrence=self.occurrence,
                committed=True,
            )
            raise SemanticFault(self.rule, committed=True)
        return False


class FaultInjector:
    def __init__(
        self,
        rules: tuple[FaultRule, ...],
        recorder: EventRecorder,
    ) -> None:
        self._rules = {(rule.operation, rule.occurrence): rule for rule in rules}
        if len(self._rules) != len(rules):
            raise ValueError("only one fault may target an operation occurrence")
        self._attempts: Counter[str] = Counter()
        self._recorder = recorder

    def operation(self, operation: str, **call_data: JsonValue) -> EffectScope:
        self._attempts[operation] += 1
        occurrence = self._attempts[operation]
        return EffectScope(
            operation=operation,
            occurrence=occurrence,
            rule=self._rules.get((operation, occurrence)),
            recorder=self._recorder,
            call_data=dict(call_data),
        )

    def attempts(self, operation: str) -> int:
        return self._attempts[operation]
