from __future__ import annotations

import pytest
from pydantic import ValidationError

from agent_effects.models import (
    AdapterInfo,
    BundleFile,
    FailureBundleManifest,
    FaultMode,
    FaultRule,
    TestCase,
    json_size,
)


def test_duplicate_fault_rules_are_rejected() -> None:
    rule = FaultRule(operation="write", mode=FaultMode.TIMEOUT_BEFORE)
    with pytest.raises(ValidationError):
        TestCase(id="duplicate", faults=(rule, rule))


def test_different_fault_modes_cannot_target_the_same_occurrence() -> None:
    with pytest.raises(ValidationError):
        TestCase(
            id="conflict",
            faults=(
                FaultRule(operation="write", mode=FaultMode.TIMEOUT_BEFORE),
                FaultRule(operation="write", mode=FaultMode.TIMEOUT_AFTER_COMMIT),
            ),
        )


def test_models_round_trip_json() -> None:
    case = TestCase(
        id="round-trip",
        world={"items": [{"id": 1}]},
        faults=(FaultRule(operation="write", mode=FaultMode.TIMEOUT_AFTER_COMMIT),),
    )
    restored = TestCase.model_validate_json(case.model_dump_json())
    assert restored == case
    assert json_size(case) > 1


def test_json_size_rejects_non_json_values() -> None:
    with pytest.raises(TypeError, match="unsupported JSON-like value"):
        json_size(object())


def test_case_id_rejects_path_separators_and_traversal() -> None:
    for unsafe in ("../escape", "nested/case", "/absolute", "has space"):
        with pytest.raises(ValidationError):
            TestCase(id=unsafe)


def test_bundle_file_rejects_nonportable_paths() -> None:
    for unsafe in ("../case.json", "/case.json", "nested/../case.json", "./case.json"):
        with pytest.raises(ValidationError, match="portable relative paths"):
            BundleFile(path=unsafe, role="case", sha256="0" * 64, size=1)


def test_bundle_manifest_rejects_duplicate_payload_paths() -> None:
    entry = BundleFile(path="case.json", role="case", sha256="0" * 64, size=1)
    with pytest.raises(ValidationError, match="must be unique"):
        FailureBundleManifest(
            toolkit_version="0.1.0a0",
            created_at="2026-08-19T00:00:00Z",
            failure_id="0" * 12,
            case_id="case",
            subject="test",
            test_ids=("case",),
            contract_ids=(),
            adapter=AdapterInfo(name="agent"),
            primary_failure_category="contract",
            signature=("failed",),
            minimized=False,
            files=(entry, entry),
        )
