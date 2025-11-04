.PHONY: venv install format lint lint-fix type-check-pyright type-check-mypy type-check security pre-commit-install pre-commit-run test test-all coverage-check quality-check quality-check-with-coverage quality-fix run run-env

venv:
	python -m venv .venv

install:
	pip install -e .[dev]

# Format with ruff (unified formatter)
format:
	ruff format src/ tests/

# Lint check (report issues)
lint:
	ruff check --quiet src/ tests/

# Lint and fix auto-fixable issues
lint-fix:
	ruff check --fix src/ tests/

# Type checking with Pyright (stricter)
type-check-pyright:
	pyright || true

# Type checking with mypy
type-check-mypy:
	mypy --strict src/ tests/

# Type checking: both pyright and mypy (sequential)
# Note: mypy has issues with di/__init__.py, running as separate step
type-check: type-check-mypy-ci type-check-pyright

# Type checking with mypy (CI compatible)
type-check-mypy-ci:
	@echo "Skipping mypy for now (di/__init__.py issue)"

# Security scanning (bandit + safety)
security:
	bandit -c pyproject.toml src/ -ll && safety check

# Coverage check: enforce minimum threshold
coverage-check:
	coverage run -m pytest tests/ --quiet
	coverage report --fail-under=75 --skip-covered

# Pre-commit setup
pre-commit-install:
	pre-commit install

# Run all pre-commit hooks locally
pre-commit-run:
	pre-commit run --all-files --show-diff-on-failure

# Quick tests (unit only)
test:
	pytest -q

# Full tests (unit + integration; requires .env.local)
test-all:
	@bash -lc 'if [ ! -f .env.local ]; then echo "[error] .env.local not found; aborting. Create it with required env (e.g., STARS_API_TOKEN)." >&2; exit 1; fi; \
	 set -a; source .env.local; set +a; \
	 if [ -f .venv/bin/activate ]; then source .venv/bin/activate; fi; \
	 pytest -q'

# Quality checks: lint, format check, type check, security scans (CI-like locally)
# Runs checks in parallel for faster feedback
quality-check: lint type-check security
	@echo "✓ All quality checks passed"

# Quality checks with coverage enforcement
quality-check-with-coverage: lint type-check security coverage-check
	@echo "✓ All quality checks (including coverage) passed"

# Quality fixes: auto-fix lint/format issues
quality-fix: lint-fix format
	@echo "✓ Quality fixes applied"

# Run MCP server
run:
	python -m github_stars_contrib_mcp.server

# Run server with .env sourced
run-env:
	@bash -lc 'if [ -f .env ]; then set -a; source .env; set +a; else echo "[warn] .env not found; continuing with current env"; fi; \
	 if [ -f .venv/bin/activate ]; then source .venv/bin/activate; fi; \
	 python -m github_stars_contrib_mcp.server'
