# Public repository and prerelease runbook

This runbook records the authorized GitHub publication path for
`eschmidt01/agent-effects-testkit`. It never publishes to PyPI or TestPyPI.

## 1. Create an empty public repository

Create `eschmidt01/agent-effects-testkit` in the GitHub UI with no generated
README, license, or `.gitignore`, or run:

```bash
gh repo create eschmidt01/agent-effects-testkit --public \
  --description "Property-based transaction testing for AI agents with real-world side effects. Inject commit-boundary failures, assert business invariants, and reduce failures into reproducible regression cases."
```

## 2. Add and verify `origin`

```bash
git remote add origin https://github.com/eschmidt01/agent-effects-testkit.git
git remote -v
```

## 3. Push the candidate commit

```bash
git push -u origin main
```

## 4. Observe the exact GitHub Actions run

```bash
gh run list --repo eschmidt01/agent-effects-testkit --branch main --limit 5
gh run watch <RUN_ID> --repo eschmidt01/agent-effects-testkit --exit-status
```

Record both values after the run passes:

```text
Commit SHA: <FULL_COMMIT_SHA>
Workflow URL: https://github.com/eschmidt01/agent-effects-testkit/actions/runs/<RUN_ID>
```

Do not treat a local matrix as remote-CI success.

## 5. Tag only the revision that passed

Confirm `git rev-parse HEAD` equals `<FULL_COMMIT_SHA>`, then create and push an
annotated tag:

```bash
git tag -a v0.1.0a1 <FULL_COMMIT_SHA> \
  -m "Agent Effects Testkit v0.1.0a1"
git push origin v0.1.0a1
```

## 6. Create a GitHub prerelease

Use the `0.1.0a1` section of `CHANGELOG.md` as the release notes:

```bash
gh release create v0.1.0a1 \
  --repo eschmidt01/agent-effects-testkit \
  --prerelease \
  --title "Agent Effects Testkit v0.1.0a1 — Experimental Public Alpha" \
  --notes-file <PREPARED_RELEASE_NOTES_FILE>
```

## 7. Attach distributions only with separate authorization

Download or rebuild artifacts from the tagged revision, verify them with `twine
check`, and attach the wheel and sdist only after explicit package-artifact
publication authorization:

```bash
gh release upload v0.1.0a1 dist/*.whl dist/*.tar.gz \
  --repo eschmidt01/agent-effects-testkit
```

This procedure does not publish to PyPI or TestPyPI. Either publication requires
separate authorization and a separate release procedure.
