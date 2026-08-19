"""Stable, JSON-serializable models used across the testkit."""

from __future__ import annotations

from enum import StrEnum
from pathlib import PurePosixPath
from typing import Any, ClassVar, Literal, TypeAlias

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    PositiveInt,
    field_validator,
    model_validator,
)
from pydantic import JsonValue as PydanticJsonValue

# Pydantic ships a named recursive JSON value type. Reusing it avoids the
# recursion problems that anonymous recursive aliases trigger during schema
# generation while keeping every portable artifact JSON-only.
JsonValue: TypeAlias = PydanticJsonValue
JsonObject: TypeAlias = dict[str, PydanticJsonValue]


class FrozenModel(BaseModel):
    model_config: ClassVar[ConfigDict] = ConfigDict(
        frozen=True,
        extra="forbid",
    )


class FaultMode(StrEnum):
    """Where a simulated failure occurs relative to a business commit."""

    TIMEOUT_BEFORE = "timeout_before"
    TIMEOUT_AFTER_COMMIT = "timeout_after_commit"


class FaultRule(FrozenModel):
    operation: str = Field(min_length=1)
    mode: FaultMode
    occurrence: PositiveInt = 1
    metadata: JsonObject = Field(default_factory=dict)


class TestCase(FrozenModel):
    """Portable input to one agent trial.

    ``world`` contains domain-specific initial state. The framework deliberately
    keeps this as JSON so adapters can target databases, HTTP sandboxes, MCP
    servers, or in-memory fakes without inheriting a framework data model.
    """

    __test__: ClassVar[bool] = False

    schema_version: Literal["agent-effects.case/v1alpha1"] = "agent-effects.case/v1alpha1"
    id: str = Field(
        min_length=1,
        max_length=128,
        pattern=r"^[A-Za-z0-9][A-Za-z0-9._-]*$",
    )
    subject: str = Field(default="unspecified", min_length=1)
    seed: int = 0
    actor: JsonObject = Field(default_factory=dict)
    goal: JsonObject = Field(default_factory=dict)
    world: JsonObject = Field(default_factory=dict)
    faults: tuple[FaultRule, ...] = ()
    metadata: JsonObject = Field(default_factory=dict)

    @model_validator(mode="after")
    def reject_duplicate_fault_rules(self) -> TestCase:
        keys = [(item.operation, item.occurrence) for item in self.faults]
        if len(keys) != len(set(keys)):
            raise ValueError("only one fault may target an operation occurrence")
        return self


class EventKind(StrEnum):
    AGENT = "agent"
    READ = "read"
    POLICY = "policy"
    TOOL_CALL = "tool_call"
    COMMIT = "commit"
    IDEMPOTENCY_HIT = "idempotency_hit"
    FAULT = "fault"
    ERROR = "error"


class FailureStage(StrEnum):
    """Runner lifecycle stage at which a structured failure occurred."""

    WORLD_CREATION = "world_creation"
    INITIAL_SNAPSHOT = "initial_snapshot"
    AGENT_EXECUTION = "agent_execution"
    FINAL_SNAPSHOT = "final_snapshot"
    CONTRACT_EVALUATION = "contract_evaluation"
    CLEANUP = "cleanup"
    ARTIFACT_GENERATION = "artifact_generation"


class FailureCategory(StrEnum):
    """High-level ownership category for a runner lifecycle failure."""

    INFRASTRUCTURE = "infrastructure"
    AGENT = "agent"
    CONTRACT = "contract"
    ARTIFACT = "artifact"


class TraceEvent(FrozenModel):
    sequence: int = Field(ge=0)
    kind: EventKind
    operation: str = Field(min_length=1)
    data: JsonObject = Field(default_factory=dict)


class AgentRun(FrozenModel):
    status: Literal["completed", "blocked", "error"]
    output: str = ""
    error_type: str | None = None
    error_message: str | None = None
    metadata: JsonObject = Field(default_factory=dict)


class AdapterInfo(FrozenModel):
    """Portable identity for the adapter used by a trial."""

    name: str = Field(min_length=1)
    kind: str = Field(default="python", min_length=1)
    module: str | None = None
    qualname: str | None = None


class LifecycleFailure(FrozenModel):
    """Typed failure captured while the runner advances through its lifecycle."""

    stage: FailureStage
    category: FailureCategory
    exception_type: str = Field(min_length=1)
    message: str
    primary: bool
    details: JsonObject = Field(default_factory=dict)


