#!/usr/bin/env python3
"""Lightweight static safety checks for Stars API related Python changes."""

import re
import sys
from pathlib import Path

PATTERNS = {
    "hardcoded_token": (
        r"(?i)(token|secret|api_key|password)\s*=\s*['\"]([a-zA-Z0-9_\-]{10,})['\"]",
        "Hardcoded secret/token detected",
    ),
    "direct_graphql": (
        r"query_str\s*=\s*['\"].*(?:query|mutation).*['\"]",
        "GraphQL query as plain string (potential injection)",
    ),
    "stars_token_hardcoded": (
        r"STARS_API_TOKEN\s*=\s*['\"]",
        "STARS_API_TOKEN hardcoded in source (must be an environment/config value)",
    ),
}

SKIP_DIRS = {".venv", ".git", "__pycache__", ".pytest_cache", "htmlcov"}


def is_skip_file(path: Path) -> bool:
    return bool(SKIP_DIRS.intersection(path.parts))


def check_file(filepath: str) -> list[str]:
    path = Path(filepath)
    if is_skip_file(path) or path.suffix != ".py":
        return []

    try:
        content = path.read_text(encoding="utf-8")
    except OSError as exc:
        return [f"{filepath}: Error reading file: {exc}"]

    errors: list[str] = []
    for _pattern_name, (pattern, message) in PATTERNS.items():
        for match in re.finditer(pattern, content, re.MULTILINE):
            line_num = content[: match.start()].count("\n") + 1
            errors.append(f"{filepath}:{line_num}: {message}")
    return errors


def main() -> int:
    files = [line.strip() for line in sys.stdin if line.strip()]
    errors = [error for filepath in files for error in check_file(filepath)]
    if errors:
        print("API safety issues found:")
        for error in errors:
            print(f"  {error}")
        return 1
    print("API safety checks passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
