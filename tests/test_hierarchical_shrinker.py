from __future__ import annotations

import asyncio
from collections.abc import Iterable
from dataclasses import dataclass

from agent_effects.examples.refund import (
    AGENTS,
    REFUND_CONTRACTS,
    RefundWorld,
    is_valid_refund_case,
    make_refund_case,
)
from agent_effects.models import (
    AdapterInfo,
    AgentRun,
    ContractReport,
    ContractViolation,
    FailureCategory,
    FailureSignature,
    FailureStage,
    FaultMode,
    FaultRule,
    LifecycleFailure,
    ReductionGuarantee,
    ReductionReport,
    ReductionStopReason,
    TestCase,
    TrialResult,
)
from agent_effects.protocols import ReductionCandidate
from agent_effects.runner import TrialRunner
from agent_effects.shrink import (
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
    WorldCollectionReducer,
)
from agent_effects.signatures import extract_failure_signature


def _result(
    case: TestCase,
    *,
    contract: str = "target",
    code: str = "duplicate",
    lifecycle: LifecycleFailure | None = None,
) -> TrialResult:
    violation = ContractViolation(code=code, message="diagnostic", contract=contract)
    return TrialResult(
        case=case,
        agent_name="test",
        adapter=AdapterInfo(name="test"),
        initial_state={},
        final_state={},
        events=(),
        agent_run=AgentRun(status="completed"),
        contracts=ContractReport(passed=False, violations=(violation,)),
        lifecycle_failures=(lifecycle,) if lifecycle is not None else (),
        elapsed_ms=0,
    )


def test_ddmin_succeeds_where_one_by_one_greedy_cannot() -> None:
    case = TestCase(id="ddmin", world={"items": ["a", "b", "c", "d"]})
    target = extract_failure_signature(_result(case))

    async def evaluate(candidate: TestCase) -> TrialResult:
        items = candidate.world["items"]
        if items in (["a", "b", "c", "d"], ["c", "d"]):
            return _result(candidate)
        return _result(candidate, contract="other", code="other_failure")

    async def scenario() -> None:
        async def still_matches(candidate: TestCase) -> bool:
            return extract_failure_signature(await evaluate(candidate)) == target

        greedy = await GreedyShrinker().shrink(
            case=case,
            target_signature=("duplicate",),
            still_fails=still_matches,
            reducers=(ReduceWorldListReducer(("items",)),),
        )
        report = await HierarchicalShrinker().shrink(
            case=case,
            target_signature=target,
            evaluate=evaluate,
            reducers=(ListDDMinReducer(("items",)),),
            is_valid=lambda _: True,
        )
        assert greedy.minimized == case
        assert report.minimized.world["items"] == ["c", "d"]
        assert report.accepted_reductions[0].explanation.startswith("removed list indices")

    asyncio.run(scenario())


@dataclass(frozen=True, slots=True)
class _DuplicateReducer:
    name: str = "duplicates"

    def candidates(self, case: TestCase) -> Iterable[ReductionCandidate]:
        candidate = case.model_copy(update={"metadata": {}})
        yield ReductionCandidate(candidate, "first")
        yield ReductionCandidate(candidate, "second")


def test_cache_reuse_and_deterministic_output() -> None:
    case = TestCase(id="cache", metadata={"noise": "x"})
    target = extract_failure_signature(_result(case))

    async def evaluate(candidate: TestCase) -> TrialResult:
        if candidate.metadata:
            return _result(candidate)
        return _result(candidate, contract="different", code="different")

    async def run_once() -> ReductionReport:
        return await HierarchicalShrinker().shrink(
            case=case,
            target_signature=target,
            evaluate=evaluate,
            reducers=(_DuplicateReducer(),),
            is_valid=lambda _: True,
        )

    first = asyncio.run(run_once())
    second = asyncio.run(run_once())
    assert first.minimized == second.minimized == case
    assert first.cache_hits >= 1
    assert first.model_dump(exclude={"elapsed_ms"}) == second.model_dump(exclude={"elapsed_ms"})

    legacy_payload = first.model_dump(mode="json")
    for field in (
        "validity_predicate",
        "evaluation_budget_exhausted",
        "time_budget_exhausted",
        "guarantee",
    ):
        legacy_payload.pop(field)
    legacy_payload["stop_reason"] = "minimal"
    legacy = ReductionReport.model_validate(legacy_payload)
    assert legacy.stop_reason is ReductionStopReason.LEGACY_MINIMAL
    assert legacy.guarantee is ReductionGuarantee.NO_MINIMALITY_CLAIM


