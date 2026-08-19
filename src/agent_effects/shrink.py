"""Composable, validity-preserving counterexample shrinking."""

from __future__ import annotations

import json
import math
import time
from collections.abc import Awaitable, Callable, Iterable, Sequence
from copy import deepcopy
from dataclasses import dataclass
from typing import Any, TypeAlias, cast

from .models import (
    FailureSignature,
    JsonValue,
    ReductionGuarantee,
    ReductionObservation,
    ReductionReport,
    ReductionStep,
    ReductionStopReason,
    ShrinkReport,
    ShrinkStep,
    TestCase,
    TrialResult,
    json_size,
)
from .protocols import (
    CaseReducer,
    CaseValidator,
    FailurePredicate,
    Reducer,
    ReductionCandidate,
)
from .signatures import SignatureExtractor, case_digest, extract_failure_signature

JsonPath = tuple[str | int, ...]
Evaluation: TypeAlias = Callable[[TestCase], Awaitable[TrialResult]]
Clock: TypeAlias = Callable[[], float]
ArgumentReductionHook: TypeAlias = Callable[[TestCase], Iterable[ReductionCandidate]]


def _replace_path(root: JsonValue, path: JsonPath, value: JsonValue) -> JsonValue:
    if not path:
        return value
    clone = deepcopy(root)
    cursor: Any = clone
    for segment in path[:-1]:
        cursor = cursor[segment]
    cursor[path[-1]] = value
    return clone


def _read_path(root: JsonValue, path: JsonPath) -> JsonValue:
    cursor: Any = root
    for segment in path:
        cursor = cursor[segment]
    return cast(JsonValue, cursor)


@dataclass(frozen=True, slots=True)
class RemoveFaultReducer:
    name: str = "remove_fault"

    def candidates(self, case: TestCase) -> Iterable[TestCase]:
        for index in range(len(case.faults)):
            yield case.model_copy(
                update={
                    "faults": (
                        *case.faults[:index],
                        *case.faults[index + 1 :],
                    )
                }
            )


@dataclass(frozen=True, slots=True)
class ReduceWorldListReducer:
    path: JsonPath
    name: str = "reduce_world_list"

    def candidates(self, case: TestCase) -> Iterable[TestCase]:
        current = _read_path(case.world, self.path)
        if not isinstance(current, list):
            raise TypeError(f"world path {self.path!r} is not a list")
        if current:
            world = _replace_path(case.world, self.path, [])
            assert isinstance(world, dict)
            yield case.model_copy(update={"world": world})
        for index in range(len(current)):
            reduced = [*current[:index], *current[index + 1 :]]
            world = _replace_path(case.world, self.path, reduced)
            assert isinstance(world, dict)
            yield case.model_copy(update={"world": world})


@dataclass(frozen=True, slots=True)
class SetWorldValueReducer:
    path: JsonPath
    values: tuple[JsonValue, ...]
    name: str = "set_world_value"

    def candidates(self, case: TestCase) -> Iterable[TestCase]:
        current = _read_path(case.world, self.path)
        for value in self.values:
            if value == current:
                continue
            world = _replace_path(case.world, self.path, value)
            assert isinstance(world, dict)
            yield case.model_copy(update={"world": world})


def _validated_update(case: TestCase, **updates: object) -> TestCase | None:
    payload = case.model_dump(mode="json")
    payload.update(updates)
    try:
        return TestCase.model_validate(payload)
    except ValueError:
        return None


def _ddmin_removals(length: int) -> Iterable[tuple[int, ...]]:
    """Yield deterministic partitions before the final one-at-a-time pass."""

    seen: set[tuple[int, ...]] = set()
    partitions = 2
    while length > 1 and partitions <= length:
        width = math.ceil(length / partitions)
        for start in range(0, length, width):
            removal = tuple(range(start, min(length, start + width)))
            if removal and removal not in seen:
                seen.add(removal)
                yield removal
        if partitions == length:
            break
        partitions = min(length, partitions * 2)
    for index in range(length):
        removal = (index,)
        if removal not in seen:
            yield removal


