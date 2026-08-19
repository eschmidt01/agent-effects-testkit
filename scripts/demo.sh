#!/usr/bin/env bash
set -euo pipefail

failure_dir="${1:-.agent-effects/failures}"

set +e
agent-effects demo --agent naive --output "$failure_dir"
naive_status=$?
set -e

if [[ "$naive_status" -ne 1 ]]; then
  echo "expected naive demo to fail with exit code 1; got $naive_status" >&2
  exit 2
fi

agent-effects demo --agent idempotent --output "$failure_dir"
agent-effects demo --agent reconcile --output "$failure_dir"
