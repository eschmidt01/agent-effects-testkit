"""Deterministic, self-contained HTML reports for verified failure bundles."""

from __future__ import annotations

import html
import json
from dataclasses import dataclass
from pathlib import Path
from typing import cast

from .artifacts import FailureBundle
from .models import ReductionReport, ShrinkReport

_MISSING = object()
_MAX_DIFF_ROWS = 1_000


@dataclass(frozen=True, slots=True)
class _StateChange:
    path: str
    kind: str
    before: object
    after: object


def _escape(value: object) -> str:
    return html.escape(str(value), quote=True)


def _json(value: object, *, compact: bool = False) -> str:
    separators = (",", ":") if compact else None
    rendered = json.dumps(
        value,
        ensure_ascii=False,
        indent=None if compact else 2,
        separators=separators,
        sort_keys=True,
    )
    return _escape(rendered)


def _value(value: object) -> str:
    if value is _MISSING:
        return '<span class="muted">not present</span>'
    return f"<code>{_json(value, compact=True)}</code>"


def _walk_diff(before: object, after: object, path: str, changes: list[_StateChange]) -> None:
    if len(changes) >= _MAX_DIFF_ROWS or before == after:
        return
    if isinstance(before, dict) and isinstance(after, dict):
        before_mapping = cast(dict[str, object], before)
        after_mapping = cast(dict[str, object], after)
        for key in sorted(before_mapping.keys() | after_mapping.keys()):
            child_path = f"{path}.{key}"
            if key not in before_mapping:
                changes.append(_StateChange(child_path, "added", _MISSING, after_mapping[key]))
            elif key not in after_mapping:
                changes.append(_StateChange(child_path, "removed", before_mapping[key], _MISSING))
            else:
                _walk_diff(before_mapping[key], after_mapping[key], child_path, changes)
        return
    if isinstance(before, list) and isinstance(after, list):
        for index in range(max(len(before), len(after))):
            child_path = f"{path}[{index}]"
            if index >= len(before):
                changes.append(_StateChange(child_path, "added", _MISSING, after[index]))
            elif index >= len(after):
                changes.append(_StateChange(child_path, "removed", before[index], _MISSING))
            else:
                _walk_diff(before[index], after[index], child_path, changes)
        return
    changes.append(_StateChange(path, "changed", before, after))


def _state_changes(bundle: FailureBundle) -> tuple[_StateChange, ...]:
    changes: list[_StateChange] = []
    _walk_diff(bundle.initial_world, bundle.final_world, "$", changes)
    return tuple(changes)


def _expected_observed(bundle: FailureBundle) -> tuple[str, str, str]:
    for violation in bundle.violations:
        expected = violation.details.get("expected")
        actual = violation.details.get("actual")
        if expected is None or actual is None:
            continue
        collection = (violation.path or "effect").rsplit(".", maxsplit=1)[-1]
        collection = collection.removeprefix("$").strip("[]") or "effect"
        singular = collection[:-1] if collection.endswith("s") else collection
        expected_label = singular if expected == 1 else collection
        actual_label = singular if actual == 1 else collection
        return (
            f"Expected {expected} {expected_label}",
            f"Observed {actual} {actual_label}",
            f"Expected {expected} {expected_label}; observed {actual} {actual_label}.",
        )
    category = bundle.manifest.primary_failure_category
    return (
        "Expected contracts to pass",
        f"Observed {category} failure",
        f"The trial ended with a {category} failure.",
    )


def _fault_rows(bundle: FailureBundle) -> str:
    if not bundle.faults:
        return '<tr><td colspan="4" class="muted">No injected faults.</td></tr>'
    return "".join(
        "<tr>"
        f"<td><code>{_escape(fault.operation)}</code></td>"
        f"<td>{_escape(fault.mode.value)}</td>"
        f"<td>{fault.occurrence}</td>"
        f"<td><code>{_json(fault.metadata, compact=True)}</code></td>"
        "</tr>"
        for fault in bundle.faults
    )


def _timeline_rows(bundle: FailureBundle) -> str:
    if not bundle.trace:
        return '<li class="empty">No trace events were recorded.</li>'
    return "".join(
        f'<li class="event event-{_escape(event.kind.value)}">'
        f'<span class="sequence">{event.sequence}</span>'
        '<span class="event-main">'
        f"<strong>{_escape(event.kind.value.replace('_', ' '))}</strong> "
        f"<code>{_escape(event.operation)}</code>"
        f"<small>{_json(event.data, compact=True)}</small>"
        "</span></li>"
        for event in bundle.trace
    )