def _case_size(case: TestCase) -> int:
    """Return a deterministic metric that also rewards smaller occurrences."""

    encoded = json.dumps(
        case.model_dump(mode="json"),
        sort_keys=True,
        separators=(",", ":"),
    ).encode()
    return len(encoded) + sum(rule.occurrence for rule in case.faults)


@dataclass(frozen=True, slots=True)
class WorldCollectionReducer:
    """Remove top-level world collections using ddmin partitions."""

    protected: tuple[str, ...] = ()
    name: str = "world_collections_ddmin"

    def candidates(self, case: TestCase) -> Iterable[ReductionCandidate]:
        keys = tuple(sorted(key for key in case.world if key not in self.protected))
        for indices in _ddmin_removals(len(keys)):
            removed = tuple(keys[index] for index in indices)
            world = {key: value for key, value in case.world.items() if key not in removed}
            candidate = _validated_update(case, world=world)
            if candidate is not None:
                yield ReductionCandidate(
                    case=candidate,
                    explanation=f"removed world collections {removed!r}",
                )


@dataclass(frozen=True, slots=True)
class ListDDMinReducer:
    """Partition-reduce a list at a configured world path."""

    path: JsonPath
    name: str = "world_list_ddmin"

    def candidates(self, case: TestCase) -> Iterable[ReductionCandidate]:
        current = _read_path(case.world, self.path)
        if not isinstance(current, list):
            return
        for indices in _ddmin_removals(len(current)):
            removed = set(indices)
            reduced = [item for index, item in enumerate(current) if index not in removed]
            world = _replace_path(case.world, self.path, reduced)
            if isinstance(world, dict):
                candidate = _validated_update(case, world=world)
                if candidate is not None:
                    yield ReductionCandidate(
                        case=candidate,
                        explanation=f"removed list indices {indices!r} at world{self.path!r}",
                    )


@dataclass(frozen=True, slots=True)
class MappingKeyReducer:
    """Remove deterministic partitions of keys from a world mapping."""

    path: JsonPath
    protected: tuple[str, ...] = ()
    name: str = "world_mapping_keys_ddmin"

    def candidates(self, case: TestCase) -> Iterable[ReductionCandidate]:
        current = _read_path(case.world, self.path)
        if not isinstance(current, dict):
            return
        keys = tuple(sorted(key for key in current if key not in self.protected))
        for indices in _ddmin_removals(len(keys)):
            removed = tuple(keys[index] for index in indices)
            reduced = {key: value for key, value in current.items() if key not in removed}
            world = _replace_path(case.world, self.path, reduced)
            if isinstance(world, dict):
                candidate = _validated_update(case, world=world)
                if candidate is not None:
                    yield ReductionCandidate(
                        case=candidate,
                        explanation=f"removed mapping keys {removed!r} at world{self.path!r}",
                    )


@dataclass(frozen=True, slots=True)
class FaultScheduleReducer:
    """Remove unrelated fault rules using ddmin partitions."""

    name: str = "fault_schedule_ddmin"

    def candidates(self, case: TestCase) -> Iterable[ReductionCandidate]:
        for indices in _ddmin_removals(len(case.faults)):
            removed = set(indices)
            faults = tuple(rule for index, rule in enumerate(case.faults) if index not in removed)
            candidate = _validated_update(
                case,
                faults=[item.model_dump(mode="json") for item in faults],
            )
            if candidate is not None:
                yield ReductionCandidate(
                    case=candidate,
                    explanation=f"removed fault indices {indices!r}",
                )


@dataclass(frozen=True, slots=True)
class FaultOccurrenceReducer:
    """Move fault occurrences deterministically toward the first call."""

    name: str = "fault_occurrence"

    def candidates(self, case: TestCase) -> Iterable[ReductionCandidate]:
        for index, rule in enumerate(case.faults):
            values: list[int] = []
            value = 1
            while value < rule.occurrence:
                values.append(value)
                value *= 2
            for occurrence in values:
                faults = list(case.faults)
                faults[index] = rule.model_copy(update={"occurrence": occurrence})
                candidate = _validated_update(
                    case,
                    faults=[item.model_dump(mode="json") for item in faults],
                )
                if candidate is not None:
                    yield ReductionCandidate(
                        case=candidate,
                        explanation=(
                            f"reduced fault {rule.operation!r} occurrence "
                            f"from {rule.occurrence} to {occurrence}"
                        ),
                    )


