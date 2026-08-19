"""Verified, portable failure bundles for CI artifacts and regression tests."""

from __future__ import annotations

import hashlib
import hmac
import json
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import TypeAlias

from pydantic import BaseModel, TypeAdapter, ValidationError

from . import __version__
from .models import (
    AdapterInfo,
    BundleFile,
    ContractViolation,
    FailureBundleManifest,
    FaultRule,
    JsonObject,
    ReductionReport,
    ShrinkReport,
    TestCase,
    TraceEvent,
    TrialResult,
)
from .signatures import extract_failure_signature

SCHEMA_VERSION = "agent-effects.failure/v1alpha1"
MAX_MANIFEST_BYTES = 1_000_000
MAX_PAYLOAD_BYTES = 10_000_000


class BundleVerificationError(ValueError):
    """Raised when a bundle fails integrity or internal-consistency checks."""


def _json_bytes(value: object) -> bytes:
    return (json.dumps(value, indent=2, sort_keys=True) + "\n").encode()


def _model_bytes(value: BaseModel) -> bytes:
    return _json_bytes(value.model_dump(mode="json"))


def _sha256(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def _trace_jsonl(events: tuple[TraceEvent, ...]) -> bytes:
    return b"".join(
        (
            json.dumps(
                event.model_dump(mode="json"),
                sort_keys=True,
                separators=(",", ":"),
            ).encode()
            + b"\n"
        )
        for event in events
    )


def _legacy_failure_digest(result: TrialResult) -> str:
    canonical = json.dumps(
        {
            "case": result.case.model_dump(mode="json"),
            "signature": result.signature,
            "agent": result.agent_name,
        },
        sort_keys=True,
        separators=(",", ":"),
    )
    return _sha256(canonical.encode())


def _failure_digest(result: TrialResult) -> str:
    canonical = json.dumps(
        {
            "case": result.case.model_dump(mode="json"),
            "failure_signature": extract_failure_signature(result).model_dump(mode="json"),
            "agent": result.agent_name,
        },
        sort_keys=True,
        separators=(",", ":"),
    )
    return _sha256(canonical.encode())


def _safe_payload_path(root: Path, relative: str) -> Path:
    candidate = root / relative
    try:
        candidate.resolve().relative_to(root.resolve())
    except ValueError as exc:
        raise BundleVerificationError(
            f"bundle payload path escapes its root: {relative!r}"
        ) from exc
    if candidate.is_symlink():
        raise BundleVerificationError(f"bundle payload may not be a symlink: {relative}")
    return candidate


def _read_limited(path: Path, *, limit: int) -> bytes:
    if not path.is_file():
        raise BundleVerificationError(f"missing bundle file: {path.name}")
    size = path.stat().st_size
    if size > limit:
        raise BundleVerificationError(
            f"bundle file exceeds the {limit}-byte safety limit: {path.name}"
        )
    return path.read_bytes()


def _next_destination(root: Path, stem: str, content_digest: str) -> Path:
    candidate = root / stem
    if candidate.exists():
        manifest_path = candidate / "manifest.json"
        existing_digest: str | None = None
        try:
            existing = FailureBundleManifest.model_validate_json(
                _read_limited(manifest_path, limit=MAX_MANIFEST_BYTES)
            )
            existing_digest = existing.content_digest
        except (BundleVerificationError, ValidationError):
            pass
        if existing_digest != content_digest:
            candidate = root / f"{stem}-{content_digest[12:20]}"
    base_name = candidate.name
    suffix = 1
    while candidate.exists():
        suffix += 1
        candidate = root / f"{base_name}-{suffix}"
    return candidate


ShrinkArtifact: TypeAlias = ShrinkReport | ReductionReport


@dataclass(frozen=True, slots=True)
class FailureBundle:
    """An integrity-checked bundle loaded into typed portable models."""

    root: Path
    manifest: FailureBundleManifest
    case: TestCase
    minimized_case: TestCase
    initial_world: JsonObject | None
    final_world: JsonObject | None
    faults: tuple[FaultRule, ...]
    trace: tuple[TraceEvent, ...]
    violations: tuple[ContractViolation, ...]
    result: TrialResult
    shrink: ShrinkArtifact | None = None

    @classmethod
    def load(cls, path: Path, *, verify: bool = True) -> FailureBundle:
        """Load a bundle, verifying hashes and cross-file identities by default."""

        root = path.resolve()
        if not root.is_dir():
            raise BundleVerificationError(f"bundle path is not a directory: {path}")
        manifest_path = root / "manifest.json"
        if manifest_path.is_symlink():
            raise BundleVerificationError("bundle manifest may not be a symlink")
        manifest_payload = _read_limited(manifest_path, limit=MAX_MANIFEST_BYTES)
        try:
            manifest = FailureBundleManifest.model_validate_json(manifest_payload)
        except ValidationError as exc:
            raise BundleVerificationError(
                "unsupported or malformed bundle manifest; alpha bundles without "
                "content hashes must be regenerated"
            ) from exc

        entries = {item.path: item for item in manifest.files}
        expected_files = {"manifest.json", *entries}
        actual_files: set[str] = set()
        for item in root.rglob("*"):
            if item.is_symlink():
                raise BundleVerificationError(
                    f"bundle contents may not contain symlinks: {item.name}"
                )
            if item.is_file():
                actual_files.add(item.relative_to(root).as_posix())
        if actual_files != expected_files:
            missing = sorted(expected_files - actual_files)
            extra = sorted(actual_files - expected_files)
            raise BundleVerificationError(
                f"bundle file set mismatch; missing={missing}, unlisted={extra}"
            )

        payloads: dict[str, bytes] = {}
        for relative, entry in entries.items():
            file_path = _safe_payload_path(root, relative)
            payload = _read_limited(file_path, limit=MAX_PAYLOAD_BYTES)
            if len(payload) != entry.size:
                raise BundleVerificationError(f"size mismatch for {relative}")
            if verify and not hmac.compare_digest(_sha256(payload), entry.sha256):
                raise BundleVerificationError(f"SHA-256 mismatch for {relative}")
            payloads[relative] = payload

        required = {
            "case.json",
            "minimized-case.json",
            "initial-world.json",
            "final-world.json",
            "faults.json",
            "trace.json",
            "violations.json",
            "result.json",
            "reproduce.md",
        }
        absent = sorted(required - payloads.keys())
        if absent:
            raise BundleVerificationError(f"bundle is missing required payloads: {absent}")

        try:
            case = TestCase.model_validate_json(payloads["case.json"])
            minimized_case = TestCase.model_validate_json(payloads["minimized-case.json"])
            initial_world: JsonObject | None = TypeAdapter(JsonObject | None).validate_json(
                payloads["initial-world.json"]
            )
            final_world: JsonObject | None = TypeAdapter(JsonObject | None).validate_json(
                payloads["final-world.json"]
            )
            faults = TypeAdapter(tuple[FaultRule, ...]).validate_json(payloads["faults.json"])
            trace = TypeAdapter(tuple[TraceEvent, ...]).validate_json(payloads["trace.json"])
            violations = TypeAdapter(tuple[ContractViolation, ...]).validate_json(
                payloads["violations.json"]
            )
            result = TrialResult.model_validate_json(payloads["result.json"])
            shrink_payload = payloads.get("reduction-report.json", payloads.get("shrink.json"))
            shrink = (
                TypeAdapter(ShrinkArtifact).validate_json(shrink_payload)
                if shrink_payload is not None
                else None
            )
        except ValidationError as exc:
            raise BundleVerificationError(f"bundle payload validation failed: {exc}") from exc

        cls._verify_relationships(
            manifest=manifest,
            case=case,
            minimized_case=minimized_case,
            initial_world=initial_world,
            final_world=final_world,
            faults=faults,
            trace=trace,
            violations=violations,
            result=result,
            shrink=shrink,
            payloads=payloads,
        )
        return cls(
            root=root,
            manifest=manifest,
            case=case,
            minimized_case=minimized_case,
            initial_world=initial_world,
            final_world=final_world,
            faults=faults,
            trace=trace,
            violations=violations,
            result=result,
            shrink=shrink,
        )

    @staticmethod
    def _verify_relationships(
        *,
        manifest: FailureBundleManifest,
        case: TestCase,
        minimized_case: TestCase,
        initial_world: JsonObject | None,
        final_world: JsonObject | None,
        faults: tuple[FaultRule, ...],
        trace: tuple[TraceEvent, ...],
        violations: tuple[ContractViolation, ...],
        result: TrialResult,
        shrink: ShrinkArtifact | None,
        payloads: dict[str, bytes],
    ) -> None:
        if manifest.case_id != case.id or result.case != case:
            raise BundleVerificationError("case identifiers do not match across bundle files")
        if result.agent_name != manifest.adapter.name:
            raise BundleVerificationError("adapter identity does not match the trial result")
        if result.adapter != manifest.adapter:
            raise BundleVerificationError("adapter metadata does not match the trial result")
        if result.contract_ids != manifest.contract_ids:
            raise BundleVerificationError("contract identifiers do not match the trial result")
        if result.initial_state != initial_world or result.final_state != final_world:
            raise BundleVerificationError("world snapshots do not match the trial result")
        if result.events != trace or result.contracts.violations != violations:
            raise BundleVerificationError("trace or violations do not match the trial result")
        if case.faults != faults:
            raise BundleVerificationError("fault schedule does not match the original case")
        if result.signature != manifest.signature:
            raise BundleVerificationError("failure signature does not match the manifest")
        if manifest.content_digest is None:
            expected_digest = _legacy_failure_digest(result)
        else:
            expected_digest = _failure_digest(result)
            if not hmac.compare_digest(expected_digest, manifest.content_digest):
                raise BundleVerificationError("full content digest does not match bundle content")
        if expected_digest[:12] != manifest.failure_id:
            raise BundleVerificationError("display failure ID does not match bundle content")
        exact_signature = extract_failure_signature(result)
        if manifest.failure_signature is not None and manifest.failure_signature != exact_signature:
            raise BundleVerificationError("typed failure signature does not match the result")
        category = result.primary_failure_category or "unknown"
        if category != manifest.primary_failure_category:
            raise BundleVerificationError("primary failure category does not match result")
        if manifest.reproducer_id != result.reproducer_id:
            raise BundleVerificationError("reproducer identity does not match the trial result")
        if manifest.minimized != (shrink is not None):
            raise BundleVerificationError("manifest minimized flag does not match bundle content")
        if shrink is not None:
            if shrink.original != case or shrink.minimized != minimized_case:
                raise BundleVerificationError("shrink report cases do not match bundle cases")
            if isinstance(shrink, ReductionReport) and shrink.target_signature != exact_signature:
                raise BundleVerificationError(
                    "reduction target signature does not match the original result"
                )
        elif minimized_case != case:
            raise BundleVerificationError("unreported minimized case differs from original case")
        if "trace.jsonl" in payloads:
            expected_jsonl = _trace_jsonl(trace)
            if payloads["trace.jsonl"] != expected_jsonl:
                raise BundleVerificationError("legacy trace.jsonl does not match trace.json")


class FailureStore:
    """Write versioned failure bundles without overwriting an earlier bundle."""

    def __init__(self, root: Path) -> None:
        self.root = root

    def write(
        self,
        result: TrialResult,
        *,
        shrink: ShrinkArtifact | None = None,
    ) -> Path:
        """Persist one self-consistent bundle and return its directory."""

        content_digest = _failure_digest(result)
        failure_id = content_digest[:12]
        self.root.mkdir(parents=True, exist_ok=True)
        destination = _next_destination(
            self.root,
            f"{result.case.id}-{failure_id}",
            content_digest,
        )
        destination.mkdir()

        minimized_case = shrink.minimized if shrink is not None else result.case
        adapter = result.adapter or AdapterInfo(name=result.agent_name)
        portable_result = result.model_copy(update={"artifact_path": None, "adapter": adapter})
        reproduction_text = "\n".join(
            [
                "# Reproduce this Agent Effects failure",
                "",
                "Verify and rerun the reduced case stored as minimized-case.json:",
                "",
                "```bash",
                "agent-effects bundle verify .",
                "agent-effects reproduce --dry-run .",
                "agent-effects reproduce .",
                "```",
                "",
                (
                    f"Registered reproducer: `{result.reproducer_id}`"
                    if result.reproducer_id
                    else "No registered reproducer was declared for this bundle."
                ),
                "",
                (
                    "`bundle verify` and `bundle inspect` do not execute code. "
                    "`reproduce` executes the installed registered reproducer."
                ),
                "",
            ]
        ).encode()
        trace_jsonl = _trace_jsonl(portable_result.events)
        readme_text = "\n".join(
            [
                f"# Agent Effects failure `{failure_id}`",
                "",
                f"- Case: `{result.case.id}`",
                f"- Agent: `{result.agent_name}`",
                f"- Contract signature: `{', '.join(result.signature)}`",
                f"- Reduced case included: `{'yes' if shrink is not None else 'no'}`",
                "",
                "Run `agent-effects bundle inspect .` to inspect this bundle.",
                "",
            ]
        ).encode()

        payloads: dict[str, tuple[str, bytes]] = {
            "case.json": ("original_case", _model_bytes(result.case)),
            "minimized-case.json": ("minimized_case", _model_bytes(minimized_case)),
            "initial-world.json": ("initial_world", _json_bytes(result.initial_state)),
            "final-world.json": ("final_world", _json_bytes(result.final_state)),
            "faults.json": (
                "fault_schedule",
                _json_bytes([item.model_dump(mode="json") for item in result.case.faults]),
            ),
            "trace.json": (
                "trace",
                _json_bytes([item.model_dump(mode="json") for item in result.events]),
            ),
            "violations.json": (
                "violations",
                _json_bytes([item.model_dump(mode="json") for item in result.contracts.violations]),
            ),
            "result.json": ("trial_result", _model_bytes(portable_result)),
            "reproduce.md": ("reproduction_instructions", reproduction_text),
            "trace.jsonl": ("legacy_trace", trace_jsonl),
            "README.md": ("legacy_readme", readme_text),
        }
        if isinstance(shrink, ReductionReport):
            payloads["reduction-report.json"] = (
                "reduction_report",
                _model_bytes(shrink),
            )
        elif shrink is not None:
            payloads["shrink.json"] = ("shrink_report", _model_bytes(shrink))

        entries: list[BundleFile] = []
        for relative in sorted(payloads):
            role, payload = payloads[relative]
            (destination / relative).write_bytes(payload)
            entries.append(
                BundleFile(
                    path=relative,
                    role=role,
                    sha256=_sha256(payload),
                    size=len(payload),
                )
            )

        manifest = FailureBundleManifest(
            toolkit_version=__version__,
            created_at=datetime.now(UTC).isoformat(),
            failure_id=failure_id,
            content_digest=content_digest,
            case_id=result.case.id,
            subject=result.case.subject,
            test_ids=(result.case.id,),
            contract_ids=result.contract_ids,
            adapter=adapter,
            primary_failure_category=result.primary_failure_category or "unknown",
            signature=result.signature,
            failure_signature=extract_failure_signature(result),
            reproducer_id=result.reproducer_id,
            minimized=shrink is not None,
            files=tuple(entries),
        )
        (destination / "manifest.json").write_bytes(_model_bytes(manifest))

        FailureBundle.load(destination)
        return destination


def verify_bundle(path: Path) -> FailureBundle:
    """Verify and load a portable failure bundle."""

    return FailureBundle.load(path)


def load_result(path: Path) -> TrialResult:
    """Load a result directly, preserving compatibility with early alpha callers."""

    file_path = path / "result.json" if path.is_dir() else path
    return TrialResult.model_validate_json(file_path.read_text(encoding="utf-8"))