class ContractViolation(FrozenModel):
    code: str = Field(min_length=1)
    message: str = Field(min_length=1)
    contract: str = Field(min_length=1)
    path: str | None = None
    details: JsonObject = Field(default_factory=dict)


class ContractReport(FrozenModel):
    passed: bool
    violations: tuple[ContractViolation, ...] = ()

    @property
    def codes(self) -> tuple[str, ...]:
        return tuple(sorted({item.code for item in self.violations}))


class EvaluationContext(FrozenModel):
    case: TestCase
    agent_name: str
    agent_run: AgentRun
    initial_state: JsonObject
    final_state: JsonObject
    events: tuple[TraceEvent, ...]


class TrialResult(FrozenModel):
    schema_version: Literal["agent-effects.result/v1alpha1"] = "agent-effects.result/v1alpha1"
    case: TestCase
    agent_name: str
    adapter: AdapterInfo | None = None
    contract_ids: tuple[str, ...] = ()
    reproducer_id: str | None = None
    initial_state: JsonObject | None
    final_state: JsonObject | None
    events: tuple[TraceEvent, ...]
    agent_run: AgentRun | None
    contracts: ContractReport
    lifecycle_failures: tuple[LifecycleFailure, ...] = ()
    elapsed_ms: float = Field(ge=0)
    artifact_path: str | None = None

    @model_validator(mode="after")
    def reject_multiple_primary_failures(self) -> TrialResult:
        if sum(item.primary for item in self.lifecycle_failures) > 1:
            raise ValueError("at most one lifecycle failure may be primary")
        return self

    @property
    def passed(self) -> bool:
        return self.contracts.passed and not self.lifecycle_failures

    @property
    def signature(self) -> tuple[str, ...]:
        return self.contracts.codes

    @property
    def primary_failure(self) -> LifecycleFailure | None:
        return next((item for item in self.lifecycle_failures if item.primary), None)

    @property
    def primary_failure_category(self) -> str | None:
        failure = self.primary_failure
        if failure is not None:
            return failure.category.value
        if self.contracts.violations:
            return FailureCategory.CONTRACT.value
        return None


class ContractFailureIdentity(FrozenModel):
    """Stable identity and multiplicity for one kind of contract violation."""

    contract_id: str = Field(min_length=1)
    violation_code: str = Field(min_length=1)
    count: PositiveInt = 1


class FailureSignature(FrozenModel):
    """Portable failure identity that excludes unstable diagnostic text."""

    schema_version: Literal["agent-effects.signature/v1alpha1"] = "agent-effects.signature/v1alpha1"
    primary_category: str = Field(min_length=1)
    primary_stage: FailureStage | None = None
    exception_type: str | None = None
    stable_error_code: str | None = None
    contract_failures: tuple[ContractFailureIdentity, ...] = ()


class ReductionStopReason(StrEnum):
    """Why reduction stopped; current writers never emit legacy ``minimal``."""

    LOCALLY_MINIMAL = "locally_minimal"
    EVALUATION_BUDGET_EXHAUSTED = "evaluation_budget_exhausted"
    TIME_BUDGET_EXHAUSTED = "time_budget_exhausted"
    UNSTABLE_BASELINE = "unstable_baseline"
    INVALID_BASELINE = "invalid_baseline"
    BASELINE_DID_NOT_REPRODUCE = "baseline_did_not_reproduce"
    LEGACY_MINIMAL = "minimal"


class ReductionGuarantee(StrEnum):
    """Scope of the minimality claim supported by a reduction report."""

    LOCALLY_MINIMAL_UNDER_CONFIGURED_REDUCERS = "locally_minimal_under_configured_reducers"
    BUDGET_LIMITED_REDUCTION = "budget_limited_reduction"
    NO_MINIMALITY_CLAIM = "no_minimality_claim"


class ReductionObservation(FrozenModel):
    """One baseline observation retained when stability is checked."""

    signature: FailureSignature
    trace: tuple[TraceEvent, ...] = ()


class ReductionStep(FrozenModel):
    """One accepted, strictly complexity-reducing candidate."""

    reducer: str = Field(min_length=1)
    explanation: str = Field(min_length=1)
    before_digest: str = Field(pattern=r"^[0-9a-f]{64}$")
    after_digest: str = Field(pattern=r"^[0-9a-f]{64}$")
    before_size: int = Field(ge=0)
    after_size: int = Field(ge=0)


