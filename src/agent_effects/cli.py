"""Command-line interface for demos and failure-bundle inspection."""

from __future__ import annotations

import asyncio
import json
import platform
import sys
from pathlib import Path
from typing import Annotated

import pydantic
import typer
from rich.console import Console
from rich.table import Table

from . import __version__
from .artifacts import (
    BundleVerificationError,
    FailureBundle,
    FailureStore,
    load_result,
)
from .examples.refund import (
    AGENTS,
    REFUND_CONTRACTS,
    RefundWorld,
    is_valid_refund_case,
    make_refund_case,
)
from .models import FaultMode, TestCase, TrialResult
from .runner import TrialRunner
from .schemas import export_schemas
from .shrink import FaultScheduleReducer, HierarchicalShrinker, ListDDMinReducer
from .signatures import extract_failure_signature

app = typer.Typer(
    no_args_is_help=True,
    help="Property-based transaction testing for tool-using AI agents.",
)
console = Console()
bundle_app = typer.Typer(help="Verify and inspect portable failure bundles.")
schema_app = typer.Typer(help="Export versioned portable JSON Schemas.")
app.add_typer(bundle_app, name="bundle")
app.add_typer(schema_app, name="schema")


@app.command()
def version() -> None:
    console.print(__version__)


@app.command()
def doctor() -> None:
    table = Table(title="Agent Effects environment")
    table.add_column("Component")
    table.add_column("Value")
    table.add_row("agent-effects", __version__)
    table.add_row("Python", platform.python_version())
    table.add_row("Platform", platform.platform())
    table.add_row("Pydantic", pydantic.__version__)
    table.add_row("Executable", sys.executable)
    console.print(table)


@app.command("init")
def init_project(
    destination: Annotated[
        Path,
        typer.Argument(help="Destination directory"),
    ] = Path("."),
    template: Annotated[
        str,
        typer.Option("--template", help="starter or lost-ack"),
    ] = "starter",
    force: Annotated[
        bool,
        typer.Option("--force", help="Overwrite files owned by the selected template"),
    ] = False,
) -> None:
    """Generate a guarded, API-key-free Agent Effects project."""

    from .scaffolding import ScaffoldError, generate_project

    try:
        written = generate_project(destination, template=template, force=force)
    except ScaffoldError as exc:
        raise typer.BadParameter(str(exc)) from exc
    console.print(
        f"[green]initialized[/] {template} project at {destination} "
        f"({len(written)} files); next: cd {destination} && pytest -q"
    )


@app.command("bundle-show")
def bundle_show(
    path: Annotated[Path, typer.Argument(exists=True, readable=True)],
    json_output: Annotated[bool, typer.Option("--json")] = False,
) -> None:
    result = load_result(path)
    if json_output:
        console.print_json(result.model_dump_json())
        return
    table = Table(title=f"Failure bundle: {result.case.id}")
    table.add_column("Field")
    table.add_column("Value")
    table.add_row("Agent", result.agent_name)
    table.add_row("Passed", str(result.passed))
    table.add_row("Signature", ", ".join(result.signature))
    table.add_row("Events", str(len(result.events)))
    table.add_row("Elapsed", f"{result.elapsed_ms:.2f} ms")
    console.print(table)
    for violation in result.contracts.violations:
        console.print(f"[bold red]{violation.code}[/]: {violation.message}")


@bundle_app.command("verify")
def bundle_verify(
    path: Annotated[Path, typer.Argument(exists=True, readable=True)],
) -> None:
    """Check content integrity, schemas, safe paths, and internal consistency."""

    try:
        bundle = FailureBundle.load(path)
    except BundleVerificationError as exc:
        raise typer.BadParameter(str(exc)) from exc
    console.print(
        "[green]integrity-checked[/] "
        f"{bundle.manifest.failure_id} ({len(bundle.manifest.files)} payloads); "
        "verified for internal consistency; unsigned hashes do not authenticate "
        "bundle provenance"
    )


@bundle_app.command("inspect")
def bundle_inspect(
    path: Annotated[Path, typer.Argument(exists=True, readable=True)],
    json_output: Annotated[bool, typer.Option("--json")] = False,
) -> None:
    """Inspect an integrity-checked bundle without executing its reproducer."""

    try:
        bundle = FailureBundle.load(path)
    except BundleVerificationError as exc:
        raise typer.BadParameter(str(exc)) from exc
    if json_output:
        console.print_json(bundle.manifest.model_dump_json())
        return
    table = Table(title=f"Integrity-checked failure bundle: {bundle.manifest.case_id}")
    table.add_column("Field")
    table.add_column("Value")
    table.add_row("Failure ID", bundle.manifest.failure_id)
    table.add_row("Full digest", bundle.manifest.content_digest or "<legacy bundle>")
    table.add_row("Agent", bundle.manifest.adapter.name)
    table.add_row("Primary category", bundle.manifest.primary_failure_category)
    table.add_row("Signature", ", ".join(bundle.manifest.signature))
    table.add_row("Reduced case included", str(bundle.manifest.minimized))
    table.add_row("Reproducer", bundle.manifest.reproducer_id or "<not declared>")
    console.print(table)


@schema_app.command("export")
def schema_export(
    output: Annotated[Path, typer.Option("--output", help="Schema output directory")],
) -> None:
    """Export deterministic v1alpha1 JSON Schemas."""

    paths = export_schemas(output)
    console.print(f"[green]exported[/] {len(paths)} schemas to {output}")


