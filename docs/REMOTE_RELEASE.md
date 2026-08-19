# Remote setup and prerelease procedure

These commands are prepared for use only after the repository owner explicitly
authorizes external publication. They have not been executed. Replace every
angle-bracketed placeholder; do not infer an owner or organization.

## 1. Create an empty public repository

Create `<GITHUB_OWNER>/<REPOSITORY_NAME>` in the GitHub UI with no generated
README, license, or `.gitignore`, or run:

```bash
gh repo create <GITHUB_OWNER>/<REPOSITORY_NAME> --public \
  --description "Commit-aware side-effect testing for AI agents"
```

## 2. Add and verify `origin`

```bash
git remote add origin https://github.com/<GITHUB_OWNER>/<REPOSITORY_NAME>.git
git remote -v
```

## 3. Push the candidate commit

```bash
git push -u origin main
```

## 4. Observe the exact GitHub Actions run

```bash
gh run list --repo <GITHUB_OWNER>/<REPOSITORY_NAME> --branch main --limit 5
gh run watch <RUN_ID> --repo <GITHUB_OWNER>/<REPOSITORY_NAME> --exit-status
```

Record both values after the run passes:

```text
Commit SHA: <FULL_COMMIT_SHA>
Workflow URL: https://github.com/<GITHUB_OWNER>/<REPOSITORY_NAME>/actions/runs/<RUN_ID>
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
  --repo <GITHUB_OWNER>/<REPOSITORY_NAME> \
  --prerelease \
  --title "Agent Effects Testkit v0.1.0a1" \
  --notes-file <PREPARED_RELEASE_NOTES_FILE>
```

## 7. Attach distributions only with separate authorization

Download or rebuild artifacts from the tagged revision, verify them with `twine
check`, and attach the wheel and sdist only after explicit package-artifact
publication authorization:

```bash
gh release upload v0.1.0a1 dist/*.whl dist/*.tar.gz \
  --repo <GITHUB_OWNER>/<REPOSITORY_NAME>
```

This procedure does not publish to PyPI or TestPyPI. Either publication requires
separate authorization and a separate release procedure.
