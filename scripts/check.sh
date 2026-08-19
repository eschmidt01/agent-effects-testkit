#!/usr/bin/env bash
set -euo pipefail

python -m compileall -q src tests examples
pytest
ruff check .
ruff format --check .
mypy --strict src tests
mkdocs build --strict
