# Failure bundle specification

## Version

`agent-effects.failure/v1alpha1`

A failure bundle is a local, content-addressed directory for inspection, CI
retention, one-command reproduction, and promotion into a regression fixture.

## Canonical layout

```text
<case-id>-<failure-id>/
├── manifest.json
├── case.json
├── minimized-case.json
├── initial-world.json
├── final-world.json
├── faults.json
├── trace.json
├── violations.json
├── result.json
├── reproduce.md
├── reduction-report.json # present for hierarchical reduction
├── shrink.json           # legacy greedy-report compatibility
├── trace.jsonl          # alpha compatibility view
└── README.md            # alpha compatibility view
```

The original case is never replaced by the reduced case. The filename
`minimized-case.json` and manifest field `minimized` are retained as portable
`v1alpha1` schema names; they mean that a reduction report/case is included, not
that global minimality was proved. When no reduction report exists,
`minimized-case.json` equals `case.json` explicitly.

## Manifest

`manifest.json` is a `FailureBundleManifest` containing:

- bundle schema and toolkit versions;
- creation timestamp;
- authoritative full SHA-256 content digest derived from the case, typed failure
  signature, and agent name;
- shortened 12-character failure ID for display and directory names;
- case, subject, test, and contract identifiers;
- adapter module/type information;
- primary failure category and exact violation signature;
- optional registered reproducer ID;
- reduced-case-present status (the compatibility field is named `minimized`);
- role, byte count, and SHA-256 hash for every payload.

The manifest does not hash itself. Every other file is listed exactly once.
Portable POSIX-relative paths are required.

The complete digest is authoritative. If two bundles share a shortened display
ID, the writer compares their complete digests and selects a non-overwriting
alternate path.

## Verification

Run:

```bash
agent-effects bundle verify ./failure-bundle
agent-effects bundle inspect ./failure-bundle
```

Verification fails closed for unsupported or malformed manifests, unsafe paths,
symlinks, oversized inputs, missing or unlisted files, size/hash mismatches,
invalid payload schemas, and disagreement between redundant payloads. Cross-file
checks bind the case, adapter, snapshots, faults, trace, violations, result,
typed signature, full content digest, display ID, reduced case, and reduction
report into one internally consistent unit.

These unsigned hashes are tamper-evident relative to the manifest: they detect
accidental corruption and changes made without regenerating the manifest. They
do not authenticate a bundle author, establish trusted provenance, resist an
attacker who can regenerate the manifest, or sandbox reproducer code.

Early alpha bundles without content hashes are still readable through
`load_result()`, but `FailureBundle.load()` rejects them with an explicit
regeneration message.

## Reproduction

Run:

```bash
agent-effects reproduce ./failure-bundle
agent-effects reproduce --dry-run ./failure-bundle
```

The dry run identifies the reproducer without loading or executing it.
Reproduction verifies the bundle first, resolves its reproducer by a registered
identifier, reruns the reduced case in `minimized-case.json`, and requires the same exact typed
failure signature. Bundle data is never treated as a Python
import path. A third-party adapter must install an `agent_effects.reproducers`
entry point; missing adapter code produces an actionable error.

Verification and inspection never execute code. Reproduction explicitly executes
an installed, registered adapter and should be used only in a suitably isolated
test environment.

## Privacy

Bundles may contain sensitive world state and tool arguments. Core performs no
automatic redaction in this alpha. Applications must use synthetic data where
possible, keep credentials outside `TestCase`, redact before recording, restrict
artifact access and retention, and review bundles before sharing them.