def test_invalid_and_different_failure_candidates_are_rejected() -> None:
    case = TestCase(id="validity", world={"items": [1, 2, 3, 4]})
    target = extract_failure_signature(_result(case))

    async def evaluate(candidate: TestCase) -> TrialResult:
        items = candidate.world["items"]
        if items == [1, 2, 3, 4]:
            return _result(candidate)
        if items == [2, 3, 4]:
            lifecycle = LifecycleFailure(
                stage=FailureStage.WORLD_CREATION,
                category=FailureCategory.INFRASTRUCTURE,
                exception_type="ValueError",
                message="dynamic details are excluded",
                primary=True,
            )
            return _result(candidate, lifecycle=lifecycle)
        return _result(candidate, contract="different", code="different")

    def has_three_items(candidate: TestCase) -> bool:
        items = candidate.world.get("items")
        return isinstance(items, list) and len(items) >= 3

    report = asyncio.run(
        HierarchicalShrinker().shrink(
            case=case,
            target_signature=target,
            evaluate=evaluate,
            reducers=(ListDDMinReducer(("items",)),),
            is_valid=has_three_items,
        )
    )
    assert report.minimized == case
    assert report.invalid_candidates_skipped > 0
    assert report.different_failures > 0


def test_fault_actor_goal_and_custom_argument_reducers() -> None:
    case = TestCase(
        id="structured",
        actor={"id": "actor", "nickname": "noise"},
        goal={"operation": "pay", "amount": 100, "note": "noise"},
        faults=(
            FaultRule(
                operation="pay",
                mode=FaultMode.TIMEOUT_AFTER_COMMIT,
                occurrence=4,
            ),
        ),
    )
    target = extract_failure_signature(_result(case))

    def arguments(candidate: TestCase) -> Iterable[ReductionCandidate]:
        if candidate.goal.get("amount") == 100:
            goal = dict(candidate.goal)
            goal["amount"] = 1
            yield ReductionCandidate(
                candidate.model_copy(update={"goal": goal}),
                "reduced payment amount to one",
            )

    async def evaluate(candidate: TestCase) -> TrialResult:
        return _result(candidate)

    report = asyncio.run(
        HierarchicalShrinker().shrink(
            case=case,
            target_signature=target,
            evaluate=evaluate,
            reducers=(
                FaultOccurrenceReducer(),
                ActorAttributeReducer(required=("id",)),
                GoalFieldReducer(required=("operation", "amount")),
                ArgumentReducer("payment_amount", arguments),
            ),
            is_valid=lambda _: True,
        )
    )
    assert report.minimized.faults[0].occurrence == 1
    assert report.minimized.actor == {"id": "actor"}
    assert report.minimized.goal == {"operation": "pay", "amount": 1}
    assert {step.reducer for step in report.accepted_reductions} >= {
        "fault_occurrence",
        "optional_actor_attributes",
        "optional_goal_fields",
        "operation_arguments:payment_amount",
    }


def test_evaluation_and_injected_time_budgets_stop_structurally() -> None:
    case = TestCase(id="budgets", world={"items": [1, 2, 3, 4]})
    target = extract_failure_signature(_result(case))

    async def different(candidate: TestCase) -> TrialResult:
        if candidate == case:
            return _result(candidate)
        return _result(candidate, contract="other", code="other")

    evaluation_report = asyncio.run(
        HierarchicalShrinker(max_evaluations=1).shrink(
            case=case,
            target_signature=target,
            evaluate=different,
            reducers=(ListDDMinReducer(("items",)),),
            is_valid=lambda _: True,
        )
    )
    assert evaluation_report.stop_reason is ReductionStopReason.EVALUATION_BUDGET_EXHAUSTED
    assert evaluation_report.evaluation_budget_exhausted
    assert evaluation_report.guarantee is ReductionGuarantee.BUDGET_LIMITED_REDUCTION
    assert "max_evaluations" in evaluation_report.diagnostic

    ticks = iter((0.0, 0.0, 0.010, 0.011, 0.012))
    time_report = asyncio.run(
        HierarchicalShrinker(max_elapsed_ms=1, clock=lambda: next(ticks)).shrink(
            case=case,
            target_signature=target,
            evaluate=different,
            reducers=(ListDDMinReducer(("items",)),),
            is_valid=lambda _: True,
        )
    )
    assert time_report.stop_reason is ReductionStopReason.TIME_BUDGET_EXHAUSTED
    assert time_report.time_budget_exhausted
    assert "max_elapsed_ms" in time_report.diagnostic