@dataclass(frozen=True, slots=True)
class ActorAttributeReducer:
    """Remove optional actor attributes in stable key order."""

    required: tuple[str, ...] = ()
    name: str = "optional_actor_attributes"

    def candidates(self, case: TestCase) -> Iterable[ReductionCandidate]:
        keys = tuple(sorted(key for key in case.actor if key not in self.required))
        for indices in _ddmin_removals(len(keys)):
            removed = tuple(keys[index] for index in indices)
            actor = {key: value for key, value in case.actor.items() if key not in removed}
            candidate = _validated_update(case, actor=actor)
            if candidate is not None:
                yield ReductionCandidate(
                    case=candidate,
                    explanation=f"removed optional actor attributes {removed!r}",
                )


@dataclass(frozen=True, slots=True)
class GoalFieldReducer:
    """Remove optional goal fields in stable key order."""

    required: tuple[str, ...] = ()
    name: str = "optional_goal_fields"

    def candidates(self, case: TestCase) -> Iterable[ReductionCandidate]:
        keys = tuple(sorted(key for key in case.goal if key not in self.required))
        for indices in _ddmin_removals(len(keys)):
            removed = tuple(keys[index] for index in indices)
            goal = {key: value for key, value in case.goal.items() if key not in removed}
            candidate = _validated_update(case, goal=goal)
            if candidate is not None:
                yield ReductionCandidate(
                    case=candidate,
                    explanation=f"removed optional goal fields {removed!r}",
                )


@dataclass(frozen=True, slots=True)
class ArgumentReducer:
    """Delegate domain-specific operation argument simplification to a hook."""

    stable_name: str
    hook: ArgumentReductionHook

    @property
    def name(self) -> str:
        return f"operation_arguments:{self.stable_name}"

    def candidates(self, case: TestCase) -> Iterable[ReductionCandidate]:
        return self.hook(case)


