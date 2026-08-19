"""Agent Effects Testkit public API.

The public names are loaded lazily so pytest can discover the optional plugin
without importing the full runtime before coverage and tracing hooks start.
"""

from __future__ import annotations

from importlib import import_module
from typing import TYPE_CHECKING

__version__ = "0.1.0a1"

if TYPE_CHECKING:
    from .adapters import CallableAgentAdapter
    from .artifacts import (
        BundleVerificationError,
        FailureBundle,
        FailureStore,
        load_result,
        verify_bundle,
    )
    from .contract_helpers import (
        at_most_one_effect,
        events_must_precede,
        exactly_one_effect,
        forbid_field_reads,
        no_effects_after_cancellation,
        records_must_link,
        requires_authorization_for_writes,
        unique_business_key,
    )
    from .contracts import FunctionContract, PredicateContract, contract, evaluate_contracts
    from .faults import FaultInjector, SemanticFault
    from .models import (
        AdapterInfo,
        AgentRun,
        BundleFile,
        ContractFailureIdentity,
        ContractReport,
        ContractViolation,
        EvaluationContext,
        EventKind,
        FailureBundleManifest,
        FailureCategory,
        FailureSignature,
        FailureStage,
        FaultMode,
        FaultRule,
        LifecycleFailure,
        ReductionGuarantee,
        ReductionReport,
        ReductionStopReason,
        ShrinkReport,
        TestCase,
        TraceEvent,
        TrialResult,
    )
    from .runner import TrialRunner
    from .schemas import export_schemas
    from .shrink import (
        ActorAttributeReducer,
        ArgumentReducer,
        FaultOccurrenceReducer,
        FaultScheduleReducer,
        GoalFieldReducer,
        GreedyShrinker,
        HierarchicalShrinker,
        ListDDMinReducer,
        MappingKeyReducer,
        ReduceWorldListReducer,
        RemoveFaultReducer,
        SetWorldValueReducer,
        WorldCollectionReducer,
    )
    from .signatures import case_digest, extract_failure_signature
    from .world import BaseWorld

_EXPORTS: dict[str, tuple[str, str]] = {
    "AdapterInfo": (".models", "AdapterInfo"),
    "AgentRun": (".models", "AgentRun"),
    "BaseWorld": (".world", "BaseWorld"),
    "BundleFile": (".models", "BundleFile"),
    "BundleVerificationError": (".artifacts", "BundleVerificationError"),
    "CallableAgentAdapter": (".adapters", "CallableAgentAdapter"),
    "ContractReport": (".models", "ContractReport"),
    "ContractFailureIdentity": (".models", "ContractFailureIdentity"),
    "ContractViolation": (".models", "ContractViolation"),
    "EvaluationContext": (".models", "EvaluationContext"),
    "EventKind": (".models", "EventKind"),
    "FailureBundle": (".artifacts", "FailureBundle"),
    "FailureBundleManifest": (".models", "FailureBundleManifest"),
    "FailureCategory": (".models", "FailureCategory"),
    "FailureSignature": (".models", "FailureSignature"),
    "FailureStage": (".models", "FailureStage"),
    "FailureStore": (".artifacts", "FailureStore"),
    "FaultInjector": (".faults", "FaultInjector"),
    "FaultMode": (".models", "FaultMode"),
    "FaultRule": (".models", "FaultRule"),
    "FunctionContract": (".contracts", "FunctionContract"),
    "GreedyShrinker": (".shrink", "GreedyShrinker"),
    "HierarchicalShrinker": (".shrink", "HierarchicalShrinker"),
    "LifecycleFailure": (".models", "LifecycleFailure"),
    "ReductionReport": (".models", "ReductionReport"),
    "ReductionGuarantee": (".models", "ReductionGuarantee"),
    "ReductionStopReason": (".models", "ReductionStopReason"),
    "PredicateContract": (".contracts", "PredicateContract"),
    "ReduceWorldListReducer": (".shrink", "ReduceWorldListReducer"),
    "RemoveFaultReducer": (".shrink", "RemoveFaultReducer"),
    "SemanticFault": (".faults", "SemanticFault"),
    "SetWorldValueReducer": (".shrink", "SetWorldValueReducer"),
    "ActorAttributeReducer": (".shrink", "ActorAttributeReducer"),
    "ArgumentReducer": (".shrink", "ArgumentReducer"),
    "FaultOccurrenceReducer": (".shrink", "FaultOccurrenceReducer"),
    "FaultScheduleReducer": (".shrink", "FaultScheduleReducer"),
    "GoalFieldReducer": (".shrink", "GoalFieldReducer"),
    "ListDDMinReducer": (".shrink", "ListDDMinReducer"),
    "MappingKeyReducer": (".shrink", "MappingKeyReducer"),
    "WorldCollectionReducer": (".shrink", "WorldCollectionReducer"),
    "ShrinkReport": (".models", "ShrinkReport"),
    "TestCase": (".models", "TestCase"),
    "TraceEvent": (".models", "TraceEvent"),
    "TrialResult": (".models", "TrialResult"),
    "TrialRunner": (".runner", "TrialRunner"),
    "contract": (".contracts", "contract"),
    "evaluate_contracts": (".contracts", "evaluate_contracts"),
    "export_schemas": (".schemas", "export_schemas"),
    "load_result": (".artifacts", "load_result"),
    "verify_bundle": (".artifacts", "verify_bundle"),
    "case_digest": (".signatures", "case_digest"),
    "extract_failure_signature": (".signatures", "extract_failure_signature"),
    "at_most_one_effect": (".contract_helpers", "at_most_one_effect"),
    "events_must_precede": (".contract_helpers", "events_must_precede"),
    "exactly_one_effect": (".contract_helpers", "exactly_one_effect"),
    "forbid_field_reads": (".contract_helpers", "forbid_field_reads"),
    "no_effects_after_cancellation": (
        ".contract_helpers",
        "no_effects_after_cancellation",
    ),
    "records_must_link": (".contract_helpers", "records_must_link"),
    "requires_authorization_for_writes": (
        ".contract_helpers",
        "requires_authorization_for_writes",
    ),
    "unique_business_key": (".contract_helpers", "unique_business_key"),
}

