# Initial repository security and hygiene audit

**Audit date:** 2026-08-19
**Scope:** files selected by `git ls-files --others --exclude-standard` before
the initial commit. Ignored build output and caches were not treated as source.

This is a bounded repository-hygiene audit, not a security certification or a
claim that regex scanning can find every secret.

## Commands and results

### Secrets, credentials, paths, and fixture data

The intended files were scanned with `rg` for private-key headers; AWS, GitHub,
OpenAI, and Slack token shapes; credential-like assignments; cookies; common
database connection strings; `/Users/`, named `/home/` directories, Windows user
directories, and the local username. The same path/token scan was run directly
against `tests/fixtures/failure_bundles/`.

```bash
git ls-files --others --exclude-standard -z | xargs -0 rg -l -i \
  -e '-----BEGIN (RSA |EC |OPENSSH |DSA )?PRIVATE KEY-----' \
  -e 'AKIA[0-9A-Z]{16}' -e 'ASIA[0-9A-Z]{16}' \
  -e 'gh[pousr]_[A-Za-z0-9_]{20,}' \
  -e 'github_pat_[A-Za-z0-9_]{20,}' -e 'sk-[A-Za-z0-9]{20,}' \
  -e 'xox[baprs]-[A-Za-z0-9-]{10,}' \
  -e '(api[_-]?key|client[_-]?secret|password|passwd|access[_-]?token|auth[_-]?token|cookie)[[:space:]]*[:=][[:space:]]*[A-Za-z0-9_./+:-]{12,}' \
  -e 'postgres(ql)?://[^[:space:]]+' -e 'mongodb(\+srv)?://[^[:space:]]+' \
  -e 'mysql://[^[:space:]]+' -e 'redis://[^[:space:]]+'

git ls-files --others --exclude-standard -z | xargs -0 rg -n \
  '/Users/|/home/[A-Za-z0-9._-]+|[A-Za-z]:\\Users\\|ericwallas'

rg -n -i -e '/Users/' -e '/private/var/' -e '/home/[A-Za-z0-9._-]+/' \
  -e 'ericwallas' -e 'AKIA[0-9A-Z]{16}' -e 'sk-[A-Za-z0-9]{20,}' \
  tests/fixtures/failure_bundles
```

The pre-documentation scans returned no matches. A final self-scan after adding
this audit page matched only the literal `mysql://`/`redis://` search expressions
shown above; that documented command was reviewed as a false positive. The
checked-in synthetic bundle is 64 KiB. No `gitleaks`, `detect-secrets`, or
`trufflehog` executable was installed, so no result from a specialized secret
scanner is claimed.

### Symlinks and oversized files

```bash
git ls-files --others --exclude-standard -z | \
  xargs -0 -I{} find '{}' -type l -print
git ls-files --others --exclude-standard -z | \
  xargs -0 -I{} find '{}' -type f -size +1M -print
```

Both commands returned no paths. The executable bits were inspected with `ls -l
scripts/*.sh scripts/*.py`: `scripts/check.sh` and `scripts/demo.sh` are
executable shell scripts; the Python acceptance script is intentionally invoked
through Python and is not executable.

### Direct runtime dependency licenses

Installed distribution metadata was queried with `importlib.metadata` for the
three direct runtime dependencies:

```text
pydantic 2.13.4: MIT
rich 15.0.0: MIT
typer 0.27.1: MIT
```

MIT licensing is compatible with this project's Apache-2.0 distribution. This
check covers direct runtime dependencies, not a legal opinion or an exhaustive
audit of every optional/transitive package.

### Metadata and security boundaries

- `LICENSE`, `NOTICE`, `pyproject.toml`, `CITATION.cff`, `SECURITY.md`,
  `CONTRIBUTING.md`, and `CODE_OF_CONDUCT.md` consistently identify Apache-2.0.
- Package and citation authorship uses the collective “Agent Effects
  contributors”; no individual or organization identity was invented.
- No repository URL is declared before a repository exists. Placeholder remote
  values appear only in the explicitly unexecuted remote-release procedure.
- Bundle documentation and CLI language describe unsigned hashes as
  integrity-checked and tamper-evident relative to the manifest. They explicitly
  disclaim author authentication, trusted provenance, and resistance to an
  attacker who regenerates the manifest.
- `bundle verify` and `bundle inspect` load portable data only. A regression test
  makes reproducer entry-point resolution fail if either command reaches it.
  `reproduce --dry-run` lists metadata without loading an entry point;
  `reproduce` is the explicit installed-code execution boundary.

### Generated and local-only content

The development lock file is retained for contributor/CI reproducibility while
runtime dependency ranges remain in `pyproject.toml`. Wheels, sdists, coverage,
built documentation, package metadata, virtual environments, caches, and raw
machine-specific validation transcripts are ignored. One small synthetic bundle
is retained as a test/documentation fixture. No remote was configured and no
package, release, tag, or repository was published during this audit.
