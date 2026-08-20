from __future__ import annotations

import json
from pathlib import Path

import pytest
from typer.testing import CliRunner

import agent_effects.reproduction as reproduction
from agent_effects.artifacts import FailureStore
from agent_effects.cli import app
from agent_effects.examples.refund import (
    AGENTS,
    REFUND_CONTRACTS,
    RefundWorld,
    make_refund_case,
)
from agent_effects.models import FaultMode
from agent_effects.runner import TrialRunner

runner = CliRunner()


def _bundle(tmp_path: Path, *, reproducer: bool = True) -> Path:
    trial = TrialRunner().run_sync(
        case=make_refund_case(fault_mode=FaultMode.TIMEOUT_AFTER_COMMIT),
        world_factory=RefundWorld,
        agent=AGENTS["naive"],
        contracts=REFUND_CONTRACTS,
        write_failure=False,
        reproducer_id=("agent-effects.examples.refund/naive/v1" if reproducer else None),
    )
    return FailureStore(tmp_path).write(trial)


def test_doctor() -> None:
    result = runner.invoke(app, ["doctor"])
    assert result.exit_code == 0
    assert "Agent Effects environment" in result.stdout


def test_version() -> None:
    result = runner.invoke(app, ["version"])
    assert result.exit_code == 0
    assert "0.1.0a2" in result.stdout


def test_demo_naive_writes_bundle_and_fails(tmp_path: Path) -> None:
    output = tmp_path / "failures"
    result = runner.invoke(
        app,
        ["demo", "--agent", "naive", "--output", str(output)],
    )
    assert result.exit_code == 1
    assert "duplicate_business_effect" in result.stdout
    assert any(output.iterdir())


def test_demo_naive_report_explains_expected_and_observed_state(tmp_path: Path) -> None:
    output = tmp_path / "failures"
    result = runner.invoke(
        app,
        ["demo", "--agent", "naive", "--output", str(output), "--report"],
    )

    assert result.exit_code == 1
    assert "expected 1 refund" in result.stdout
    assert "observed 2 refunds" in result.stdout
    assert "report:" in result.stdout
    assert len(list(output.glob("*-report.html"))) == 1


def test_demo_robust_passes(tmp_path: Path) -> None:
    result = runner.invoke(
        app,
        ["demo", "--agent", "idempotent", "--output", str(tmp_path)],
    )
    assert result.exit_code == 0
    assert "PASS" in result.stdout


def test_bundle_verify_inspect_and_reproduce_commands(tmp_path: Path) -> None:
    bundle = _bundle(tmp_path)

    verified = runner.invoke(app, ["bundle", "verify", str(bundle)])
    inspected = runner.invoke(app, ["bundle", "inspect", str(bundle)])
    reproduced = runner.invoke(app, ["reproduce", str(bundle)])

    assert verified.exit_code == 0, verified.stdout
    assert "verified" in verified.stdout
    assert inspected.exit_code == 0, inspected.stdout
    assert "Primary category" in inspected.stdout
    assert reproduced.exit_code == 0, reproduced.stdout
    assert "reproduced" in reproduced.stdout


def test_bundle_verify_and_inspect_never_resolve_reproducer_code(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    bundle = _bundle(tmp_path)
    monkeypatch.setattr(
        reproduction,
        "entry_points",
        lambda **_kwargs: pytest.fail("verify or inspect resolved reproducer code"),
    )

    verified = runner.invoke(app, ["bundle", "verify", str(bundle)])
    inspected = runner.invoke(app, ["bundle", "inspect", str(bundle)])

    assert verified.exit_code == 0, verified.stdout
    assert inspected.exit_code == 0, inspected.stdout


def test_bundle_show_compatibility_and_json_inspection(tmp_path: Path) -> None:
    bundle = _bundle(tmp_path)

    shown = runner.invoke(app, ["bundle-show", str(bundle)])
    shown_json = runner.invoke(app, ["bundle-show", str(bundle), "--json"])
    inspected_json = runner.invoke(app, ["bundle", "inspect", str(bundle), "--json"])

    assert shown.exit_code == 0
    assert "refund_cardinality" in shown.stdout
    assert shown_json.exit_code == 0
    assert "agent-effects.result/v1alpha1" in shown_json.stdout
    assert inspected_json.exit_code == 0
    assert "agent-effects.failure/v1alpha1" in inspected_json.stdout


def test_bundle_commands_fail_closed_for_tampering(tmp_path: Path) -> None:
    bundle = _bundle(tmp_path)
    case_path = bundle / "case.json"
    case_path.write_bytes(case_path.read_bytes() + b"tampered")

    verified = runner.invoke(app, ["bundle", "verify", str(bundle)])
    inspected = runner.invoke(app, ["bundle", "inspect", str(bundle)])

    assert verified.exit_code == 2
    assert inspected.exit_code == 2
    assert "mismatch" in verified.stdout + verified.stderr


def test_reproduce_requires_declared_reproducer(tmp_path: Path) -> None:
    bundle = _bundle(tmp_path, reproducer=False)
    result = runner.invoke(app, ["reproduce", str(bundle)])

    assert result.exit_code == 2
    assert "does not declare" in result.stdout + result.stderr


def test_demo_rejects_unknown_agent_and_fault(tmp_path: Path) -> None:
    unknown_agent = runner.invoke(app, ["demo", "--agent", "missing"])
    unknown_fault = runner.invoke(
        app,
        ["demo", "--fault", "disconnect", "--output", str(tmp_path)],
    )

    assert unknown_agent.exit_code == 2
    assert unknown_fault.exit_code == 2


def test_case_validate_command(tmp_path: Path) -> None:
    case_path = tmp_path / "case.json"
    case_path.write_text(
        json.dumps(make_refund_case().model_dump(mode="json")),
        encoding="utf-8",
    )
    result = runner.invoke(app, ["case-validate", str(case_path)])

    assert result.exit_code == 0
    assert "valid" in result.stdout
