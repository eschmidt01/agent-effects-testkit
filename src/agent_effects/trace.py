"""Trace recording primitives with no dependency on an observability vendor."""

from __future__ import annotations

from collections.abc import Iterable

from .models import EventKind, JsonValue, TraceEvent


class EventRecorder:
    def __init__(self) -> None:
        self._events: list[TraceEvent] = []

    def record(
        self,
        kind: EventKind,
        operation: str,
        **data: JsonValue,
    ) -> TraceEvent:
        event = TraceEvent(
            sequence=len(self._events),
            kind=kind,
            operation=operation,
            data=dict(data),
        )
        self._events.append(event)
        return event

    @property
    def events(self) -> tuple[TraceEvent, ...]:
        return tuple(self._events)

    def extend(self, events: Iterable[TraceEvent]) -> None:
        for event in events:
            self.record(event.kind, event.operation, **event.data)