class HierarchicalShrinker:
    """Sequential, signature-preserving hierarchical delta debugger."""

    def __init__(
        self,
        *,
        max_evaluations: int = 250,
        max_elapsed_ms: float | None = None,
        confirm_signature_runs: int = 1,
        clock: Clock = time.perf_counter,
    ) -> None:
        if max_evaluations < 1:
            raise ValueError("max_evaluations must be positive")
        if max_elapsed_ms is not None and max_elapsed_ms <= 0:
            raise ValueError("max_elapsed_ms must be positive when provided")
        if confirm_signature_runs < 1:
            raise ValueError("confirm_signature_runs must be positive")
        self.max_evaluations = max_evaluations
        self.max_elapsed_ms = max_elapsed_ms
        self.confirm_signature_runs = confirm_signature_runs
        self._clock = clock

    async def shrink(
        self,
        *,
        case: TestCase,
        target_signature: FailureSignature,
        evaluate: Evaluation,
        reducers: Sequence[Reducer],
        is_valid: CaseValidator,
        validity_predicate_id: str | None = None,
        signature_extractor: SignatureExtractor = extract_failure_signature,
    ) -> ReductionReport:
        """Reduce ``case`` while reproducing exactly ``target_signature``."""

        if validity_predicate_id is not None and not validity_predicate_id.strip():
            raise ValueError("validity_predicate_id must not be empty")

        started = self._clock()
        observations: list[ReductionObservation] = []
        steps: list[ReductionStep] = []
        cache: dict[str, FailureSignature | None] = {}
        candidate_evaluations = 0
        cache_hits = 0
        invalid_candidates = 0
        different_failures = 0
        current = case
        stop_reason = ReductionStopReason.LOCALLY_MINIMAL
        guarantee = ReductionGuarantee.LOCALLY_MINIMAL_UNDER_CONFIGURED_REDUCERS
        evaluation_budget_exhausted = False
        time_budget_exhausted = False
        predicate_name = validity_predicate_id or (
            f"{getattr(is_valid, '__module__', '<unknown>')}."
            f"{getattr(is_valid, '__qualname__', type(is_valid).__qualname__)}"
        )
        diagnostic = (
            "No smaller valid same-signature candidate was found by the configured "
            "reducers within the configured budgets. This is a local guarantee over "
            "generated candidates, not a claim of global minimality."
        )

        def elapsed_ms() -> float:
            return max(0.0, (self._clock() - started) * 1000)

        def report() -> ReductionReport:
            return ReductionReport(
                original=case,
                minimized=current,
                initial_case_digest=case_digest(case),
                final_case_digest=case_digest(current),
                initial_size=_case_size(case),
                final_size=_case_size(current),
                target_signature=target_signature,
                reducers_used=tuple(item.name for item in reducers),
                validity_predicate=predicate_name,
                baseline_observations=tuple(observations),
                candidate_evaluations=candidate_evaluations,
                cache_hits=cache_hits,
                invalid_candidates_skipped=invalid_candidates,
                different_failures=different_failures,
                accepted_reductions=tuple(steps),
                elapsed_ms=elapsed_ms(),
                evaluation_budget=self.max_evaluations,
                time_budget_ms=self.max_elapsed_ms,
                evaluation_budget_exhausted=evaluation_budget_exhausted,
                time_budget_exhausted=time_budget_exhausted,
                confirm_signature_runs=self.confirm_signature_runs,
                stop_reason=stop_reason,
                guarantee=guarantee,
                diagnostic=diagnostic,
            )

        try:
            baseline_valid = is_valid(case)
        except Exception as exc:
            baseline_valid = False
            diagnostic = (
                "The world validity predicate raised "
                f"{type(exc).__name__}. Fix the predicate before shrinking."
            )
        if not baseline_valid:
            stop_reason = ReductionStopReason.INVALID_BASELINE
            guarantee = ReductionGuarantee.NO_MINIMALITY_CLAIM
            if not diagnostic.startswith("The world validity predicate raised"):
                diagnostic = (
                    "The world validity predicate rejected the original case; "
                    "fix the fixture or predicate before shrinking."
                )
            return report()

        for _ in range(self.confirm_signature_runs):
            try:
                baseline = await evaluate(case)
            except Exception as exc:
                stop_reason = ReductionStopReason.BASELINE_DID_NOT_REPRODUCE
                guarantee = ReductionGuarantee.NO_MINIMALITY_CLAIM
                diagnostic = (
                    "The baseline evaluator raised outside the structured runner: "
                    f"{type(exc).__name__}. Return a TrialResult for lifecycle failures."
                )
                return report()
            signature = signature_extractor(baseline)
            observations.append(ReductionObservation(signature=signature, trace=baseline.events))

        observed = {item.signature for item in observations}
        if len(observed) != 1:
            stop_reason = ReductionStopReason.UNSTABLE_BASELINE
            guarantee = ReductionGuarantee.NO_MINIMALITY_CLAIM
            diagnostic = (
                "Baseline runs produced inconsistent failure signatures; no minimality "
                "claim is made. Increase confirm_signature_runs or make "
                "the agent and world deterministic."
            )
            return report()
        observed_signature = observations[0].signature
        if observed_signature != target_signature:
            stop_reason = ReductionStopReason.BASELINE_DID_NOT_REPRODUCE
            guarantee = ReductionGuarantee.NO_MINIMALITY_CLAIM
            diagnostic = (
                "The original case no longer reproduces the requested failure signature; "
                "refresh the target result before shrinking."
            )
            return report()
        cache[case_digest(case)] = observed_signature

        budget_exhausted = False
        changed = True
        while changed and not budget_exhausted:
            changed = False
            for reducer in reducers:
                accepted = True
                while accepted and not budget_exhausted:
                    accepted = False
                    before_size = _case_size(current)
                    before_digest = case_digest(current)
                    for reduction in reducer.candidates(current):
                        if self.max_elapsed_ms is not None and elapsed_ms() >= self.max_elapsed_ms:
                            stop_reason = ReductionStopReason.TIME_BUDGET_EXHAUSTED
                            guarantee = ReductionGuarantee.BUDGET_LIMITED_REDUCTION
                            time_budget_exhausted = True
                            diagnostic = (
                                "The shrink time budget was exhausted; increase "
                                "max_elapsed_ms to continue reduction. No local-minimality "
                                "claim is made for this result."
                            )
                            budget_exhausted = True
                            break
                        candidate = reduction.case
                        after_size = _case_size(candidate)
                        if candidate == current or after_size >= before_size:
                            continue
                        try:
                            candidate_valid = is_valid(candidate)
                        except Exception:
                            candidate_valid = False
                        if not candidate_valid:
                            invalid_candidates += 1
                            continue
                        digest = case_digest(candidate)
                        if digest in cache:
                            cache_hits += 1
                            candidate_signature = cache[digest]
                        else:
                            if candidate_evaluations >= self.max_evaluations:
                                stop_reason = ReductionStopReason.EVALUATION_BUDGET_EXHAUSTED
                                guarantee = ReductionGuarantee.BUDGET_LIMITED_REDUCTION
                                evaluation_budget_exhausted = True
                                diagnostic = (
                                    "The shrink evaluation budget was exhausted; increase "
                                    "max_evaluations to continue reduction. No local-minimality "
                                    "claim is made for this result."
                                )
                                budget_exhausted = True
                                break
                            candidate_evaluations += 1
                            try:
                                outcome = await evaluate(candidate)
                                candidate_signature = signature_extractor(outcome)
                            except Exception:
                                candidate_signature = None
                            cache[digest] = candidate_signature
                        if candidate_signature != target_signature:
                            different_failures += 1
                            continue
                        steps.append(
                            ReductionStep(
                                reducer=reducer.name,
                                explanation=reduction.explanation,
                                before_digest=before_digest,
                                after_digest=digest,
                                before_size=before_size,
                                after_size=after_size,
                            )
                        )
                        current = candidate
                        changed = True
                        accepted = True
                        break
                if budget_exhausted:
                    break

        return report()


