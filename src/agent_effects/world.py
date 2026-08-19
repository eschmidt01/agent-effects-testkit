"""Convenience base class for world adapters."""

from __future__ import annotations

from abc import ABC, abstractmethod

from .faults import FaultInjector
from .models import JsonObject, TestCase
from .trace import EventRecorder


class BaseWorld(ABC):
    def __init__(self, case: TestCase) -> None:
        self.case = case
        self.recorder = EventRecorder()
        self.faults = FaultInjector(case.faults, self.recorder)

    @abstractmethod
    async def snapshot(self) -> JsonObject:
        raise NotImplementedError

    async def close(self) -> None:
        return None
