from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

import agent_effects


def test_public_api_exports_are_available() -> None:
    assert agent_effects.FaultMode.TIMEOUT_AFTER_COMMIT.value == "timeout_after_commit"
    assert agent_effects.TestCase(id="public-api").id == "public-api"
    assert agent_effects.FailureStage.CLEANUP.value == "cleanup"
    assert agent_effects.FailureBundle.__name__ == "FailureBundle"
    assert agent_effects.FailureSignature(primary_category="contract").primary_category == (
        "contract"
    )
    assert agent_effects.HierarchicalShrinker.__name__ == "HierarchicalShrinker"
    assert agent_effects.ReductionGuarantee.NO_MINIMALITY_CLAIM.value == ("no_minimality_claim")
    assert agent_effects.exactly_one_effect("effects").name == "exactly_one:effects"
    assert callable(agent_effects.export_schemas)
    assert callable(agent_effects.render_bundle_report)
    assert callable(agent_effects.write_bundle_report)
    assert "TrialRunner" in dir(agent_effects)


def test_package_includes_typing_marker() -> None:
    marker = Path(agent_effects.__file__).with_name("py.typed")
    assert marker.is_file()


def test_top_level_import_is_lazy() -> None:
    environment = os.environ.copy()
    environment["PYTHONPATH"] = str(Path(__file__).parents[1] / "src")
    code = """
import sys
import agent_effects
assert 'agent_effects.models' not in sys.modules
assert agent_effects.FaultMode.TIMEOUT_BEFORE.value == 'timeout_before'
assert 'agent_effects.models' in sys.modules
"""
    completed = subprocess.run(
        [sys.executable, "-c", code],
        check=False,
        capture_output=True,
        text=True,
        env=environment,
    )
    assert completed.returncode == 0, completed.stderr
