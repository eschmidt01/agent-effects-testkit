from __future__ import annotations

import asyncio
import hashlib
import json
from pathlib import Path

import pytest

import agent_effects.artifacts as artifacts
from agent_effects.artifacts import (
    BundleVerificationError,
    FailureBundle,
    FailureStore,
    load_result,
    verify_bundle,
)
from agent_effects.examples.refund import (
    AGENTS,
    REFUND_CONTRACTS,
    RefundWorld,
    make_refund_case,
)
from agent_effects.models import FaultMode
from agent_effects.runner import TrialRunner


def test_failure_bundle_is_portable_json(tmp_path: Path) -> None:
    result = asyncio.run(
        TrialRunner().run(
            case=make_refund_case(fault_mode=FaultMode.TIMEOUT_AFTER_COMMIT),
            world_factory=RefundWorld,
            agent=AGENTS["naive"],
            contracts=REFUND_CONTRACTS,
            write_failure=False,
        )
    )
    path = FailureStore(tmp_path).write(result)
    assert path.is_dir()
    assert {item.name for item in path.iterdir()} >= {
        "manifest.json",
        "case.json",
        "result.json",
        "trace.jsonl",
        "README.md",
    }
    manifest = json.loads((path / "manifest.json").read_text())
    assert manifest["schema_version"] == "agent-effects.failure/v1alpha1"
    assert manifest["signature"] == list(result.signature)
    assert len(manifest["content_digest"]) == 64
    assert manifest["failure_id"] == manifest["content_digest"][:12]
    assert manifest["failure_signature"]["primary_category"] == "contract"
    trace_lines = (path / "trace.jsonl").read_text().splitlines()
    assert len(trace_lines) == len(result.events)
    restored = load_result(path)
    assert restored == result
    bundle = FailureBundle.load(path)
    assert bundle.result == result
    assert bundle.minimized_case == result.case


def test_failure_bundle_keeps_original_and_minimized_cases_separate(tmp_path: Path) -> None:
    from agent_effects.models import ShrinkReport, ShrinkStep

    result = asyncio.run(
        TrialRunner().run(
            case=make_refund_case(
                fault_mode=FaultMode.TIMEOUT_AFTER_COMMIT,
                noise_records=4,
            ),
            world_factory=RefundWorld,
            agent=AGENTS["naive"],
            contracts=REFUND_CONTRACTS,
            write_failure=False,
        )
    )
    minimized = make_refund_case(
        fault_mode=FaultMode.TIMEOUT_AFTER_COMMIT,
        noise_records=0,
    )
    shrink = ShrinkReport(
        original=result.case,
        minimized=minimized,
        target_signature=result.signature,
        evaluations=2,
        accepted_steps=(ShrinkStep(reducer="reduce_world_list", before_size=10, after_size=5),),
    )

    path = FailureStore(tmp_path).write(result, shrink=shrink)
    original_payload = json.loads((path / "case.json").read_text())
    minimized_payload = json.loads((path / "minimized-case.json").read_text())
    manifest = json.loads((path / "manifest.json").read_text())

    assert original_payload == result.case.model_dump(mode="json")
    assert minimized_payload == minimized.model_dump(mode="json")
    assert manifest["minimized"] is True
    manifest_paths = {entry["path"] for entry in manifest["files"]}
    assert {"minimized-case.json", "shrink.json"} <= manifest_paths


def _write_reproducible_bundle(tmp_path: Path, *, case_id: str = "tamper-case") -> Path:
    result = asyncio.run(
        TrialRunner().run(
            case=make_refund_case(
                fault_mode=FaultMode.TIMEOUT_AFTER_COMMIT,
                case_id=case_id,
            ),
            world_factory=RefundWorld,
            agent=AGENTS["naive"],
            contracts=REFUND_CONTRACTS,
            write_failure=False,
            reproducer_id="agent-effects.examples.refund/naive/v1",
        )
    )
    return FailureStore(tmp_path).write(result)


def _replace_payload(bundle: Path, name: str, payload: bytes) -> None:
    (bundle / name).write_bytes(payload)
    manifest_path = bundle / "manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    for entry in manifest["files"]:
        if entry["path"] == name:
            entry["sha256"] = hashlib.sha256(payload).hexdigest()
            entry["size"] = len(payload)
    manifest_path.write_text(json.dumps(manifest), encoding="utf-8")


