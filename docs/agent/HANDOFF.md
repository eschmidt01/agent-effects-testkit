# Implementation handoff

Task: AE-201 — `v0.1.0a2` visual failure report
Status: locally complete on `feat/visual-failure-report`; pull-request CI and
review remain release gates

Changed:

- added deterministic `bundle report` rendering and local `--open` support;
- added expected/observed state, fault table, durable-commit timeline,
  violations, structured diff, reduction guarantee, reproduction boundary, and
  collapsible raw verified JSON;
- made report generation load a fully verified bundle, reject output inside the
  bundle, escape untrusted strings, use no remote assets/scripts, and emit CSP;
- connected `demo --agent naive --report` while retaining failure exit status;
- bumped the candidate package version to `0.1.0a2` without tagging or release;
- redesigned the README/docs around “Test the world your AI agent leaves
  behind” and category-level positioning;
- added light/dark transaction SVGs, reproducible 25-second terminal GIF,
  report screenshot, social preview, public synthetic report, and provenance;
- added a least-privilege GitHub Pages workflow, community issue drafts, and
  launch-demo script; and
- reordered the roadmap so the visual report precedes the single proposed
  LangGraph integration.

Validation:

- `ruff check .` → passed;
- `ruff format --check .` → 101 files already formatted;
- `mypy --strict src tests` → passed, 44 source files;
- `pytest` → 130 passed;
- branch coverage → 91.61%, above the unchanged 90% floor;
- `mkdocs build --strict` → passed;
- `python -m compileall -q src tests examples scripts` → passed;
- `uv build` → `0.1.0a2` sdist and wheel built;
- `twine check dist/*` → both distributions passed;
- installed-wheel clean-room report/bundle/reproduction/safe-agent flow → passed;
- Chrome structural/render check → two commits, one fault, two violations, no
  scripts, remote references, console warnings, or subresource requests;
- Firefox → not locally available.

Decisions:

- reports are derived artifacts beside bundles, never unlisted files within
  them;
- report output is deterministic for a fixed verified bundle and renderer;
- native HTML disclosure elements keep raw JSON usable without JavaScript;
- no report code imports reproduction or entry-point discovery;
- the renderer shows the bundle's toolkit version rather than claiming the
  current renderer created the original failure; and
- Pages deploys only from `main`; this feature branch does not change that
  repository setting or publish a site.

Risks / unresolved:

- reports intentionally contain unredacted bundle evidence; adapters still own
  redaction and CI owners control artifact visibility and retention;
- the structured diff caps displayed rows at 1,000 while complete snapshots
  remain available under raw JSON;
- unsigned bundle hashes do not authenticate provenance;
- the browser automation security boundary blocked direct `file://` navigation,
  so Chrome visual validation used a loopback-only server with exactly one
  document request; unit tests cover local file URI opening and zero report
  subresources;
- GitHub Pages must be enabled for GitHub Actions after the pull request is
  merged if the repository setting is not already enabled; and
- no external engineer has completed an independent onboarding attempt.

Next:

- review and merge only after pull-request CI is green;
- enable/verify GitHub Pages and set the prepared social preview manually;
- collect one independent onboarding/adoption report and file findings; then
- begin only the scoped optional LangGraph `0.2.0a1` milestone from ADR 0005.
