"""Auto-loaded pytest entry point for Agent Effects.

This shim intentionally avoids importing :mod:`agent_effects` during pytest
plugin discovery. Coverage, tracing, and application hooks can therefore start
before the testkit's runtime modules are imported.
"""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING

import pytest

if TYPE_CHECKING:
    from _pytest.config import Config

    from agent_effects.runner import TrialRunner


def pytest_configure(config: Config) -> None:
    config.addinivalue_line(
        "markers",
        "agent_effects: deterministic world-state contract test for an agent",
    )


@pytest.fixture
def agent_effects_runner(tmp_path: Path) -> TrialRunner:
    from agent_effects.runner import TrialRunner

    return TrialRunner(artifact_dir=tmp_path / "agent-effects-failures")
