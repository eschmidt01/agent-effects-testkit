# Validation report

**Project:** Agent Effects Testkit 0.1.0a1
**Validation date:** 2026-08-19
**Scope:** public-alpha candidate through AE-003, AE-004, and minimum viable
developer experience.

This report records commands that completed successfully in the implementation
environment. It is not a claim of product-market fit, company readiness,
production readiness, or a completed remote CI run.

## Source checks

The primary source run used CPython 3.12.0, Ruff 0.16.3, mypy 1.20.2,
pytest 9.1.1, MkDocs 1.6.1, Hypothesis 6.165.10, and Pydantic 2.13.4.

| Command | Result |
|---|---|
| `ruff check .` | Passed |
| `ruff format --check .` | Passed; 91 files already formatted |
| `mypy --strict src tests` | Passed; 41 source files checked |
| `pytest` | Passed; 121 tests |
| `pytest --cov=agent_effects --cov-report=term-missing` | Passed; 92.08% branch coverage |
| `mkdocs build --strict` | Passed |
| `python -m compileall -q src tests examples scripts` | Passed |

The configured branch-coverage floor is 90%.

## Reduction benchmark

The deterministic benchmark starts with 1,000 unrelated world records, one
unrelated fault, and the naive refund lost-ack failure. Hierarchical ddmin
produced zero noise records and one essential fault in 12 candidate evaluations
(11 accepted reductions, one cache hit, 31.382 ms observed), below the required
80-evaluation ceiling. The initial/final size metrics were 31,621 and 648. The
31.382 ms observation applies only to this deterministic in-process refund
example; it is not an expected shrinking time for networked or model-driven
agents.

The run ended `locally_minimal`: no smaller valid, same-signature candidate was
found by the configured reducers within the configured budgets. This is not a
global-minimality claim.

The non-monotonic ddmin regression proves partition removal can reduce
`["a", "b", "c", "d"]` to `["c", "d"]` when removing either `"a"` or `"b"`
alone changes the failure. The old one-by-one greedy reducer cannot make that
first move and leaves the original list unchanged.

## Build and metadata

| Command | Result |
|---|---|
| `uv build` (uv 0.12.5) | Passed; sdist and universal wheel built |
| `twine check dist/*` (Twine 6.2.0) | Both distributions passed |

## Installed-wheel checks

The wheel was installed outside the source tree under CPython 3.11.10, 3.12.14,
and 3.13.0. In each environment, package and metadata versions were `0.1.0a1`,
the generated passing starter ran successfully, and pytest passed.

The clean-room workflow additionally proved:

- the installed pytest plugin auto-loaded and supplied `agent_effects_runner`;
- `agent-effects init demo --template lost-ack` generated four portable files;
- the first pytest run exited 1 for `duplicate_business_effect` and
  `refund_cardinality` and emitted a bundle;
- verify and inspect completed without executing reproducer code;
- `reproduce --dry-run` identified the built-in reproducer without executing it;
- reproduction matched the typed failure signature;
- switching to stable idempotency made pytest pass.

The acceptance script prints a readable transcript on each run. That transient,
machine-specific output is intentionally not stored in source control.

## Schemas and bundles

- 20 Draft 2020-12 schemas export with stable `v1alpha1` `$id` values.
- Fresh exports match checked-in fixtures byte-for-byte.
- Existing checked-in `0.1.0a0` cases and bundles continue to load.
- New manifests contain a full content digest and typed failure signature.
- Tests cover missing, modified, unrelated, unsafe, incompatible, malformed,
  and cross-file-mismatch bundle inputs plus shortened-ID collision handling.
- Unsigned hashes check integrity relative to the manifest; they do not
  authenticate author or provenance.

The hierarchical sample is an intentional test/documentation fixture under
[`tests/fixtures/failure_bundles/refund-lost-ack`](tests/fixtures/failure_bundles/refund-lost-ack).

## Remaining release gates

- No Git metadata or remote was present, so no actual GitHub Actions run, URL,
  or commit SHA is available. The remote Python 3.11–3.13 CI gate remains open.
- An external engineer has not independently completed or timed the quickstart.
- No design-partner or retained real-world regression evidence exists yet.
- Reproducer code is installed code and still requires an appropriate external
  sandbox for untrusted adapters.

The accurate status is: an experimental public-alpha candidate for deterministic
pre-production testing of AI-agent side effects. It is not a generally
production-ready release.
