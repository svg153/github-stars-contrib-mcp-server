
.PHONY: install test run format lint lint-fix run-env

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

format:
	ruff format src

lint:
	ruff check src

lint-fix:
	ruff check --fix src
