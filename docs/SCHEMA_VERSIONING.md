# Portable schema versioning

Agent Effects exports JSON Schema Draft 2020-12 documents with stable identifiers
under `https://schemas.agent-effects.dev/v1alpha1/`. The URL is an identifier;
schema export and validation do not require network access.

## Source of truth

Portable Python models in `agent_effects.models` are the source of truth. Run:

```bash
agent-effects schema export --output ./schemas
```

The checked-in `schemas/v1alpha1` directory is a compatibility fixture. Tests
compare a fresh export byte-for-byte with these files and validate representative
instances using JSON Schema Draft 2020-12.

## Additive changes

An additive change may retain `v1alpha1` only when existing valid documents remain
valid and their meaning does not change. During alpha, examples include:

- adding an optional field with a backward-compatible default;
- adding a new exported schema without changing an existing schema;
- documenting a previously unspecified value more precisely without narrowing it.

Because portable models currently reject unknown fields, adding a field affects
older Python readers even when the JSON shape is otherwise additive. Producers
must not emit a new optional field until the supported reader range understands it.

`0.1.0a1` adds optional `content_digest` and `failure_signature` manifest fields.
The reader continues to load checked-in `v1alpha1` bundles produced by `0.1.0a0`;
new writers emit both fields and use the full digest as authoritative identity.
It also adds independent failure-signature and reduction-report schema exports.
The final candidate adds optional reduction guarantee, validity-predicate, and
budget-exhaustion metadata. Readers accept the earlier `minimal` stop value as
`LEGACY_MINIMAL` with `no_minimality_claim`; new writers emit
`locally_minimal` only when the configured local search completes.

## Breaking changes

A new schema version and migration note are required when a change:

- removes or renames a field;
- makes an optional field required;
- changes a field type, enum meaning, or validation range;
- changes failure identity, commit semantics, or cross-file bundle relationships;
- makes a previously valid document invalid;
- changes a stable `$id` or file role.

Readers reject unsupported versions. They never silently reinterpret a document
under a different schema version.

## Determinism and portability

Schema files use sorted-key, UTF-8 JSON with a trailing newline. They contain no
timestamps, local paths, usernames, or environment-specific values. Generated
schemas are development and interoperability artifacts; the Python runtime never
imports checked-in schema files.