def _violation_cards(bundle: FailureBundle) -> str:
    if not bundle.violations:
        return '<p class="muted">No contract violations were recorded.</p>'
    return "".join(
        '<article class="violation">'
        f"<div><code>{_escape(item.code)}</code><span>{_escape(item.contract)}</span></div>"
        f"<p>{_escape(item.message)}</p>"
        f'<p class="muted">Path: <code>{_escape(item.path or "not specified")}</code></p>'
        f"<pre>{_json(item.details)}</pre>"
        "</article>"
        for item in bundle.violations
    )


def _diff_rows(bundle: FailureBundle) -> str:
    changes = _state_changes(bundle)
    if not changes:
        return '<tr><td colspan="4" class="muted">No state changes were recorded.</td></tr>'
    rows = "".join(
        "<tr>"
        f"<td><code>{_escape(item.path)}</code></td>"
        f'<td><span class="change-{_escape(item.kind)}">{_escape(item.kind)}</span></td>'
        f"<td>{_value(item.before)}</td>"
        f"<td>{_value(item.after)}</td>"
        "</tr>"
        for item in changes
    )
    if len(changes) >= _MAX_DIFF_ROWS:
        rows += (
            '<tr><td colspan="4" class="muted">State diff was limited to '
            f"{_MAX_DIFF_ROWS} rows; use the raw JSON below for the complete snapshots.</td></tr>"
        )
    return rows


def _signature(bundle: FailureBundle) -> str:
    signature = bundle.manifest.failure_signature
    if signature is not None:
        return _json(signature.model_dump(mode="json"))
    return _json(list(bundle.manifest.signature))


def _reduction(bundle: FailureBundle) -> str:
    reduction = bundle.shrink
    if isinstance(reduction, ReductionReport):
        reduction_percent = (
            0.0
            if reduction.initial_size == 0
            else (1 - reduction.final_size / reduction.initial_size) * 100
        )
        steps = (
            "".join(
                "<li>"
                f"<code>{_escape(step.reducer)}</code> — {_escape(step.explanation)} "
                f'<span class="muted">({step.before_size} → {step.after_size})</span>'
                "</li>"
                for step in reduction.accepted_reductions
            )
            or '<li class="muted">No candidate reduction was accepted.</li>'
        )
        return f"""
        <div class="stat-grid">
          <div><strong>{reduction.initial_size}</strong><span>initial size</span></div>
          <div><strong>{reduction.final_size}</strong><span>final size</span></div>
          <div><strong>{reduction_percent:.1f}%</strong><span>reduction</span></div>
          <div><strong>{reduction.candidate_evaluations}</strong><span>evaluations</span></div>
          <div><strong>{reduction.cache_hits}</strong><span>cache hits</span></div>
          <div><strong>{reduction.elapsed_ms:.3f} ms</strong><span>in-process time</span></div>
        </div>
        <dl class="details-grid">
          <dt>Guarantee</dt><dd><code>{_escape(reduction.guarantee.value)}</code></dd>
          <dt>Stop reason</dt><dd><code>{_escape(reduction.stop_reason.value)}</code></dd>
          <dt>Validity predicate</dt><dd><code>{_escape(reduction.validity_predicate)}</code></dd>
          <dt>Reducers</dt><dd>{_escape(", ".join(reduction.reducers_used) or "none")}</dd>
          <dt>Evaluation budget</dt><dd>{reduction.candidate_evaluations} / {reduction.evaluation_budget}
            (exhausted: {_escape(str(reduction.evaluation_budget_exhausted).lower())})</dd>
          <dt>Time budget</dt><dd>{_escape(reduction.time_budget_ms or "not configured")}
            (exhausted: {_escape(str(reduction.time_budget_exhausted).lower())})</dd>
          <dt>Target signature</dt><dd><pre>{_json(reduction.target_signature.model_dump(mode="json"))}</pre></dd>
        </dl>
        <p>{_escape(reduction.diagnostic)}</p>
        <h3>Accepted reductions</h3><ol>{steps}</ol>
        """
    if isinstance(reduction, ShrinkReport):
        return (
            "<p>This legacy reduction report records "
            f"{reduction.evaluations} evaluations and {len(reduction.accepted_steps)} "
            "accepted steps. It does not make a local-minimality guarantee.</p>"
        )
    return '<p class="muted">No reduced counterexample was included.</p>'


def _raw_sections(bundle: FailureBundle) -> str:
    documents: tuple[tuple[str, object], ...] = (
        ("manifest.json", bundle.manifest.model_dump(mode="json")),
        ("case.json", bundle.case.model_dump(mode="json")),
        ("minimized-case.json", bundle.minimized_case.model_dump(mode="json")),
        ("initial-world.json", bundle.initial_world),
        ("final-world.json", bundle.final_world),
        ("faults.json", [item.model_dump(mode="json") for item in bundle.faults]),
        ("trace.json", [item.model_dump(mode="json") for item in bundle.trace]),
        ("violations.json", [item.model_dump(mode="json") for item in bundle.violations]),
        ("result.json", bundle.result.model_dump(mode="json")),
        (
            "reduction report",
            bundle.shrink.model_dump(mode="json") if bundle.shrink is not None else None,
        ),
    )
    return "".join(
        f"<details><summary>{_escape(name)}</summary><pre><code>{_json(document)}</code></pre></details>"
        for name, document in documents
    )


