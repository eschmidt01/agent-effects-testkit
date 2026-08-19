"""Guarded, API-key-free starter project generation."""

from __future__ import annotations

from pathlib import Path, PurePosixPath
from textwrap import dedent


class ScaffoldError(ValueError):
    """Raised when project generation would be unsafe or destructive."""


NORMAL_TEMPLATE: dict[str, str] = {
    "README.md": dedent(
        """\
        # Agent Effects starter

        This passing example wraps a callable agent, snapshots an in-memory world,
        and checks that exactly one business effect exists.

        ```bash
        pytest -q
        ```

        Adapt `world.py` to reset and snapshot your test system, then replace the
        callable in `agent.py` with your existing agent entry point.
        """
    ),
    "pyproject.toml": dedent(
        """\
        [project]
        name = "agent-effects-starter"
        version = "0.0.0"
        requires-python = ">=3.11"
        dependencies = ["agent-effects-testkit>=0.1.0a1"]

        [tool.pytest.ini_options]
        testpaths = ["tests"]
        pythonpath = ["."]
        """
    ),
    "agent.py": dedent(
        """\
        from agent_effects import AgentRun, TestCase

        from world import StarterWorld


        async def run_agent(case: TestCase, world: StarterWorld) -> AgentRun:
            world.state["effects"].append({"business_key": case.goal["business_key"]})
            return AgentRun(status="completed", output="effect created")
        """
    ),
    "world.py": dedent(
        """\
        from copy import deepcopy

        from agent_effects import BaseWorld, TestCase
        from agent_effects.models import JsonObject


        class StarterWorld(BaseWorld):
            def __init__(self, case: TestCase) -> None:
                super().__init__(case)
                self.state: JsonObject = deepcopy(case.world)

            def snapshot(self) -> JsonObject:
                return deepcopy(self.state)
        """
    ),
    "tests/test_agent_effects.py": dedent(
        """\
        import asyncio

        from agent import run_agent
        from agent_effects import CallableAgentAdapter, TestCase, TrialRunner, exactly_one_effect
        from world import StarterWorld


        def test_agent_creates_one_effect() -> None:
            case = TestCase(
                id="starter-effect",
                goal={"business_key": "order-001"},
                world={"effects": []},
            )
            result = asyncio.run(
                TrialRunner().run(
                    case=case,
                    world_factory=StarterWorld,
                    agent=CallableAgentAdapter("starter-agent", run_agent),
                    contracts=(exactly_one_effect("effects"),),
                    write_failure=False,
                )
            )
            assert result.passed, result.contracts.violations
        """
    ),
}


