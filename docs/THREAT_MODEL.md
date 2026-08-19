# Threat model

## Scope

Agent Effects is a testing library, not a sandbox or production authorization
system. It executes adapters and agents in the caller's Python process unless an
external environment supplies isolation.

## Assets

- developer machine and CI runner;
- credentials used by world/agent adapters;
- source code and dependency integrity;
- initial/final world snapshots;
- tool arguments, traces, and failure bundles;
- test results used as release gates.

## Adversaries and failure sources

- a malicious or compromised agent under test;
- prompt injection causing unsafe tool inputs;
- a buggy third-party adapter;
- a crafted failure bundle loaded from an untrusted source;
- accidental use of production data;
- compromised dependencies or CI actions;
- denial of service through infinite loops or enormous traces;
- weak contracts that create false confidence.

## Primary risks

### Arbitrary code and network access

The target agent and adapter can execute with test-process permissions. Core does
not isolate filesystem, process, or network access.

**Mitigation:** run untrusted targets in containers/VMs controlled outside the
library. Future subprocess/container adapters require a separate security ADR.

### Secret and personal-data leakage

Snapshots and tool arguments can contain credentials, employee records, payment
data, or other sensitive information. Failure bundles are designed for easy CI
upload, which increases exposure.

**Mitigation:** use synthetic data by default; inject secrets outside `TestCase`;
add adapter-specific redaction before recording; restrict CI artifact access;
set retention; review `AE-104` redaction hooks before production trace import.

### Unsafe real side effects

An incorrectly configured adapter could call a live payment, email, HR, or
infrastructure service while intentionally injecting retries.

**Mitigation:** require explicit test endpoints/accounts, sandbox credentials,
and reset capability. Documentation and future adapters must fail closed when an
environment cannot prove it is non-production.

### Artifact paths and parsing

Case IDs become part of local failure-directory names. Untrusted IDs containing
path separators or traversal components could otherwise write outside the
configured artifact root. JSON documents may also be oversized or crafted to
exhaust memory, and README content could later become an injection surface in a
viewer.

**Mitigation:** portable case IDs are restricted to a bounded filename-safe
character set. Integrity-checked bundles require normalized relative paths, reject
symlinks and unlisted files, enforce per-file size limits, validate versioned
schemas, compare complete SHA-256 hashes, and cross-check redundant identities.
Unsigned hashes provide integrity relative to the manifest and do not authenticate
the author or provenance; an attacker able to change payloads and regenerate the
manifest can create a new internally consistent bundle. Short display-ID collisions
are resolved by comparing full digests and selecting a non-overwriting path. Escape
content in any future HTML viewer; never execute bundle content.

### Reproducer execution

An untrusted bundle could try to name executable code. Verification and inspection
therefore never execute anything and reproducer identifiers are not import paths.
`agent-effects reproduce --dry-run` reports the registered identity without
executing it.
`agent-effects reproduce` resolves only built-in or installed
`agent_effects.reproducers` entry points after verification. Reproduction still
executes trusted installed adapter code and must run with test credentials in an
appropriate external sandbox when the adapter is not trusted.

### Oracle failure and false confidence

A broken contract can miss a dangerous outcome. The current engine converts
contract exceptions to failures but cannot prove completeness.

**Mitigation:** mutation tests, independent state/trace contracts, review by
domain experts, and explicit non-goal language. Do not market a passing test as a
formal safety proof.

### Denial of service

Agents can loop, stream unbounded output, or create enormous state. Shrinking can
require many expensive reruns.

**Mitigation:** the shrinker enforces caller-controlled elapsed-time and candidate
evaluation budgets and runs candidates sequentially. Agent execution timeouts,
cost, event, and state-size limits remain adapter/CI responsibilities. CI should
use deterministic scripted agents before live models.

### Supply chain

Optional framework integrations can dramatically increase dependency surface.

**Mitigation:** minimal core dependencies, isolated extras, pinned CI matrices,
Dependabot, signed releases when available, and no remote code execution during
installation.

## Trust assumptions

- contract and validity code are trusted application code;
- maintainers review core adapters;
- test users understand that runtime safety controls remain necessary;
- local filesystem permissions protect bundles unless explicitly uploaded;
- model outputs and external service data are untrusted.

## Security requirements for new features

A feature needs a threat-model update when it:

- executes subprocesses or containers;
- accepts a remote bundle or trace;
- renders HTML;
- stores credentials;
- communicates with a hosted service;
- runs concurrently across processes;
- imports production data;
- automatically generates or executes contract code.