def render_bundle_report(bundle: FailureBundle) -> str:
    """Render one already verified bundle as deterministic standalone HTML."""

    expected, observed, explanation = _expected_observed(bundle)
    return f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <meta http-equiv="Content-Security-Policy" content="default-src 'none'; style-src 'unsafe-inline'; img-src data:; object-src 'none'; base-uri 'none'; form-action 'none'; frame-ancestors 'none'">
  <title>Agent Effects failure — {_escape(bundle.manifest.case_id)}</title>
  <style>
    :root {{ color-scheme: light dark; --bg:#f7f5f0; --panel:#fff; --text:#18201d; --muted:#61706a; --line:#d9ded9; --accent:#007a65; --bad:#b42318; --warn:#9a6700; --commit:#0a66c2; --code:#eef1ee; }}
    @media (prefers-color-scheme: dark) {{ :root {{ --bg:#101513; --panel:#171d1a; --text:#edf4ef; --muted:#a6b4ad; --line:#33413a; --accent:#4bd1b3; --bad:#ff8a80; --warn:#f2c14e; --commit:#75b8ff; --code:#222b27; }} }}
    * {{ box-sizing:border-box; }} body {{ margin:0; background:var(--bg); color:var(--text); font:15px/1.55 ui-sans-serif,system-ui,-apple-system,BlinkMacSystemFont,"Segoe UI",sans-serif; }}
    main {{ max-width:1120px; margin:auto; padding:48px 24px 80px; }} header {{ border-bottom:1px solid var(--line); padding-bottom:32px; }}
    .eyebrow {{ color:var(--accent); font-weight:800; letter-spacing:.08em; text-transform:uppercase; }} h1 {{ font-size:clamp(2rem,5vw,4.25rem); line-height:1.03; margin:.2em 0; letter-spacing:-.045em; }} h2 {{ margin-top:42px; font-size:1.55rem; }} h3 {{ margin-top:26px; }}
    .lede {{ font-size:1.2rem; max-width:760px; }} .warning {{ margin-top:22px; padding:14px 18px; border-left:4px solid var(--warn); background:var(--panel); }}
    .outcome {{ display:grid; grid-template-columns:1fr 1fr; gap:14px; margin:28px 0; }} .outcome div,.stat-grid div {{ background:var(--panel); border:1px solid var(--line); border-radius:12px; padding:18px; }} .outcome strong {{ display:block; font-size:1.35rem; }} .expected strong {{ color:var(--accent); }} .observed strong {{ color:var(--bad); }}
    table {{ width:100%; border-collapse:collapse; background:var(--panel); }} th,td {{ text-align:left; vertical-align:top; border:1px solid var(--line); padding:10px 12px; }} th {{ font-size:.8rem; text-transform:uppercase; letter-spacing:.04em; color:var(--muted); }}
    code,pre {{ font-family:ui-monospace,SFMono-Regular,Consolas,monospace; }} code {{ overflow-wrap:anywhere; }} pre {{ white-space:pre-wrap; overflow-wrap:anywhere; padding:14px; background:var(--code); border-radius:8px; }}
    .timeline {{ list-style:none; padding:0; position:relative; }} .event {{ display:flex; gap:14px; padding:9px 0; }} .sequence {{ display:grid; place-items:center; flex:0 0 34px; height:34px; border:2px solid var(--line); border-radius:50%; font-weight:800; background:var(--panel); }} .event-main {{ min-width:0; }} .event-main strong {{ display:inline-block; min-width:108px; text-transform:uppercase; font-size:.72rem; letter-spacing:.05em; }} .event-main small {{ display:block; color:var(--muted); }} .event-commit .sequence {{ border-color:var(--commit); color:var(--commit); }} .event-fault .sequence {{ border-color:var(--bad); color:var(--bad); }}
    .violation {{ border:1px solid var(--line); border-left:4px solid var(--bad); background:var(--panel); padding:16px 18px; margin:12px 0; }} .violation div {{ display:flex; gap:12px; align-items:center; }} .violation span,.muted {{ color:var(--muted); }}
    .change-added {{ color:var(--bad); font-weight:700; }} .change-removed {{ color:var(--warn); font-weight:700; }} .change-changed {{ color:var(--commit); font-weight:700; }}
    .stat-grid {{ display:grid; grid-template-columns:repeat(3,1fr); gap:10px; }} .stat-grid strong,.stat-grid span {{ display:block; }} .stat-grid strong {{ font-size:1.3rem; }} .stat-grid span {{ color:var(--muted); }} .details-grid {{ display:grid; grid-template-columns:180px 1fr; gap:8px 16px; }} .details-grid dt {{ color:var(--muted); }} .details-grid dd {{ margin:0; min-width:0; }}
    details {{ border:1px solid var(--line); background:var(--panel); margin:8px 0; }} summary {{ cursor:pointer; padding:12px 14px; font-weight:700; }} details pre {{ margin:0; border-radius:0; }} footer {{ margin-top:48px; padding-top:24px; border-top:1px solid var(--line); color:var(--muted); }}
    @media (max-width:700px) {{ .outcome,.stat-grid {{ grid-template-columns:1fr; }} .details-grid {{ grid-template-columns:1fr; }} table {{ display:block; overflow-x:auto; }} }}
  </style>
</head>
<body>
<main>
  <header>
    <div class="eyebrow">Agent Effects · integrity-checked failure report</div>
    <h1>{_escape(explanation)}</h1>
    <p class="lede">The agent reported <q>{_escape(bundle.result.agent_run.output if bundle.result.agent_run else "no output")}</q>, but deterministic contracts rejected the world it left behind.</p>
    <div class="outcome"><div class="expected"><span>Contract expectation</span><strong>{_escape(expected)}</strong></div><div class="observed"><span>Final world</span><strong>{_escape(observed)}</strong></div></div>
    <p class="warning"><strong>Sensitive-data boundary:</strong> failure bundles and reports may contain state, tool arguments, and identifiers. Redaction is adapter-owned. Review this file before uploading it as a CI artifact or sharing it.</p>
  </header>

  <section id="identity"><h2>Failure identity</h2><dl class="details-grid">
    <dt>Case</dt><dd><code>{_escape(bundle.manifest.case_id)}</code></dd>
    <dt>Failure ID</dt><dd><code>{_escape(bundle.manifest.failure_id)}</code></dd>
    <dt>Category</dt><dd><code>{_escape(bundle.manifest.primary_failure_category)}</code></dd>
    <dt>Agent adapter</dt><dd><code>{_escape(bundle.manifest.adapter.name)}</code></dd>
    <dt>Signature</dt><dd><pre>{_signature(bundle)}</pre></dd>
  </dl></section>

  <section id="faults"><h2>Injected fault</h2><table><thead><tr><th>Operation</th><th>Mode</th><th>Occurrence</th><th>Metadata</th></tr></thead><tbody>{_fault_rows(bundle)}</tbody></table></section>
  <section id="timeline"><h2>Event timeline</h2><p>Blue markers identify durable commits. Red markers identify injected faults.</p><ol class="timeline">{_timeline_rows(bundle)}</ol></section>
  <section id="violations"><h2>Contract violations</h2>{_violation_cards(bundle)}</section>
  <section id="state-diff"><h2>Structured state diff</h2><table><thead><tr><th>Path</th><th>Change</th><th>Initial</th><th>Final</th></tr></thead><tbody>{_diff_rows(bundle)}</tbody></table></section>
  <section id="reduction"><h2>Reduction</h2>{_reduction(bundle)}</section>
  <section id="reproduction"><h2>Reproduce</h2><p>Verification and report generation execute no reproducer code. The final command crosses that boundary and executes installed registered code; run it only in an appropriate test environment.</p><pre><code>agent-effects bundle verify /path/to/bundle
agent-effects bundle inspect /path/to/bundle
agent-effects reproduce --dry-run /path/to/bundle
agent-effects reproduce /path/to/bundle</code></pre></section>
  <section id="raw"><h2>Raw verified JSON</h2><p>These collapsible documents are embedded for offline inspection. JavaScript is not required.</p>{_raw_sections(bundle)}</section>
  <footer>Bundle toolkit version: Agent Effects Testkit {_escape(bundle.manifest.toolkit_version)}. This report was derived locally from content verified for integrity and internal consistency. Unsigned hashes do not authenticate provenance.</footer>
</main>
</body>
</html>
"""


def write_bundle_report(bundle: FailureBundle, output: Path) -> Path:
    """Write a deterministic report for an already verified bundle."""

    destination = output.resolve()
    try:
        destination.relative_to(bundle.root)
    except ValueError:
        pass
    else:
        raise ValueError(
            "report output must be outside the verified bundle directory so its "
            "manifest file set remains valid"
        )
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_text(render_bundle_report(bundle), encoding="utf-8", newline="\n")
    return destination
