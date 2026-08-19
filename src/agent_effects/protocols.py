"""Public extension protocols for worlds, agents, contracts, and reducers."""

from __future__ import annotations

from collections.abc import Awaitable, Callable, Iterable, Sequence
from dataclasses import dataclass
from typing import Protocol, TypeAlias, runtime_checkable

from .models import (
    AgentRun,
    ContractViolation,
    EvaluationContext,
    JsonObject,
    TestCase,
)
from .trace import EventRecorder


@runtime_checkable
class World(Protocol):
    recorder: EventRecorder

    def snapshot(self) -> JsonObject | Awaitable[JsonObject]: ...

    def close(self) -> Awaitable[None] | None: ...


@runtime_checkable
class AgentAdapter(Protocol):
    @property
    def name(self) -> str: ...

    def run(self, case: TestCase, world: World) -> AgentRun | Awaitable[AgentRun]: ...


@runtime_checkable
class Contract(Protocol):
    @property
    def name(self) -> str: ...

    def evaluate(self, context: EvaluationContext) -> Sequence[ContractViolation]: ...


@runtime_checkable
class CaseReducer(Protocol):
    @property
    def name(self) -> str: ...

    def candidates(self, case: TestCase) -> Iterable[TestCase]: ...


@dataclass(frozen=True, slots=True)
class ReductionCandidate:
    """An immutable candidate plus a human-readable reduction explanation."""

    case: TestCase
    explanation: str


@runtime_checkable
class Reducer(Protocol):
    """Framework-neutral source of deterministic reduction candidates."""

    @property
    def name(self) -> str: ...

    def candidates(self, case: TestCase) -> Iterable[ReductionCandidate]: ...


WorldFactory: TypeAlias = Callable[[TestCase], World | Awaitable[World]]
FailurePredicate: TypeAlias = Callable[[TestCase], Awaitable[bool]]
CaseValidator: TypeAlias = Callable[[TestCase], bool]