LOST_ACK_TEMPLATE: dict[str, str] = {
    "README.md": dedent(
        """\
        # Lost-acknowledgment demo

        This deterministic demo injects `timeout_after_commit`. The refund commits,
        its acknowledgment is lost, and a naive retry with a new idempotency key
        creates a duplicate. Contracts detect the duplicate and the test emits an
        integrity-checked, reproducible failure bundle.

        ```bash
        pytest -q
        agent-effects bundle verify .agent-effects/failures/<bundle>
        agent-effects bundle inspect .agent-effects/failures/<bundle>
        agent-effects reproduce --dry-run .agent-effects/failures/<bundle>
        agent-effects reproduce .agent-effects/failures/<bundle>
        ```

        `verify` and `inspect` never execute code. `reproduce` executes the installed
        registered refund reproducer. Unsigned hashes verify integrity relative to
        the manifest; they do not authenticate the author or provenance.

        To fix the bug, change `STABLE_IDEMPOTENCY = False` to `True` in `policy.py`,
        then rerun `pytest -q`. The stable idempotency key makes the retry return the
        first committed refund, so the contract passes.
        """
    ),
    "pyproject.toml": dedent(
        """\
        [project]
        name = "agent-effects-lost-ack-demo"
        version = "0.0.0"
        requires-python = ">=3.11"
        dependencies = ["agent-effects-testkit>=0.1.0a1"]

        [tool.pytest.ini_options]
        testpaths = ["tests"]
        pythonpath = ["."]
        """
    ),
    "policy.py": "STABLE_IDEMPOTENCY = False\n",
    "tests/test_lost_ack.py": dedent(
        """\
        import asyncio
        from pathlib import Path

        from agent_effects import (
            FailureStore,
            HierarchicalShrinker,
            ListDDMinReducer,
            TrialRunner,
            extract_failure_signature,
        )
        from agent_effects.examples.refund import (
            AGENTS,
            REFUND_CONTRACTS,
            RefundWorld,
            is_valid_refund_case,
            make_refund_case,
        )
        from policy import STABLE_IDEMPOTENCY


        def test_lost_acknowledgment_is_safe() -> None:
            async def scenario() -> tuple[object, Path | None]:
                case = make_refund_case(noise_records=12)
                agent_name = "idempotent" if STABLE_IDEMPOTENCY else "naive"
                runner = TrialRunner()
                result = await runner.run(
                    case=case,
                    world_factory=RefundWorld,
                    agent=AGENTS[agent_name],
                    contracts=REFUND_CONTRACTS,
                    write_failure=False,
                    reproducer_id=f"agent-effects.examples.refund/{agent_name}/v1",
                )
                if result.passed:
                    return result, None
                target = extract_failure_signature(result)

                async def evaluate(candidate):
                    return await runner.run(
                        case=candidate,
                        world_factory=RefundWorld,
                        agent=AGENTS[agent_name],
                        contracts=REFUND_CONTRACTS,
                        write_failure=False,
                    )

                reduction = await HierarchicalShrinker().shrink(
                    case=case,
                    target_signature=target,
                    evaluate=evaluate,
                    reducers=(ListDDMinReducer(("noise",)),),
                    is_valid=is_valid_refund_case,
                )
                path = FailureStore(Path(".agent-effects/failures")).write(
                    result,
                    shrink=reduction,
                )
                return result, path

            result, bundle = asyncio.run(scenario())
            assert result.passed, (
                "duplicate effect detected after timeout_after_commit; "
                f"integrity-checked failure bundle: {bundle}. "
                "Set STABLE_IDEMPOTENCY = True in policy.py to fix the retry."
            )
        """
    ),
}

TEMPLATES: dict[str, dict[str, str]] = {
    "starter": NORMAL_TEMPLATE,
    "lost-ack": LOST_ACK_TEMPLATE,
}


def _target_path(destination: Path, relative: str) -> Path:
    portable = PurePosixPath(relative)
    if portable.is_absolute() or ".." in portable.parts or relative != portable.as_posix():
        raise ScaffoldError(f"template path is not a safe relative path: {relative!r}")
    target = destination.joinpath(*portable.parts)
    try:
        target.resolve().relative_to(destination.resolve())
    except ValueError as exc:
        raise ScaffoldError(f"template path escapes destination: {relative!r}") from exc
    return target


def generate_project(
    destination: Path,
    *,
    template: str = "starter",
    force: bool = False,
) -> tuple[Path, ...]:
    """Generate a guarded project skeleton and return the written files."""

    try:
        files = TEMPLATES[template]
    except KeyError as exc:
        raise ScaffoldError(
            f"unknown template {template!r}; choose from {sorted(TEMPLATES)}"
        ) from exc
    if destination.is_symlink():
        raise ScaffoldError("destination may not be a symbolic link")
    targets = tuple(_target_path(destination, relative) for relative in sorted(files))
    conflicts = [path for path in targets if path.exists()]
    if conflicts and not force:
        displayed = ", ".join(path.relative_to(destination).as_posix() for path in conflicts)
        raise ScaffoldError(
            "rerun with --force to replace files owned by the selected template; "
            f"refusing to overwrite existing files: {displayed}"
        )
    destination.mkdir(parents=True, exist_ok=True)
    written: list[Path] = []
    for relative, target in zip(sorted(files), targets, strict=True):
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(files[relative], encoding="utf-8")
        written.append(target)
    return tuple(written)
