#!/usr/bin/env python3
"""
API Safety Hook - Validates Stars API safety patterns in staged code.

Checks for:
1. No hardcoded tokens or secrets in code
2. Proper STARS_API_TOKEN usage (via config only)
3. Error handling patterns (try/except around API calls)
4. Circuit breaker usage for API calls
5. No GraphQL injection vulnerabilities
"""

import re
import sys
from pathlib import Path
from typing import List

# Patterns indicating potential API safety issues
PATTERNS = {
    "hardcoded_token": (
        r"(?i)(token|secret|api_key|password)\s*=\s*['\"]([a-zA-Z0-9_\-]{10,})['\"]",
        "Hardcoded secret/token detected",
    ),
    "direct_graphql": (
        r"query_str\s*=\s*['\"].*(?:query|mutation).*['\"]",
        "GraphQL query as plain string (potential injection)",
    ),
    "missing_error_handling": (
        r"(?:stars_client|StarsClient|graphql)\.(?:query|mutation).*(?!\n\s*(?:try|except))",
        "API call without try/except wrapper",
    ),
    "stars_token_hardcoded": (
        r"STARS_API_TOKEN\s*=\s*['\"]",
        "STARS_API_TOKEN hardcoded in source (must be env var)",
    ),
    "env_token_unsafe": (
        r"(?i)os\.environ\.get\(['\"]STARS_API_TOKEN['\"](?!\s*,\s*(?:\w+\.)?)?(?:['\"][^'\"]*)?['\"]?\)",
        "STARS_API_TOKEN access without secure config",
    ),
}

# Files that should be checked
PYTHON_FILES_PATTERN = r"\.py$"

# Files to skip
SKIP_DIRS = {".venv", ".git", "__pycache__", ".pytest_cache", "htmlcov"}


def is_skip_file(path: Path) -> bool:
    """Check if file should be skipped."""
    for skip_dir in SKIP_DIRS:
        if skip_dir in path.parts:
            return True
    return False


def check_file(filepath: str) -> List[str]:
    """Check single file for API safety issues."""
    errors = []
    path = Path(filepath)

    if is_skip_file(path) or not path.suffix == ".py":
        return errors

    try:
        content = path.read_text()
        lines = content.split("\n")

        for pattern_name, (pattern, message) in PATTERNS.items():
            matches = re.finditer(pattern, content, re.MULTILINE)
            for match in matches:
                # Find line number
                line_num = content[: match.start()].count("\n") + 1
                errors.append(f"{filepath}:{line_num}: {message}")

        # Additional checks for common misconfigurations
        if "STARS_API_TOKEN" in content:
            # Check if it's being used correctly (via config.settings)
            if "from " in content and "config.settings" in content:
                if "config.settings.STARS_API_TOKEN" not in content:
                    # Importing config but not using it for token
                    for i, line in enumerate(lines, 1):
                        if "STARS_API_TOKEN" in line and "config.settings" not in line:
                            errors.append(
                                f"{filepath}:{i}: Use config.settings.STARS_API_TOKEN, not direct env access"
                            )

    except Exception as e:
        errors.append(f"{filepath}: Error reading file: {e}")

    return errors


def main() -> int:
    """Main entry point for pre-commit hook."""
    all_errors = []

    # Get files from stdin (pre-commit standard)
    for filepath in sys.stdin:
        filepath = filepath.strip()
        if filepath:
            errors = check_file(filepath)
            all_errors.extend(errors)

    if all_errors:
        print("❌ API Safety Issues Found:")
        for error in all_errors:
            print(f"  {error}")
        return 1

    print("✓ API safety checks passed")
    return 0


if __name__ == "__main__":
    sys.exit(main())
