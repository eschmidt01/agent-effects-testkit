"""Stable failure identities and canonical portable-case digests."""

from __future__ import annotations

import hashlib
import json
from collections import Counter
from collections.abc import Callable
from typing import TypeAlias

from .models import ContractFailureIdentity, FailureSignature, TestCase, TrialResult

SignatureExtractor: TypeAlias = Callable[[TrialResult], FailureSignature]


def extract_failure_signature(result: TrialResult) -> FailureSignature:
    """Derive a deterministic identity without messages or dynamic values.

    A primary lifecycle failure takes precedence over contract diagnostics that
    may have been added while preserving the structured runner result. Ordinary
    contract failures retain the multiplicity of each contract/code pair.
    """

    primary = result.primary_failure
    if primary is not None:
        stable_code = primary.details.get("error_code")
        return FailureSignature(
            primary_category=primary.category.value,
            primary_stage=primary.stage,
            exception_type=primary.exception_type,
            stable_error_code=stable_code if isinstance(stable_code, str) else None,
        )

    counts = Counter(
        (violation.contract, violation.code) for violation in result.contracts.violations
    )
    identities = tuple(
        ContractFailureIdentity(
            contract_id=contract_id,
            violation_code=violation_code,
            count=count,
        )
        for (contract_id, violation_code), count in sorted(counts.items())
    )
    return FailureSignature(
        primary_category=result.primary_failure_category or "none",
        contract_failures=identities,
    )


def case_digest(case: TestCase) -> str:
    """Return the full SHA-256 digest of a canonical portable case."""

    canonical = json.dumps(
        case.model_dump(mode="json"),
        sort_keys=True,
        separators=(",", ":"),
    ).encode()
    return hashlib.sha256(canonical).hexdigest()
