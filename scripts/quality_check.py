#!/usr/bin/env python3
"""Run the same core quality checks used by CI from a local checkout."""

from __future__ import annotations

import argparse
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def run(command: list[str], label: str, *, optional: bool = False) -> bool:
    print(f"\n== {label} ==")
    result = subprocess.run(command, cwd=ROOT, check=False)
    if result.returncode and optional:
        print(f"warning: {label} reported issues")
        return True
    return result.returncode == 0


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--fix", action="store_true")
    parser.add_argument("--security", action="store_true")
    parser.add_argument("--type", action="store_true")
    parser.add_argument("--tests", action="store_true")
    args = parser.parse_args()

    if args.fix:
        checks = [
            run(["ruff", "check", "--fix", "."], "Ruff fixes"),
            run(["ruff", "format", "."], "Ruff format"),
        ]
        return 0 if all(checks) else 1

    selected = args.security or args.type or args.tests
    checks: list[bool] = []
    if not selected:
        checks.extend(
            [
                run(["ruff", "check", "."], "Ruff lint"),
                run(["ruff", "format", "--check", "."], "Ruff format check"),
                run(["pre-commit", "run", "--all-files"], "Pre-commit"),
                run(["pytest", "-q"], "Pytest"),
            ]
        )
    if args.type:
        checks.extend(
            [
                run(["pyright", "src", "tests"], "Pyright", optional=True),
                run(["mypy", "src"], "Mypy", optional=True),
            ]
        )
    if args.security:
        checks.extend(
            [
                run(["bandit", "-c", "pyproject.toml", "-r", "src"], "Bandit"),
                run(["safety", "check"], "Safety", optional=True),
            ]
        )
    if args.tests:
        checks.append(run(["pytest", "-q"], "Pytest"))
    return 0 if all(checks) else 1


if __name__ == "__main__":
    raise SystemExit(main())
