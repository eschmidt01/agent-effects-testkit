# Governance

The project begins with a maintainer-led model optimized for a small, coherent
alpha.

## Maintainers

Maintainers merge changes, cut releases, manage security reports, and protect
the product boundary. New maintainers should demonstrate sustained technical
contributions, careful review, and respectful community participation.

## Decisions

- Routine changes are decided through pull-request review.
- Public schema, architecture, security-boundary, or scope changes require an
  ADR and at least one maintainer approval.
- Irreversible or controversial changes should remain open for public comment
  after the repository has an active community.
- Security fixes may be developed privately and documented after release.

## Compatibility

During alpha, maintainers may make breaking changes when evidence requires them.
Every breaking change must include migration guidance and a versioned artifact
strategy. The bar rises substantially after `1.0`.

## Commercial neutrality

Core remains local-first and usable without a hosted service. A future hosted
product must not remove essential testing, shrinking, or bundle functionality
from the Apache-2.0 core.
