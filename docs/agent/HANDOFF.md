# Implementation handoff

Task: AE-003, AE-004, and minimum viable Phase 6
Status: local and remote CI complete; prerelease and external quickstart timing open

Changed:

- added stable typed contract/lifecycle failure signatures and custom extractors;
- added sequential hierarchical ddmin, composable reducers, canonical caching,
  confirmation runs, validity enforcement, evaluation/time budgets, and reports;
- added full-digest bundle identity, safe short-ID collision handling, reduction
  reports, exact typed reproduction, and no-execution dry-run inspection;
- corrected unsigned-hash security language across product and security docs;
- added guarded passing and explicit lost-ack project templates through `init`;
- added eight deterministic contract helpers and actionable runner diagnostics;
- added onboarding documentation and installed-wheel clean-room automation;
- bumped the candidate version to `0.1.0a1` and updated schema fixtures.

Validation:

- `ruff check .` → passed;
- `ruff format --check .` → 88 files already formatted;
- `mypy --strict src tests` → passed, 41 source files;
- `pytest` → 120 passed;
- branch coverage → 92.17%, 90% floor;
- `mkdocs build --strict` → passed;
- `uv build` → sdist and wheel built;
- `twine check dist/*` → both passed;
- installed wheel starter → passed on Python 3.11.10, 3.12.14, and 3.13.0;
- clean installed-wheel lost-ack workflow and pytest plugin smoke → passed;
- 1,000-record ddmin benchmark → 12 evaluations, zero noise, one fault.

Decisions:

- failure signatures exclude messages, paths, timestamps, random IDs, dynamic
  record values, and irrelevant ordering;
- complete SHA-256 digests are authoritative; 12-character IDs are display-only;
- unsigned manifests establish internal consistency, not author authenticity;
- candidate evaluation is sequential and always preceded by strict size and
  validity checks;
- normal scaffolds pass; only `--template lost-ack` intentionally fails.

Risks / unresolved:

- GitHub Actions run `32313536424` passed the complete Python 3.11–3.13,
  quality, package, and clean-room matrix for commit `97e853b061a10686a835ead1a82d6a28ef528719`;
- no external engineer has timed the quickstart;
- installed registered reproducers execute code and are not sandboxed;
- adapters still own redaction, agent execution limits, and test-environment isolation;
- custom signature extractors are supported by shrinking, but their code is not
  serialized into portable bundles.

Next:

- publish the authorized GitHub prerelease from an exact green commit, then run
  one external onboarding session before starting LangGraph.
