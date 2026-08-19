"""Deterministic JSON Schema export for every public portable model."""

from __future__ import annotations

import json
from collections.abc import Callable
from pathlib import Path
from typing import TypeVar, cast

from pydantic import BaseModel, TypeAdapter

from .models import (
    AdapterInfo,
    AgentRun,
    ContractFailureIdentity,
    ContractReport,
    ContractViolation,
    FailureBundleManifest,
    FailureSignature,
    FaultRule,
    JsonObject,
    LifecycleFailure,
    ReductionGuarantee,
    ReductionReport,
    ShrinkReport,
    TestCase,
    TraceEvent,
    TrialResult,
)

SCHEMA_DIALECT = "https://json-schema.org/draft/2020-12/schema"
SCHEMA_VERSION = "v1alpha1"
SCHEMA_BASE = f"https://schemas.agent-effects.dev/{SCHEMA_VERSION}"

T = TypeVar("T")
SchemaFactory = Callable[[], JsonObject]


def _model_schema(model: type[BaseModel]) -> JsonObject:
    return cast(JsonObject, model.model_json_schema(ref_template="#/$defs/{model}"))


def _type_schema(adapter: TypeAdapter[T]) -> JsonObject:
    return cast(JsonObject, adapter.json_schema(ref_template="#/$defs/{model}"))


def _model(model: type[BaseModel]) -> SchemaFactory:
    return lambda: _model_schema(model)


SCHEMA_EXPORTS: dict[str, SchemaFactory] = {
    "actor": lambda: _type_schema(TypeAdapter(JsonObject)),
    "adapter-info": _model(AdapterInfo),
    "agent-run": _model(AgentRun),
    "contract-report": _model(ContractReport),
    "contract-failure-identity": _model(ContractFailureIdentity),
    "contract-violation": _model(ContractViolation),
    "failure-bundle-manifest": _model(FailureBundleManifest),
    "failure-signature": _model(FailureSignature),
    "fault-rule": _model(FaultRule),
    "fault-schedule": lambda: _type_schema(TypeAdapter(tuple[FaultRule, ...])),
    "goal": lambda: _type_schema(TypeAdapter(JsonObject)),
    "lifecycle-failure": _model(LifecycleFailure),
    "reduction-report": _model(ReductionReport),
    "reduction-guarantee": lambda: _type_schema(TypeAdapter(ReductionGuarantee)),
    "shrink-report": _model(ShrinkReport),
    "test-case": _model(TestCase),
    "trace": lambda: _type_schema(TypeAdapter(tuple[TraceEvent, ...])),
    "trace-event": _model(TraceEvent),
    "trial-result": _model(TrialResult),
    "world-snapshot": lambda: _type_schema(TypeAdapter(JsonObject | None)),
}


def exported_schema(name: str) -> JsonObject:
    """Build one normalized public schema by its stable export name."""

    try:
        payload = SCHEMA_EXPORTS[name]()
    except KeyError as exc:
        raise ValueError(f"unknown portable schema: {name}") from exc
    payload["$schema"] = SCHEMA_DIALECT
    payload["$id"] = f"{SCHEMA_BASE}/{name}.schema.json"
    payload["x-agent-effects-schema-version"] = SCHEMA_VERSION
    return payload


def schema_bytes(name: str) -> bytes:
    """Serialize one schema deterministically without machine-specific data."""

    return (json.dumps(exported_schema(name), indent=2, sort_keys=True) + "\n").encode()


def export_schemas(output: Path) -> tuple[Path, ...]:
    """Write every public schema and return paths in stable name order."""

    output.mkdir(parents=True, exist_ok=True)
    written: list[Path] = []
    for name in sorted(SCHEMA_EXPORTS):
        path = output / f"{name}.schema.json"
        path.write_bytes(schema_bytes(name))
        written.append(path)
    return tuple(written)
