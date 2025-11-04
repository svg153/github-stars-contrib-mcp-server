#!/usr/bin/env python
"""
Local quality check runner: lint, format, security, and tests.
Mimics CI/CD pipeline but runs locally with fast feedback loop.

Usage:
    python scripts/quality_check.py              # Run all checks
    python scripts/quality_check.py --lint       # Only lint
    python scripts/quality_check.py --security   # Only security
    python scripts/quality_check.py --tests      # Only tests
    python scripts/quality_check.py --fix        # Fix lint issues
"""

import argparse
import subprocess
import sys
from pathlib import Path

# Root directory
ROOT = Path(__file__).parent.parent

# Directories to check
SRC_DIR = ROOT / "src"
TESTS_DIR = ROOT / "tests"


def run_cmd(cmd: list[str], description: str, allow_fail: bool = False) -> bool:
    """Run a command and report status."""
    print(f"\n{'=' * 80}")
    print(f"🔵 {description}")
    print(f"{'=' * 80}")
    print(f"$ {' '.join(cmd)}\n")

    result = subprocess.run(cmd, cwd=ROOT)

    if result.returncode != 0 and not allow_fail:
        print(f"\n❌ {description} FAILED")
        return False

    if result.returncode == 0:
        print(f"\n✅ {description} PASSED")
    else:
        print(f"\n⚠️  {description} completed with issues (non-blocking)")

    return True


def lint_check() -> bool:
    """Run ruff linting checks."""
    return run_cmd(
        ["ruff", "check", str(SRC_DIR), str(TESTS_DIR)],
        "Lint Check (ruff check)",
    )


def format_check() -> bool:
    """Check code formatting."""
    return run_cmd(
        ["ruff", "format", "--check", str(SRC_DIR), str(TESTS_DIR)],
        "Format Check (ruff format --check)",
    )


def format_fix() -> bool:
    """Fix code formatting."""
    return run_cmd(
        ["ruff", "format", str(SRC_DIR), str(TESTS_DIR)],
        "Format Fix (ruff format)",
    )


def lint_fix() -> bool:
    """Fix lint issues."""
    return run_cmd(
        ["ruff", "check", "--fix", str(SRC_DIR), str(TESTS_DIR)],
        "Lint Fix (ruff check --fix)",
    )


def type_check() -> bool:
    """Run type checking (both pyright and mypy)."""
    results = []

    # Pyright (stricter)
    results.append(
        run_cmd(
            ["pyright", str(SRC_DIR), str(TESTS_DIR)],
            "Type Check - Pyright",
            allow_fail=True,
        )
    )

    # MyPy (complementary)
    results.append(
        run_cmd(
            ["mypy", "--strict", str(SRC_DIR), str(TESTS_DIR)],
            "Type Check - MyPy (strict)",
            allow_fail=True,
        )
    )

    return all(results)


def security_bandit() -> bool:
    """Run bandit security scanner."""
    return run_cmd(
        [
            "bandit",
            "-c",
            str(ROOT / "pyproject.toml"),
            "-r",
            str(SRC_DIR),
            str(TESTS_DIR),
            "-ll",
        ],
        "Security Scan - Bandit (Python code)",
        allow_fail=True,
    )


def security_safety() -> bool:
    """Run safety vulnerability scanner."""
    return run_cmd(
        ["safety", "check"],
        "Security Scan - Safety (Dependencies)",
        allow_fail=True,
    )


def security_api_safety() -> bool:
    """Run custom API safety check."""
    return run_cmd(
        ["python", str(ROOT / ".github" / "hooks" / "check-api-safety.py")],
        "Security Scan - API Safety (Stars API patterns)",
        allow_fail=True,
    )


def pre_commit_run() -> bool:
    """Run pre-commit hooks."""
    return run_cmd(
        ["pre-commit", "run", "--all-files"],
        "Pre-commit Hooks",
    )


def tests_run() -> bool:
    """Run pytest."""
    return run_cmd(
        ["pytest", "-v"],
        "Run Tests (pytest)",
    )


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Local quality check runner",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python scripts/quality_check.py              # All checks
  python scripts/quality_check.py --lint       # Only lint
  python scripts/quality_check.py --fix        # Fix issues
  python scripts/quality_check.py --security   # Security only
        """,
    )

    parser.add_argument("--lint", action="store_true", help="Run lint checks only")
    parser.add_argument("--format", action="store_true", help="Run format check only")
    parser.add_argument("--fix", action="store_true", help="Fix lint and format issues")
    parser.add_argument("--type", action="store_true", help="Run type check only")
    parser.add_argument(
        "--security", action="store_true", help="Run security scans only"
    )
    parser.add_argument("--tests", action="store_true", help="Run tests only")
    parser.add_argument("--pre-commit", action="store_true", help="Run pre-commit only")

    args = parser.parse_args()

    # If --fix, run fixes and exit
    if args.fix:
        print("🔧 Fixing issues...\n")
        results = [
            lint_fix(),
            format_fix(),
        ]
        return 0 if all(results) else 1

    # Run selected checks
    results = []

    if args.lint or not any(
        [args.lint, args.format, args.type, args.security, args.tests, args.pre_commit]
    ):
        results.append(lint_check())

    if args.format or not any(
        [args.lint, args.format, args.type, args.security, args.tests, args.pre_commit]
    ):
        results.append(format_check())

    if args.type or not any(
        [args.lint, args.format, args.type, args.security, args.tests, args.pre_commit]
    ):
        results.append(type_check())

    if args.security or not any(
        [args.lint, args.format, args.type, args.security, args.tests, args.pre_commit]
    ):
        results.append(security_bandit())
        results.append(security_safety())
        results.append(security_api_safety())

    if args.pre_commit or not any(
        [args.lint, args.format, args.type, args.security, args.tests, args.pre_commit]
    ):
        results.append(pre_commit_run())

    if args.tests or not any(
        [args.lint, args.format, args.type, args.security, args.tests, args.pre_commit]
    ):
        results.append(tests_run())

    # Summary
    print(f"\n{'=' * 80}")
    print("📊 SUMMARY")
    print(f"{'=' * 80}")
    passed = sum(results)
    total = len(results)
    print(f"Passed: {passed}/{total}")

    if all(results):
        print("✅ All checks passed!")
        return 0
    else:
        print("❌ Some checks failed")
        return 1


if __name__ == "__main__":
    sys.exit(main())
