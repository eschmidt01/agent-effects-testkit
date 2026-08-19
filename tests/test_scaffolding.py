from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import pytest
from typer.testing import CliRunner

from agent_effects.cli import app
from agent_effects.scaffolding import ScaffoldError, _target_path, generate_project

runner = CliRunner()


def _pytest(project: Path) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, "-m", "pytest", "-q"],
        cwd=project,
        check=False,
        capture_output=True,
        text=True,
    )


def test_normal_template_is_guarded_and_passes(tmp_path: Path) -> None:
    project = tmp_path / "starter"
    written = generate_project(project)
    assert {item.relative_to(project).as_posix() for item in written} == {
        "README.md",
        "agent.py",
        "pyproject.toml",
        "tests/test_agent_effects.py",
        "world.py",
    }
    result = _pytest(project)
    assert result.returncode == 0, result.stdout + result.stderr
    assert "1 passed" in result.stdout

    with pytest.raises(ScaffoldError, match="refusing to overwrite"):
        generate_project(project)
    generate_project(project, force=True)


def test_template_path_traversal_is_rejected(tmp_path: Path) -> None:
    for unsafe in ("../escape.py", "/absolute.py", "nested/../../escape.py"):
        with pytest.raises(ScaffoldError, match=r"safe relative|escapes"):
            _target_path(tmp_path, unsafe)
    assert not (tmp_path.parent / "escape.py").exists()


def test_init_cli_reports_conflicts_and_unknown_templates(tmp_path: Path) -> None:
    # Exercise the narrow non-interactive terminal behavior used by GitHub Actions.
    project = tmp_path / ("long-project-path-" + ("x" * 80)) / "cli"
    created = runner.invoke(app, ["init", str(project)])
    conflict = runner.invoke(app, ["init", str(project)])
    unknown = runner.invoke(app, ["init", str(tmp_path / "unknown"), "--template", "x"])

    assert created.exit_code == 0, created.stdout
    assert "next:" in created.stdout
    assert conflict.exit_code != 0
    assert "--force" in conflict.output
    assert unknown.exit_code != 0
    assert "unknown template" in unknown.output


def test_lost_ack_template_fails_then_passes_with_stable_idempotency(
    tmp_path: Path,
) -> None:
    project = tmp_path / "lost-ack"
    generate_project(project, template="lost-ack")

    failing = _pytest(project)
    assert failing.returncode == 1
    assert "duplicate effect detected after timeout_after_commit" in failing.stdout
    assert "integrity-checked failure bundle" in failing.stdout
    bundles = tuple((project / ".agent-effects" / "failures").iterdir())
    assert len(bundles) == 1

    dry_run = runner.invoke(app, ["reproduce", "--dry-run", str(bundles[0])])
    assert dry_run.exit_code == 0, dry_run.stdout
    assert "no code" in dry_run.stdout
    assert "was executed" in dry_run.stdout

    reproduced = subprocess.run(
        [sys.executable, "-m", "agent_effects.cli", "reproduce", str(bundles[0])],
        cwd=project,
        check=False,
        capture_output=True,
        text=True,
    )
    assert reproduced.returncode == 0, reproduced.stdout + reproduced.stderr
    assert "reproduced" in reproduced.stdout

    policy = project / "policy.py"
    policy.write_text("STABLE_IDEMPOTENCY = True\n", encoding="utf-8")
    passing = _pytest(project)
    assert passing.returncode == 0, passing.stdout + passing.stderr
    assert "1 passed" in passing.stdout
