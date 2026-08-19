# Failure signatures

`FailureSignature` is the identity the shrinker and reproducer must preserve.
It deliberately excludes timestamps, paths, messages, random IDs, record values,
and semantically irrelevant ordering.

For ordinary contract failures, the default signature contains:

- primary category `contract`;
- each sorted `(contract_id, violation_code)` pair;
- the count of each pair.

For a primary lifecycle failure, it contains:

- primary stage;
- category;
- exception class or stable error code when supplied.

A cleanup failure cannot replace an earlier agent or contract failure. A
duplicate-effect counterexample therefore cannot be accepted when a candidate
instead crashes during world creation.

Advanced domains may pass a deterministic `signature_extractor` to
`HierarchicalShrinker.shrink`. Custom extractors should use stable domain codes
and must apply the same exclusions.
