#!/usr/bin/env python3
"""
Smart Pre-commit Hook Filter - Conditionally runs expensive checks.

Rules:
- Skip hooks on merge commits (already tested)
- Skip on tag pushes (assumed stable)
- Run type checking only on changed .py files
- Batch file operations for efficiency
"""

import os
import subprocess
import sys
from pathlib import Path


def get_changed_files() -> set[str]:
    """Get list of staged files."""
    try:
        result = subprocess.run(
            ["git", "diff", "--cached", "--name-only"],
            capture_output=True,
            text=True,
        )
        return (
            set(result.stdout.strip().split("\n")) if result.stdout.strip() else set()
        )
    except Exception as e:
        print(f"Warning: Could not get changed files: {e}")
        return set()


def get_python_files(files: set[str]) -> set[str]:
    """Filter to only Python files."""
    return {f for f in files if f.endswith(".py")}


def is_merge_commit() -> bool:
    """Check if this is a merge commit."""
    merge_head_path = Path(".git/MERGE_HEAD")
    return merge_head_path.exists()


def is_tag_push() -> bool:
    """Check if we're on a tag."""
    try:
        result = subprocess.run(
            ["git", "describe", "--tags", "--exact-match"],
            capture_output=True,
            text=True,
        )
        return result.returncode == 0
    except Exception:
        return False


def should_skip() -> bool:
    """Determine if hooks should be skipped."""
    # Skip on merge commits
    if is_merge_commit():
        print("ℹ️  Skipping expensive checks on merge commit")
        return True

    # Skip on tags
    if is_tag_push():
        print("ℹ️  Skipping expensive checks on tag")
        return True

    return False


def get_import_files(py_files: set[str]) -> set[str]:
    """Get files that might be imports (for cascading type check)."""
    result = py_files.copy()
    for py_file in py_files:
        try:
            path = Path(py_file)
            if path.exists():
                content = path.read_text()
                if "from " in content or "import " in content:
                    # Add commonly imported modules
                    if "src/github_stars_contrib_mcp/" in py_file:
                        # Check if it's in tools, utils, or models
                        for prefix in ["tools", "utils", "models", "config", "domain"]:
                            if prefix in py_file:
                                # Re-run type check on main modules
                                result.add(
                                    f"src/github_stars_contrib_mcp/{prefix}/*.py"
                                )
        except Exception as e:
            print(f"Warning: Could not process {py_file}: {e}")
    return result


def filter_expensive_hooks(hook_name: str, file_list: set[str]) -> bool:
    """
    Determine if expensive hook should run.

    Returns:
        bool: True if hook should run, False to skip
    """
    if not file_list:
        return False

    # Type checking: run if Python files changed
    if hook_name == "type-check":
        py_files = get_python_files(file_list)
        if not py_files:
            print(f"⊘ {hook_name}: No Python files changed, skipping")
            return False
        return True

    # Format/lint: run on all file changes
    if hook_name in ["ruff", "ruff-format"]:
        py_files = get_python_files(file_list)
        return bool(py_files)

    return True


def main() -> int:
    """Main filter logic."""
    if should_skip():
        return 0

    changed_files = get_changed_files()
    if not changed_files:
        print("ℹ️  No files changed")
        return 0

    hook_name = os.environ.get("PRE_COMMIT_HOOK_NAME", "unknown")

    if not filter_expensive_hooks(hook_name, changed_files):
        return 0

    # Write filtered files to stdout for next stage
    for f in changed_files:
        print(f)

    return 0


if __name__ == "__main__":
    sys.exit(main())
