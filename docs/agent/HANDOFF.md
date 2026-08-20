# Implementation handoff

Task: AE-201 — `v0.1.0a2` visual failure report
Status: complete on `feat/visual-failure-report`; pull-request review remains a
release gate

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
- added flat light/dark transaction traces, reproducible 20.68-second terminal
  GIF, report screenshot, social preview, public synthetic report, and
  provenance;
- replaced the initial marketing-heavy visual treatment with a restrained
  GitHub-style documentation system using system fonts, neutral surfaces,
  crisp borders, grouped navigation, and accessible status colors;
- removed an unfinished terminal command and local absolute path from the GIF,
  with a CLI regression test for working-directory-relative artifact display;
- added a least-privilege GitHub Pages workflow, community issue drafts, and
  launch-demo script; and
- reordered the roadmap so the visual report precedes the single proposed
  LangGraph integration.

Validation:

- `ruff check .` → passed;
- `ruff format --check .` → 99 files already formatted;
- `mypy --strict src tests` → passed, 44 source files;
- `pytest` → 132 passed;
- branch coverage → 91.64%, above the unchanged 90% floor;
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
- Pages deploys from `main` and the visual-report branch so the draft can be
  reviewed at the public documentation URL without merging it.

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
- the feature-branch Pages trigger should be removed after merge if the branch
  is retained rather than deleted; and
- no external engineer has completed an independent onboarding attempt.

Next:

- review and merge only after pull-request CI and Pages are green;
- set the prepared social preview manually in repository settings;
- collect one independent onboarding/adoption report and file findings; then
- begin only the scoped optional LangGraph `0.2.0a1` milestone from ADR 0005.
