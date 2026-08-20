from __future__ import annotations

import re
import socket
from html.parser import HTMLParser
from pathlib import Path

import pytest
from typer.testing import CliRunner

import agent_effects.reproduction as reproduction
from agent_effects.artifacts import FailureBundle, FailureStore
from agent_effects.cli import app
from agent_effects.examples.refund import AGENTS, REFUND_CONTRACTS, RefundWorld, make_refund_case
from agent_effects.models import AdapterInfo, ContractReport, ContractViolation, EventKind
from agent_effects.report import render_bundle_report, write_bundle_report
from agent_effects.runner import TrialRunner

FIXTURE = Path(__file__).parent / "fixtures" / "failure_bundles" / "refund-lost-ack"


class _ReportStructure(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.ids: set[str] = set()
        self.tags: list[str] = []
        self.remote_references: list[str] = []
        self.csp = ""

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        self.tags.append(tag)
        values = dict(attrs)
        if values.get("id") is not None:
            self.ids.add(str(values["id"]))
        for name in ("src", "href"):
            value = values.get(name)
            if value is not None and re.match(r"^(?:https?:)?//", value):
                self.remote_references.append(value)
        if tag == "meta" and values.get("http-equiv") == "Content-Security-Policy":
            self.csp = str(values.get("content", ""))


def _malicious_bundle(tmp_path: Path) -> Path:
    trial = TrialRunner().run_sync(
        case=make_refund_case(),
        world_factory=RefundWorld,
        agent=AGENTS["naive"],
        contracts=REFUND_CONTRACTS,
        write_failure=False,
    )
    malicious = '<script>alert("report")</script><img src=x onerror=alert(1)>'
    violation = ContractViolation(
        code="injected_markup",
        contract=malicious,
        message=malicious,
        path="$.refunds</td><script>alert(2)</script>",
        details={"payload": malicious},
    )
    event = trial.events[0].model_copy(
        update={"kind": EventKind.READ, "operation": malicious, "data": {"payload": malicious}}
    )
    adapter = AdapterInfo(name=malicious)
    changed = trial.model_copy(
        update={
            "agent_name": malicious,
            "adapter": adapter,
            "contract_ids": (malicious,),
            "events": (event,),
            "contracts": ContractReport(passed=False, violations=(violation,)),
        }
    )
    return FailureStore(tmp_path).write(changed)


def test_checked_fixture_renders_deterministically_with_semantic_structure(tmp_path: Path) -> None:
    bundle = FailureBundle.load(FIXTURE)
    first = render_bundle_report(bundle)
    second = render_bundle_report(bundle)
    output = write_bundle_report(bundle, tmp_path / "report.html")

    assert first == second == output.read_text(encoding="utf-8")
    parser = _ReportStructure()
    parser.feed(first)
    assert {
        "identity",
        "faults",
        "timeline",
        "violations",
        "state-diff",
        "reduction",
        "reproduction",
        "raw",
    } <= parser.ids
    assert "script" not in parser.tags
    assert not parser.remote_references
    assert "default-src 'none'" in parser.csp
    assert "expected 1 refund" in first.lower()
    assert "observed 2 refunds" in first.lower()
    assert "timeout_after_commit" in first
    assert "locally_minimal_under_configured_reducers" in first


def test_report_escapes_all_bundle_controlled_markup(tmp_path: Path) -> None:
    bundle = FailureBundle.load(_malicious_bundle(tmp_path))
    rendered = render_bundle_report(bundle)

    assert '<script>alert("report")</script>' not in rendered
    assert "<img src=x onerror=alert(1)>" not in rendered
    assert "&lt;script&gt;alert" in rendered
    parser = _ReportStructure()
    parser.feed(rendered)
    assert "script" not in parser.tags
    assert "img" not in parser.tags
    assert not parser.remote_references


def test_report_creation_has_no_network_path(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def reject_network(_socket: socket.socket, _address: object) -> None:
        pytest.fail("report generation attempted a network connection")

    monkeypatch.setattr(socket.socket, "connect", reject_network)
    bundle = FailureBundle.load(FIXTURE)
    output = write_bundle_report(bundle, tmp_path / "offline.html")

    assert output.is_file()
    assert "http://" not in output.read_text(encoding="utf-8")
    assert "https://" not in output.read_text(encoding="utf-8")


def test_bundle_report_cli_verifies_and_never_resolves_reproducer(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        reproduction,
        "entry_points",
        lambda **_kwargs: pytest.fail("report resolved reproducer code"),
    )
    output = tmp_path / "failure.html"
    result = CliRunner().invoke(
        app,
        ["bundle", "report", str(FIXTURE), "--output", str(output)],
    )

    assert result.exit_code == 0, result.stdout
    assert output.is_file()
    assert "no reproducer code executed" in " ".join(result.stdout.split())


def test_bundle_report_open_uses_only_local_file_uri(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    opened: list[str] = []

    def open_local(uri: str) -> bool:
        opened.append(uri)
        return True

    monkeypatch.setattr("webbrowser.open", open_local)

    result = CliRunner().invoke(
        app,
        ["bundle", "report", str(FIXTURE), "--output", str(tmp_path / "open.html"), "--open"],
    )

    assert result.exit_code == 0, result.stdout
    assert len(opened) == 1
    assert opened[0].startswith("file://")
    assert not opened[0].startswith(("http://", "https://"))


def test_tampered_bundle_cannot_generate_report(tmp_path: Path) -> None:
    bundle = _malicious_bundle(tmp_path)
    (bundle / "trace.json").write_bytes((bundle / "trace.json").read_bytes() + b"tampered")
    output = tmp_path / "should-not-exist.html"

    result = CliRunner().invoke(
        app,
        ["bundle", "report", str(bundle), "--output", str(output)],
    )

    assert result.exit_code == 2
    assert not output.exists()


def test_report_cannot_invalidate_verified_bundle_file_set(tmp_path: Path) -> None:
    bundle_path = _malicious_bundle(tmp_path)
    bundle = FailureBundle.load(bundle_path)

    with pytest.raises(ValueError, match="outside the verified bundle"):
        write_bundle_report(bundle, bundle_path / "report.html")

    assert FailureBundle.load(bundle_path).manifest == bundle.manifest
