.PHONY: install test property lint format typecheck coverage build demo check clean

install:
	python -m pip install -e '.[dev]'

test:
	pytest

property:
	pytest tests/test_hypothesis_refund.py

lint:
	ruff check .

format:
	ruff format .

typecheck:
	mypy

coverage:
	pytest --cov=agent_effects --cov-report=term-missing --cov-report=xml

build:
	python -m build

demo:
	agent-effects demo --agent naive || test $$? -eq 1
	agent-effects demo --agent idempotent
	agent-effects demo --agent reconcile

check: lint typecheck coverage
	python -m compileall -q src tests examples

clean:
	rm -rf .pytest_cache .mypy_cache .ruff_cache .coverage htmlcov build dist site
	find . -type d -name __pycache__ -prune -exec rm -rf {} +
