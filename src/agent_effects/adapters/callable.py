"""Adapter for ordinary sync or async Python callables."""

from __future__ import annotations

import inspect
from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from typing import Generic, TypeVar, cast

from ..models import AgentRun, TestCase
from ..protocols import World

WorldT = TypeVar("WorldT", bound=World)
CallableResult = AgentRun | str
AgentFunction = Callable[
    [TestCase, WorldT],
    CallableResult | Awaitable[CallableResult],
]


@dataclass(frozen=True, slots=True)
class CallableAgentAdapter(Generic[WorldT]):
    name: str
    function: AgentFunction[WorldT]

    async def run(self, case: TestCase, world: World) -> AgentRun:
        value = self.function(case, cast(WorldT, world))
        if inspect.isawaitable(value):
            value = await value
        if isinstance(value, AgentRun):
            return value
        return AgentRun(status="completed", output=value)