class GreedyShrinker:
    """Small, predictable alpha shrinker.

    It accepts a candidate only when the caller-provided failure predicate still
    holds. Domain adapters also provide a validity predicate so simplification
    never creates impossible relational worlds.
    """

    def __init__(self, *, max_evaluations: int = 250) -> None:
        if max_evaluations < 1:
            raise ValueError("max_evaluations must be positive")
        self.max_evaluations = max_evaluations

    async def shrink(
        self,
        *,
        case: TestCase,
        target_signature: Sequence[str],
        still_fails: FailurePredicate,
        reducers: Sequence[CaseReducer],
        is_valid: CaseValidator = lambda _: True,
    ) -> ShrinkReport:
        evaluations = 0
        steps: list[ShrinkStep] = []
        current = case

        if not is_valid(current):
            raise ValueError("initial case is invalid")
        evaluations += 1
        if not await still_fails(current):
            raise ValueError("initial case does not satisfy the target failure predicate")

        changed = True
        while changed and evaluations < self.max_evaluations:
            changed = False
            before_size = json_size(current)
            for reducer in reducers:
                for candidate in reducer.candidates(current):
                    if evaluations >= self.max_evaluations:
                        break
                    after_size = json_size(candidate)
                    if candidate == current or after_size >= before_size or not is_valid(candidate):
                        continue
                    evaluations += 1
                    if await still_fails(candidate):
                        steps.append(
                            ShrinkStep(
                                reducer=reducer.name,
                                before_size=before_size,
                                after_size=after_size,
                            )
                        )
                        current = candidate
                        changed = True
                        break
                if changed or evaluations >= self.max_evaluations:
                    break

        return ShrinkReport(
            original=case,
            minimized=current,
            target_signature=tuple(target_signature),
            evaluations=evaluations,
            accepted_steps=tuple(steps),
        )
