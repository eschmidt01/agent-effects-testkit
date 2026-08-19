"""Small pytest surface; business-specific contracts remain normal Python."""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING

import pytest

if TYPE_CHECKING:
    from _pytest.config import Config

    from .models import TrialResult
    from .runner import TrialRunner


def pytest_configure(config: Config) -> None:
    config.addinivalue_line(
        "markers",
        "agent_effects: deterministic world-state contract test for an agent",
    )


@pytest.fixture
def agent_effects_runner(tmp_path: Path) -> TrialRunner:
    from .runner import TrialRunner

    return TrialRunner(artifact_dir=tmp_path / "agent-effects-failures")


def assert_contracts(result: TrialResult) -> None:
    if result.passed:
        return
    lines = ["Agent Effects contracts failed:"]
    for violation in result.contracts.violations:
        lines.append(f"- [{violation.code}] {violation.message}")
    if result.artifact_path:
        lines.append(f"Failure bundle: {result.artifact_path}")
    raise AssertionError("\n".join(lines))
