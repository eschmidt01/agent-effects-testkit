# Community issue candidates

These bounded tasks are intended to be opened with the indicated labels. They
avoid requiring familiarity with the runner internals.

## Good first issue: add report print styles

Labels: `good first issue`, `documentation`

Add a `@media print` block to the static report so tables avoid page breaks,
colors remain distinguishable in grayscale, raw JSON stays collapsed or omitted,
and security text remains visible. Add a structural test for the print rules.

## Good first issue: document a CI artifact recipe

Labels: `good first issue`, `documentation`

Add copy-paste GitHub Actions and GitLab CI examples that generate a report from
a bundle and upload only explicitly selected synthetic or redacted artifacts.
Explain retention and visibility risks; add no telemetry or network behavior to
the runtime.

## Good first issue: add a monotonic-state contract helper

Labels: `good first issue`, `enhancement`

Implement the existing AE-203 follow-up for a deterministic helper that rejects
backwards state transitions. Keep the API typed and small, add positive and
negative tests, stable contract and violation IDs, and one documented example.

## Help wanted: independently maintained fault pack

Labels: `help wanted`, `enhancement`

Propose and maintain one framework-neutral fault pack grounded in an independent
real failure pattern—for example duplicate webhook delivery or authorization
revocation. It must use synthetic data, deterministic contracts, domain-valid
reduction, no API key, and the portable bundle and report formats. Start with an
ADR or issue design before adding runtime surface.