@app.command("reproduce")
def reproduce(
    path: Annotated[Path, typer.Argument(exists=True, readable=True)],
    dry_run: Annotated[
        bool,
        typer.Option("--dry-run", help="Identify the reproducer without executing it"),
    ] = False,
) -> None:
    """Rerun a bundle with installed registered code, or inspect with --dry-run."""

    from .reproduction import (
        ReproductionError,
        inspect_registered_reproducer,
        reproduce_bundle,
    )

    try:
        bundle = FailureBundle.load(path)
        if dry_run:
            reproducer = bundle.manifest.reproducer_id
            if reproducer is None:
                raise ReproductionError(
                    "bundle has no registered reproducer; rerun the originating test "
                    "with reproducer_id configured"
                )
            description = inspect_registered_reproducer(reproducer)
            console.print(f"[green]dry run[/]: {description}; no code was executed")
            return
        console.print(
            "[yellow]execution boundary[/]: running installed registered reproducer "
            f"{bundle.manifest.reproducer_id!r}"
        )
        outcome = asyncio.run(reproduce_bundle(bundle))
    except (BundleVerificationError, ReproductionError) as exc:
        raise typer.BadParameter(str(exc)) from exc
    if not outcome.matched:
        console.print(
            "[red]not reproduced[/] "
            f"expected={outcome.expected_signature} actual={outcome.actual_signature}"
        )
        raise typer.Exit(1)
    console.print(
        f"[green]reproduced[/] {bundle.manifest.failure_id}: {', '.join(outcome.actual_signature)}"
    )


@app.command()
def demo(
    agent: Annotated[
        str,
        typer.Option(help="naive, idempotent, reconcile, or overreading"),
    ] = "naive",
    fault: Annotated[
        str,
        typer.Option(help="none, timeout_before, or timeout_after_commit"),
    ] = "timeout_after_commit",
    output: Annotated[
        Path,
        typer.Option(help="Directory for portable failure bundles"),
    ] = Path(".agent-effects/failures"),
    shrink: Annotated[bool, typer.Option("--shrink/--no-shrink")] = True,
) -> None:
    if agent not in AGENTS:
        raise typer.BadParameter(f"unknown agent {agent!r}; choose from {sorted(AGENTS)}")
    try:
        mode = None if fault == "none" else FaultMode(fault)
    except ValueError as exc:
        raise typer.BadParameter(
            "fault must be one of: none, timeout_before, timeout_after_commit"
        ) from exc
    case = make_refund_case(fault_mode=mode, noise_records=8)
    runner = TrialRunner(artifact_dir=None)
    reproducer_id = f"agent-effects.examples.refund/{agent}/v1"

    async def execute() -> int:
        result = await runner.run(
            case=case,
            world_factory=RefundWorld,
            agent=AGENTS[agent],
            contracts=REFUND_CONTRACTS,
            write_failure=False,
            reproducer_id=reproducer_id,
        )
        shrink_report = None
        if not result.passed and shrink:
            signature = extract_failure_signature(result)

            async def evaluate(candidate: TestCase) -> TrialResult:
                return await runner.run(
                    case=candidate,
                    world_factory=RefundWorld,
                    agent=AGENTS[agent],
                    contracts=REFUND_CONTRACTS,
                    write_failure=False,
                )

            shrink_report = await HierarchicalShrinker().shrink(
                case=case,
                target_signature=signature,
                evaluate=evaluate,
                reducers=(
                    ListDDMinReducer(("noise",)),
                    FaultScheduleReducer(),
                ),
                is_valid=is_valid_refund_case,
                validity_predicate_id="agent-effects.examples.refund/is_valid_refund_case/v1",
            )

        artifact_path = None
        if not result.passed:
            artifact_path = FailureStore(output).write(result, shrink=shrink_report)

        refunds = result.final_state.get("refunds", []) if result.final_state else []
        refund_count = len(refunds) if isinstance(refunds, list) else 0

        table = Table(title=f"Refund demo — {agent}")
        table.add_column("Check")
        table.add_column("Value")
        table.add_row("Result", "PASS" if result.passed else "FAIL")
        agent_output = result.agent_run.output if result.agent_run is not None else ""
        table.add_row("Agent output", agent_output or "<none>")
        table.add_row("Contract signature", ", ".join(result.signature) or "<none>")
        table.add_row("Refund count", str(refund_count))
        if shrink_report is not None:
            table.add_row(
                "Shrink evaluations",
                str(shrink_report.candidate_evaluations),
            )
            table.add_row("Shrink stop reason", shrink_report.stop_reason.value)
            table.add_row(
                "Reduced fault count",
                str(len(shrink_report.minimized.faults)),
            )
            minimized_noise = shrink_report.minimized.world.get("noise", [])
            minimized_noise_count = len(minimized_noise) if isinstance(minimized_noise, list) else 0
            table.add_row(
                "Reduced noise records",
                str(minimized_noise_count),
            )
        if artifact_path is not None:
            table.add_row("Failure bundle", str(artifact_path))
        console.print(table)
        return 0 if result.passed else 1

    try:
        exit_code = asyncio.run(execute())
    except ValueError as exc:
        raise typer.BadParameter(str(exc)) from exc
    raise typer.Exit(exit_code)


@app.command("case-validate")
def case_validate(
    path: Annotated[Path, typer.Argument(exists=True, readable=True)],
) -> None:
    case = TestCase.model_validate(json.loads(path.read_text(encoding="utf-8")))
    console.print(f"[green]valid[/] {case.id} ({len(case.faults)} fault rules)")


if __name__ == "__main__":
    app()
