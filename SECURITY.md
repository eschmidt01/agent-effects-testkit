# Security policy

## Supported versions

The project is pre-release. Security fixes are applied to the latest alpha only.

## Reporting

Do not open a public issue for a vulnerability that could expose secrets,
private world snapshots, personal data, arbitrary code execution, or unsafe
artifact handling. Contact the repository maintainers privately through the
security-advisory mechanism after the repository is published.

Until a public repository exists, keep the report private and include:

- affected version/commit;
- concise reproduction using synthetic data;
- impact and attack prerequisites;
- suggested mitigation if known.

## Security boundaries

The core testkit does **not** sandbox an agent. A world or agent adapter runs with
the permissions of the test process. Treat third-party adapters and target
agents as untrusted code and run them in an appropriate external sandbox.

Failure bundles can contain full initial/final state and tool arguments. Never
point the alpha at production data without a reviewed redaction policy. Secrets,
authentication tokens, raw medical/HR data, and customer identifiers must not be
serialized.

`agent-effects bundle verify` and `bundle inspect` parse untrusted data but do
not execute it. SHA-256 hashes provide file-integrity verification relative to
the manifest, accidental-corruption detection, and internal consistency checks.
Because manifests are unsigned, these checks do not authenticate the author,
establish trusted provenance, or resist an attacker who can regenerate the
manifest.

`agent-effects reproduce --dry-run` identifies the registered reproducer without
executing it.
`agent-effects reproduce` executes a built-in or installed registered adapter
after bundle verification; run that command only with trusted adapter packages
and test-scoped credentials. Bundle data is never used as an arbitrary Python
import path. Reproduction is not a sandbox.

See `docs/THREAT_MODEL.md` for the detailed model and required controls.