def test_invalid_and_unstable_baselines_stop_without_minimality_claim() -> None:
    case = TestCase(id="baseline")
    target = extract_failure_signature(_result(case))

    async def stable(candidate: TestCase) -> TrialResult:
        return _result(candidate)

    invalid = asyncio.run(
        HierarchicalShrinker().shrink(
            case=case,
            target_signature=target,
            evaluate=stable,
            reducers=(),
            is_valid=lambda _: False,
        )
    )
    assert invalid.stop_reason is ReductionStopReason.INVALID_BASELINE
    assert invalid.minimized == case

    calls = 0

    async def unstable(candidate: TestCase) -> TrialResult:
        nonlocal calls
        calls += 1
        if calls % 2:
            return _result(candidate)
        return _result(candidate, contract="other", code="other")

    report = asyncio.run(
        HierarchicalShrinker(confirm_signature_runs=2).shrink(
            case=case,
            target_signature=target,
            evaluate=unstable,
            reducers=(),
            is_valid=lambda _: True,
        )
    )
    assert report.stop_reason is ReductionStopReason.UNSTABLE_BASELINE
    assert len(report.baseline_observations) == 2
    assert report.guarantee is ReductionGuarantee.NO_MINIMALITY_CLAIM
    assert "no minimality claim is made" in report.diagnostic


def test_naive_refund_signature_is_preserved_while_noise_is_removed() -> None:
    case = make_refund_case(
        noise_records=1_000,
        extra_faults=(FaultRule(operation="unused_lookup", mode=FaultMode.TIMEOUT_BEFORE),),
    )
    runner = TrialRunner()

    async def scenario() -> None:
        original = await runner.run(
            case=case,
            world_factory=RefundWorld,
            agent=AGENTS["naive"],
            contracts=REFUND_CONTRACTS,
            write_failure=False,
        )
        target = extract_failure_signature(original)

        async def evaluate(candidate: TestCase) -> TrialResult:
            return await runner.run(
                case=candidate,
                world_factory=RefundWorld,
                agent=AGENTS["naive"],
                contracts=REFUND_CONTRACTS,
                write_failure=False,
            )

        report = await HierarchicalShrinker().shrink(
            case=case,
            target_signature=target,
            evaluate=evaluate,
            reducers=(ListDDMinReducer(("noise",)), FaultScheduleReducer()),
            is_valid=is_valid_refund_case,
            validity_predicate_id="agent-effects.examples.refund/is_valid_refund_case/v1",
        )
        replay = await evaluate(report.minimized)
        assert report.minimized.world["noise"] == []
        assert report.minimized.faults == (
            FaultRule(operation="issue_refund", mode=FaultMode.TIMEOUT_AFTER_COMMIT),
        )
        assert report.candidate_evaluations < 80
        assert report.stop_reason is ReductionStopReason.LOCALLY_MINIMAL
        assert report.guarantee is (ReductionGuarantee.LOCALLY_MINIMAL_UNDER_CONFIGURED_REDUCERS)
        assert report.validity_predicate.endswith("/is_valid_refund_case/v1")
        assert extract_failure_signature(replay) == target

    asyncio.run(scenario())


def test_custom_failure_signature_extractor_is_supported() -> None:
    case = TestCase(id="custom-signature", world={"items": [1, 2]})
    target = FailureSignature(primary_category="custom", stable_error_code="stable-domain-code")

    async def evaluate(candidate: TestCase) -> TrialResult:
        return _result(candidate, contract="unstable-contract", code="unstable-code")

    def custom(_result_value: TrialResult) -> FailureSignature:
        return target

    report = asyncio.run(
        HierarchicalShrinker().shrink(
            case=case,
            target_signature=target,
            evaluate=evaluate,
            reducers=(ListDDMinReducer(("items",)),),
            is_valid=lambda _: True,
            signature_extractor=custom,
        )
    )
    assert report.minimized.world["items"] == []
    assert report.target_signature == target


def test_world_collection_and_mapping_reducers_preserve_source_immutability() -> None:
    case = TestCase(
        id="mapping-reducers",
        world={"required": {"keep": 1, "noise": 2}, "unrelated": [1]},
    )
    collection_candidates = list(WorldCollectionReducer(protected=("required",)).candidates(case))
    mapping_candidates = list(
        MappingKeyReducer(("required",), protected=("keep",)).candidates(case)
    )
    assert collection_candidates[-1].case.world == {"required": {"keep": 1, "noise": 2}}
    assert mapping_candidates[-1].case.world == {
        "required": {"keep": 1},
        "unrelated": [1],
    }
    assert case.world == {"required": {"keep": 1, "noise": 2}, "unrelated": [1]}
