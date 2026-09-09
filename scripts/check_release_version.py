#!/usr/bin/env python3
"""Validate that a canonical release tag matches pyproject.toml."""

from __future__ import annotations

import argparse
from pathlib import Path

from github_stars_contrib_mcp.release_version import package_version_from, validate_tag

ROOT = Path(__file__).resolve().parent.parent
DEFAULT_PYPROJECT = ROOT / "pyproject.toml"


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("tag", help="Canonical release tag, for example v0.3.1")
    parser.add_argument(
        "--pyproject",
        type=Path,
        default=DEFAULT_PYPROJECT,
        help="Path to pyproject.toml",
    )
    args = parser.parse_args()

    package_version = package_version_from(args.pyproject)
    try:
        validate_tag(args.tag, package_version)
    except ValueError as exc:
        parser.error(str(exc))
    print(package_version)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
