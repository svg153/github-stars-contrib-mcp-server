"""Release-tag and package-version validation."""

from __future__ import annotations

import tomllib
from pathlib import Path


def normalize_tag(tag: str) -> str:
    value = tag.strip()
    if value.startswith("refs/tags/"):
        value = value.removeprefix("refs/tags/")
    if value.startswith("v"):
        value = value[1:]
    return value


def canonical_tag(tag: str) -> str:
    value = tag.strip()
    if value.startswith("refs/tags/"):
        value = value.removeprefix("refs/tags/")
    return value


def package_version_from(path: Path) -> str:
    data = tomllib.loads(path.read_text(encoding="utf-8"))
    version = data.get("project", {}).get("version")
    if not isinstance(version, str) or not version.strip():
        raise ValueError("pyproject.toml does not contain a non-empty project.version")
    return version.strip()


def validate_tag(tag: str, package_version: str) -> None:
    release_tag = canonical_tag(tag)
    expected = f"v{package_version}"
    if release_tag != expected:
        raise ValueError(
            f"release tag must be exactly {expected!r} for package version "
            f"{package_version!r}; got {tag!r}"
        )