class ReductionReport(FrozenModel):
    """Defensible record of a deterministic hierarchical reduction run."""

    schema_version: Literal["agent-effects.reduction/v1alpha1"] = "agent-effects.reduction/v1alpha1"
    original: TestCase
    minimized: TestCase = Field(
        description=(
            "Reduced case retained under the historical field name; this field does not "
            "assert global minimality."
        )
    )
    initial_case_digest: str = Field(pattern=r"^[0-9a-f]{64}$")
    final_case_digest: str = Field(pattern=r"^[0-9a-f]{64}$")
    initial_size: int = Field(ge=0)
    final_size: int = Field(ge=0)
    target_signature: FailureSignature
    reducers_used: tuple[str, ...] = ()
    validity_predicate: str = Field(default="unspecified", min_length=1)
    baseline_observations: tuple[ReductionObservation, ...] = ()
    candidate_evaluations: int = Field(ge=0)
    cache_hits: int = Field(ge=0)
    invalid_candidates_skipped: int = Field(ge=0)
    different_failures: int = Field(ge=0)
    accepted_reductions: tuple[ReductionStep, ...] = ()
    elapsed_ms: float = Field(ge=0)
    evaluation_budget: PositiveInt
    time_budget_ms: float | None = Field(default=None, gt=0)
    evaluation_budget_exhausted: bool = False
    time_budget_exhausted: bool = False
    confirm_signature_runs: PositiveInt
    stop_reason: ReductionStopReason
    guarantee: ReductionGuarantee = ReductionGuarantee.NO_MINIMALITY_CLAIM
    diagnostic: str


class ShrinkStep(FrozenModel):
    reducer: str
    before_size: int = Field(ge=0)
    after_size: int = Field(ge=0)


class ShrinkReport(FrozenModel):
    original: TestCase
    minimized: TestCase
    target_signature: tuple[str, ...]
    evaluations: int = Field(ge=0)
    accepted_steps: tuple[ShrinkStep, ...] = ()


class BundleFile(FrozenModel):
    """One content-addressed payload in a portable failure bundle."""

    path: str = Field(min_length=1, max_length=256)
    role: str = Field(min_length=1)
    sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    size: int = Field(ge=0)

    @field_validator("path")
    @classmethod
    def validate_portable_relative_path(cls, value: str) -> str:
        path = PurePosixPath(value)
        if path.is_absolute() or ".." in path.parts or value != path.as_posix():
            raise ValueError("bundle paths must be normalized portable relative paths")
        if any(part in {"", "."} for part in path.parts):
            raise ValueError("bundle paths may not contain empty or current-directory parts")
        return value


class FailureBundleManifest(FrozenModel):
    """Versioned, content-addressed index for a failure bundle."""

    schema_version: Literal["agent-effects.failure/v1alpha1"] = "agent-effects.failure/v1alpha1"
    toolkit_version: str = Field(min_length=1)
    created_at: str = Field(min_length=1)
    failure_id: str = Field(pattern=r"^[0-9a-f]{12}$")
    content_digest: str | None = Field(default=None, pattern=r"^[0-9a-f]{64}$")
    case_id: str = Field(min_length=1)
    subject: str = Field(min_length=1)
    test_ids: tuple[str, ...]
    contract_ids: tuple[str, ...]
    adapter: AdapterInfo
    primary_failure_category: str = Field(min_length=1)
    signature: tuple[str, ...]
    failure_signature: FailureSignature | None = None
    reproducer_id: str | None = None
    minimized: bool = Field(
        description=(
            "Whether a reduced case/report is included; this compatibility field does "
            "not assert global minimality."
        )
    )
    files: tuple[BundleFile, ...] = Field(min_length=1)

    @model_validator(mode="after")
    def reject_duplicate_payload_paths(self) -> FailureBundleManifest:
        paths = [item.path for item in self.files]
        if len(paths) != len(set(paths)):
            raise ValueError("bundle manifest paths must be unique")
        return self


def json_size(value: Any) -> int:
    """Return a stable rough complexity measure used by the greedy shrinker."""

    if value is None or isinstance(value, bool | int | float | str):
        return 1
    if isinstance(value, list | tuple):
        return 1 + sum(json_size(item) for item in value)
    if isinstance(value, dict):
        return 1 + sum(1 + json_size(item) for item in value.values())
    if isinstance(value, BaseModel):
        return json_size(value.model_dump(mode="json"))
    raise TypeError(f"unsupported JSON-like value: {type(value)!r}")