@pytest.mark.parametrize(
    "payload_name",
    [
        "case.json",
        "minimized-case.json",
        "initial-world.json",
        "final-world.json",
        "faults.json",
        "trace.json",
        "violations.json",
        "result.json",
        "reproduce.md",
        "trace.jsonl",
        "README.md",
    ],
)
def test_bundle_verification_detects_each_modified_payload(
    tmp_path: Path,
    payload_name: str,
) -> None:
    path = _write_reproducible_bundle(tmp_path / payload_name.replace(".", "-"))
    payload_path = path / payload_name
    payload_path.write_bytes(payload_path.read_bytes() + b"tampered")

    with pytest.raises(BundleVerificationError, match="mismatch"):
        FailureBundle.load(path)


def test_bundle_verification_detects_missing_and_unlisted_files(tmp_path: Path) -> None:
    missing_bundle = _write_reproducible_bundle(tmp_path / "missing")
    (missing_bundle / "trace.json").unlink()
    with pytest.raises(BundleVerificationError, match="file set mismatch"):
        FailureBundle.load(missing_bundle)

    extra_bundle = _write_reproducible_bundle(tmp_path / "extra")
    (extra_bundle / "unrelated.json").write_text("{}\n", encoding="utf-8")
    with pytest.raises(BundleVerificationError, match="unlisted"):
        FailureBundle.load(extra_bundle)


def test_bundle_verification_rejects_traversal_and_incompatible_versions(
    tmp_path: Path,
) -> None:
    traversal_bundle = _write_reproducible_bundle(tmp_path / "traversal")
    manifest_path = traversal_bundle / "manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    manifest["files"][0]["path"] = "../case.json"
    manifest_path.write_text(json.dumps(manifest), encoding="utf-8")
    with pytest.raises(BundleVerificationError, match="malformed bundle manifest"):
        FailureBundle.load(traversal_bundle)

    version_bundle = _write_reproducible_bundle(tmp_path / "version")
    version_manifest_path = version_bundle / "manifest.json"
    version_manifest = json.loads(version_manifest_path.read_text(encoding="utf-8"))
    version_manifest["schema_version"] = "agent-effects.failure/v999"
    version_manifest_path.write_text(json.dumps(version_manifest), encoding="utf-8")
    with pytest.raises(BundleVerificationError, match="unsupported"):
        FailureBundle.load(version_bundle)


def test_bundle_verification_rejects_cross_file_identity_mismatch(tmp_path: Path) -> None:
    first = _write_reproducible_bundle(tmp_path / "first", case_id="first-case")
    second = _write_reproducible_bundle(tmp_path / "second", case_id="second-case")
    replacement = (second / "case.json").read_bytes()
    (first / "case.json").write_bytes(replacement)

    manifest_path = first / "manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    for entry in manifest["files"]:
        if entry["path"] == "case.json":
            entry["sha256"] = hashlib.sha256(replacement).hexdigest()
            entry["size"] = len(replacement)
    manifest_path.write_text(json.dumps(manifest), encoding="utf-8")

    with pytest.raises(BundleVerificationError, match="case identifiers"):
        FailureBundle.load(first)


@pytest.mark.parametrize(
    ("field", "value", "message"),
    [
        ("contract_ids", ["unrelated"], "contract identifiers"),
        ("signature", ["unrelated"], "failure signature"),
        ("failure_id", "000000000000", "failure ID"),
        ("content_digest", "0" * 64, "full content digest"),
        ("primary_failure_category", "agent", "primary failure category"),
        ("reproducer_id", "unrelated", "reproducer identity"),
        ("minimized", True, "minimized flag"),
    ],
)
def test_bundle_manifest_identity_fields_are_cross_checked(
    tmp_path: Path,
    field: str,
    value: object,
    message: str,
) -> None:
    bundle = _write_reproducible_bundle(tmp_path / field)
    manifest_path = bundle / "manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    manifest[field] = value
    manifest_path.write_text(json.dumps(manifest), encoding="utf-8")

    with pytest.raises(BundleVerificationError, match=message):
        FailureBundle.load(bundle)


def test_bundle_adapter_metadata_is_cross_checked(tmp_path: Path) -> None:
    bundle = _write_reproducible_bundle(tmp_path)
    manifest_path = bundle / "manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    manifest["adapter"]["module"] = "unrelated.module"
    manifest_path.write_text(json.dumps(manifest), encoding="utf-8")

    with pytest.raises(BundleVerificationError, match="adapter metadata"):
        FailureBundle.load(bundle)


@pytest.mark.parametrize(
    ("payload_name", "replacement", "message"),
    [
        ("initial-world.json", b"{}\n", "world snapshots"),
        ("trace.json", b"[]\n", "trace or violations"),
        ("violations.json", b"[]\n", "trace or violations"),
        ("faults.json", b"[]\n", "fault schedule"),
    ],
)
def test_bundle_redundant_payloads_are_cross_checked(
    tmp_path: Path,
    payload_name: str,
    replacement: bytes,
    message: str,
) -> None:
    bundle = _write_reproducible_bundle(tmp_path / payload_name.replace(".", "-"))
    _replace_payload(bundle, payload_name, replacement)

    with pytest.raises(BundleVerificationError, match=message):
        FailureBundle.load(bundle)


