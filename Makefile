.PHONY: install test run format lint lint-fix run-env venv pre-commit-install pre-commit-run

install:
	pip install -e .[dev]

test:
	pytest -q

run:
	python -m github_stars_contrib_mcp.server

run-env:
	@bash -lc 'if [ -f .env ]; then set -a; source .env; set +a; else echo "[warn] .env not found; continuing with current env"; fi; \
	 if [ -f .venv/bin/activate ]; then source .venv/bin/activate; fi; \
	 python -m github_stars_contrib_mcp.server'

venv:
	python -m venv .venv

format:
	ruff format src

lint:
	ruff check --quiet .

lint-fix:
	ruff check --fix .

pre-commit-install:
	pre-commit install

pre-commit-run:
	pre-commit run --all-files

# Run all tests (unit + integration), requiring .env.local to exist and be sourced.
.PHONY: test-all
test-all:
	@bash -lc 'if [ ! -f .env.local ]; then echo "[error] .env.local not found; aborting. Create it with required env (e.g., STARS_API_TOKEN)." >&2; exit 1; fi; \
	 set -a; source .env.local; set +a; \
	 if [ -f .venv/bin/activate ]; then source .venv/bin/activate; fi; \
	 pytest -q'
