from __future__ import annotations

from agent_effects.models import EventKind
from agent_effects.trace import EventRecorder


def test_extend_resequences_imported_events() -> None:
    first = EventRecorder()
    first.record(EventKind.READ, "source", value=1)
    first.record(EventKind.COMMIT, "source", value=2)

    second = EventRecorder()
    second.record(EventKind.AGENT, "start")
    second.extend(first.events)

    assert [event.sequence for event in second.events] == [0, 1, 2]
    assert [event.operation for event in second.events] == ["start", "source", "source"]