def test_bundle_rejects_invalid_payload_even_with_matching_hash(tmp_path: Path) -> None:
    bundle = _write_reproducible_bundle(tmp_path)
    _replace_payload(bundle, "case.json", b"{}\n")

    with pytest.raises(BundleVerificationError, match="payload validation"):
        FailureBundle.load(bundle)


def test_bundle_requires_canonical_payload_roles(tmp_path: Path) -> None:
    bundle = _write_reproducible_bundle(tmp_path)
    manifest_path = bundle / "manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    manifest["files"] = [entry for entry in manifest["files"] if entry["path"] != "reproduce.md"]
    manifest_path.write_text(json.dumps(manifest), encoding="utf-8")
    (bundle / "reproduce.md").unlink()

    with pytest.raises(BundleVerificationError, match="required payloads"):
        FailureBundle.load(bundle)


def test_verification_can_skip_hashes_but_not_structural_checks(tmp_path: Path) -> None:
    bundle = _write_reproducible_bundle(tmp_path)
    readme = bundle / "README.md"
    payload = readme.read_bytes()
    readme.write_bytes(payload.replace(b"Agent", b"agent", 1))

    loaded = FailureBundle.load(bundle, verify=False)
    assert loaded.case.id == "tamper-case"


def test_verifier_helpers_support_direct_result_files_and_unique_writes(
    tmp_path: Path,
) -> None:
    result = asyncio.run(
        TrialRunner().run(
            case=make_refund_case(),
            world_factory=RefundWorld,
            agent=AGENTS["naive"],
            contracts=REFUND_CONTRACTS,
            write_failure=False,
        )
    )
    first = FailureStore(tmp_path).write(result)
    second = FailureStore(tmp_path).write(result)

    assert first != second
    assert verify_bundle(first).result == result
    assert load_result(first / "result.json") == result


def test_short_display_id_collision_uses_full_digest_for_safe_path(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    result = asyncio.run(
        TrialRunner().run(
            case=make_refund_case(),
            world_factory=RefundWorld,
            agent=AGENTS["naive"],
            contracts=REFUND_CONTRACTS,
            write_failure=False,
        )
    )
    first_digest = "a" * 64
    second_digest = "a" * 12 + "b" * 52
    values = iter((first_digest, first_digest, second_digest, second_digest))
    monkeypatch.setattr(artifacts, "_failure_digest", lambda _result: next(values))

    first = FailureStore(tmp_path).write(result)
    second = FailureStore(tmp_path).write(result)

    assert first.name.endswith("-" + "a" * 12)
    assert second.name.endswith("-" + "a" * 12 + "-" + "b" * 8)
    assert first != second


def test_bundle_path_must_be_a_directory(tmp_path: Path) -> None:
    file_path = tmp_path / "not-a-bundle"
    file_path.write_text("not a bundle", encoding="utf-8")
    with pytest.raises(BundleVerificationError, match="not a directory"):
        FailureBundle.load(file_path)


def test_legacy_v1alpha1_bundle_manifest_still_loads(tmp_path: Path) -> None:
    sample = _write_reproducible_bundle(tmp_path / "legacy")
    result = load_result(sample)
    manifest_path = sample / "manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    manifest.pop("content_digest")
    manifest.pop("failure_signature")
    manifest["failure_id"] = artifacts._legacy_failure_digest(result)[:12]
    manifest_path.write_text(json.dumps(manifest), encoding="utf-8")

    bundle = FailureBundle.load(sample)

    assert bundle.manifest.signature == (
        "duplicate_business_effect",
        "refund_cardinality",
    )
    assert bundle.manifest.reproducer_id == "agent-effects.examples.refund/naive/v1"
    assert bundle.manifest.content_digest is None


def test_checked_in_hierarchical_sample_has_typed_identity_and_report() -> None:
    sample = Path(__file__).parent / "fixtures" / "failure_bundles" / "refund-lost-ack"
    bundle = FailureBundle.load(sample)

    assert bundle.manifest.content_digest is not None
    assert bundle.manifest.failure_signature is not None
    assert bundle.shrink is not None
    assert bundle.shrink.model_dump(mode="json")["schema_version"] == (
        "agent-effects.reduction/v1alpha1"
    )
    assert bundle.shrink.model_dump(mode="json")["stop_reason"] == "locally_minimal"