__all__ = [
    "ActorAttributeReducer",
    "AdapterInfo",
    "AgentRun",
    "ArgumentReducer",
    "BaseWorld",
    "BundleFile",
    "BundleVerificationError",
    "CallableAgentAdapter",
    "ContractFailureIdentity",
    "ContractReport",
    "ContractViolation",
    "EvaluationContext",
    "EventKind",
    "FailureBundle",
    "FailureBundleManifest",
    "FailureCategory",
    "FailureSignature",
    "FailureStage",
    "FailureStore",
    "FaultInjector",
    "FaultMode",
    "FaultOccurrenceReducer",
    "FaultRule",
    "FaultScheduleReducer",
    "FunctionContract",
    "GoalFieldReducer",
    "GreedyShrinker",
    "HierarchicalShrinker",
    "LifecycleFailure",
    "ListDDMinReducer",
    "MappingKeyReducer",
    "PredicateContract",
    "ReduceWorldListReducer",
    "ReductionGuarantee",
    "ReductionReport",
    "ReductionStopReason",
    "RemoveFaultReducer",
    "SemanticFault",
    "SetWorldValueReducer",
    "ShrinkReport",
    "TestCase",
    "TraceEvent",
    "TrialResult",
    "TrialRunner",
    "WorldCollectionReducer",
    "__version__",
    "at_most_one_effect",
    "case_digest",
    "contract",
    "evaluate_contracts",
    "events_must_precede",
    "exactly_one_effect",
    "export_schemas",
    "extract_failure_signature",
    "forbid_field_reads",
    "load_result",
    "no_effects_after_cancellation",
    "records_must_link",
    "requires_authorization_for_writes",
    "unique_business_key",
    "verify_bundle",
]


def __getattr__(name: str) -> object:
    try:
        module_name, attribute_name = _EXPORTS[name]
    except KeyError as exc:
        raise AttributeError(f"module {__name__!r} has no attribute {name!r}") from exc
    value: object = getattr(import_module(module_name, __name__), attribute_name)
    globals()[name] = value
    return value


def __dir__() -> list[str]:
    return sorted({*globals(), *__all__})
