"""Canonical Agent Skill discovery, manifesting, and safe resource reads.

This module intentionally has no MCP transport dependency. It turns the repository's
canonical ``skills/<name>/`` tree into deterministic static entries that a later MCP
adapter can expose through the Skills extension.
"""

from __future__ import annotations

import hashlib
import json
import mimetypes
import re
from pathlib import Path
from typing import Any
from urllib.parse import quote

import yaml  # type: ignore[import-untyped]

from .models import SkillEntry, SkillResource

_NAME_RE = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
_MAX_SKILL_FILES = 512
_MAX_SKILL_BYTES = 16 * 1024 * 1024


class SkillCatalogError(ValueError):
    """Raised when canonical skill state is invalid or changes unexpectedly."""


def default_skills_root() -> Path:
    """Locate the canonical/packaged skill tree.

    Source checkouts author skills at repository-root ``skills/``. A future package
    build may derive that same tree into ``github_stars_contrib_mcp/_skills``; this
    lookup supports both without introducing a second authoring location.
    """

    package_root = Path(__file__).resolve().parents[1]
    packaged = package_root / "_skills"
    if packaged.is_dir():
        return packaged

    checkout = package_root.parent.parent / "skills"
    if checkout.is_dir():
        return checkout

    raise SkillCatalogError(
        "canonical Agent Skills tree is unavailable; expected packaged _skills/ "
        "or repository-root skills/"
    )


class SkillCatalog:
    """Immutable-in-use view of a static Agent Skills directory."""

    def __init__(self, root: Path | str | None = None) -> None:
        candidate = Path(root) if root is not None else default_skills_root()
        if candidate.is_symlink():
            raise SkillCatalogError(f"skills root must not be a symlink: {candidate}")
        if not candidate.is_dir():
            raise SkillCatalogError(f"skills root is not a directory: {candidate}")

        self.root = candidate.resolve(strict=True)
        self._entries = self._discover()
        self._by_uri = {entry.uri: entry for entry in self._entries}
        self._resources: dict[str, tuple[SkillEntry, SkillResource]] = {}
        for entry in self._entries:
            for resource in entry.resources:
                if resource.uri in self._resources:
                    raise SkillCatalogError(
                        f"duplicate skill resource URI: {resource.uri}"
                    )
                self._resources[resource.uri] = (entry, resource)

    def list(self) -> tuple[SkillEntry, ...]:
        """Return every canonical skill in deterministic URI order."""
        return self._entries

    def get(self, uri: str) -> SkillEntry:
        """Resolve a skill by its canonical ``SKILL.md`` URI."""
        try:
            return self._by_uri[uri]
        except KeyError as exc:
            raise SkillCatalogError(f"unknown skill URI: {uri}") from exc

    def read(self, uri: str) -> bytes:
        """Read one manifest-authorized resource and verify it has not drifted."""
        try:
            entry, resource = self._resources[uri]
        except KeyError as exc:
            raise SkillCatalogError(f"unknown skill resource URI: {uri}") from exc

        _assert_safe_file(resource.file_path, entry.root_path)
        data = resource.file_path.read_bytes()
        digest = _digest(data)
        if len(data) != resource.size or digest != resource.digest:
            raise SkillCatalogError(
                f"skill resource changed after manifest creation: {resource.uri}; "
                "refresh the skill entry before reading"
            )
        return data

    def _discover(self) -> tuple[SkillEntry, ...]:
        entries: list[SkillEntry] = []
        names: set[str] = set()

        for directory in sorted(self.root.iterdir(), key=lambda path: path.name):
            if directory.is_symlink():
                raise SkillCatalogError(
                    f"symlinked skill directories are not allowed: {directory}"
                )
            if not directory.is_dir():
                continue

            skill_file = directory / "SKILL.md"
            if not skill_file.is_file():
                continue

            entry = _build_entry(directory)
            if entry.name in names:
                raise SkillCatalogError(f"duplicate skill name: {entry.name}")
            names.add(entry.name)
            entries.append(entry)

        if not entries:
            raise SkillCatalogError(f"no Agent Skills found under {self.root}")

        return tuple(sorted(entries, key=lambda entry: entry.uri))


def _build_entry(skill_root: Path) -> SkillEntry:
    _assert_safe_file(skill_root / "SKILL.md", skill_root)
    skill_bytes = (skill_root / "SKILL.md").read_bytes()
    frontmatter = _parse_frontmatter(skill_bytes)
    name = _validate_frontmatter(frontmatter, skill_root.name)
    description = str(frontmatter["description"])

    resources: list[SkillResource] = []
    total_size = 0

    for path in sorted(skill_root.rglob("*"), key=lambda item: item.as_posix()):
        if path.is_symlink():
            raise SkillCatalogError(f"symlinks are not allowed in skills: {path}")
        if path.is_dir():
            continue
        if not path.is_file():
            raise SkillCatalogError(f"unsupported skill filesystem entry: {path}")

        _assert_safe_file(path, skill_root)
        relative = path.relative_to(skill_root).as_posix()
        data = path.read_bytes()
        total_size += len(data)
        resources.append(
            SkillResource(
                uri=_resource_uri(name, relative),
                relative_path=relative,
                digest=_digest(data),
                size=len(data),
                mime_type=_mime_type(path),
                file_path=path,
            )
        )

    if len(resources) > _MAX_SKILL_FILES:
        raise SkillCatalogError(
            f"skill {name!r} exceeds {_MAX_SKILL_FILES} files: {len(resources)}"
        )
    if total_size > _MAX_SKILL_BYTES:
        raise SkillCatalogError(
            f"skill {name!r} exceeds {_MAX_SKILL_BYTES} bytes: {total_size}"
        )

    skill_uri = _resource_uri(name, "SKILL.md")
    if not any(resource.uri == skill_uri for resource in resources):
        raise SkillCatalogError(f"skill {name!r} manifest does not contain SKILL.md")

    return SkillEntry(
        uri=skill_uri,
        name=name,
        description=description,
        frontmatter=frontmatter,
        resources=tuple(resources),
        root_path=skill_root.resolve(strict=True),
    )


def _parse_frontmatter(data: bytes) -> dict[str, Any]:
    try:
        text = data.decode("utf-8")
    except UnicodeDecodeError as exc:
        raise SkillCatalogError("SKILL.md must be valid UTF-8") from exc

    lines = text.splitlines()
    if not lines or lines[0] != "---":
        raise SkillCatalogError("SKILL.md must begin with YAML frontmatter")

    try:
        closing = lines.index("---", 1)
    except ValueError as exc:
        raise SkillCatalogError("SKILL.md frontmatter is not terminated") from exc

    try:
        loaded = yaml.safe_load("\n".join(lines[1:closing]))
    except yaml.YAMLError as exc:
        raise SkillCatalogError(f"invalid SKILL.md YAML frontmatter: {exc}") from exc

    if not isinstance(loaded, dict):
        raise SkillCatalogError("SKILL.md frontmatter must be a YAML mapping")
    if not all(isinstance(key, str) for key in loaded):
        raise SkillCatalogError("SKILL.md frontmatter keys must be strings")

    try:
        json.dumps(loaded)
    except (TypeError, ValueError) as exc:
        raise SkillCatalogError(
            "SKILL.md frontmatter must contain JSON-serializable values"
        ) from exc

    return dict(loaded)


def _validate_frontmatter(frontmatter: dict[str, Any], directory_name: str) -> str:
    name = frontmatter.get("name")
    description = frontmatter.get("description")

    if not isinstance(name, str):
        raise SkillCatalogError("SKILL.md frontmatter requires string field 'name'")
    if not (1 <= len(name) <= 64) or not _NAME_RE.fullmatch(name):
        raise SkillCatalogError(
            f"invalid Agent Skill name {name!r}; use 1-64 lowercase letters, "
            "numbers, and single hyphens"
        )
    if name != directory_name:
        raise SkillCatalogError(
            f"skill name {name!r} must match parent directory {directory_name!r}"
        )

    if not isinstance(description, str) or not description.strip():
        raise SkillCatalogError(
            "SKILL.md frontmatter requires non-empty string field 'description'"
        )
    if len(description) > 1024:
        raise SkillCatalogError("Agent Skill description must be <= 1024 characters")

    compatibility = frontmatter.get("compatibility")
    if compatibility is not None and (
        not isinstance(compatibility, str)
        or not compatibility
        or len(compatibility) > 500
    ):
        raise SkillCatalogError(
            "Agent Skill compatibility must be a non-empty string <= 500 characters"
        )

    metadata = frontmatter.get("metadata")
    if metadata is not None:
        if not isinstance(metadata, dict) or not all(
            isinstance(key, str) and isinstance(value, str)
            for key, value in metadata.items()
        ):
            raise SkillCatalogError(
                "Agent Skill metadata must map string keys to string values"
            )

    allowed_tools = frontmatter.get("allowed-tools")
    if allowed_tools is not None and not isinstance(allowed_tools, str):
        raise SkillCatalogError("Agent Skill allowed-tools must be a string")

    return name


def _resource_uri(skill_name: str, relative_path: str) -> str:
    encoded_path = "/".join(
        quote(segment, safe="-._~") for segment in relative_path.split("/")
    )
    return f"skill://{skill_name}/{encoded_path}"


def _digest(data: bytes) -> str:
    return f"sha256:{hashlib.sha256(data).hexdigest()}"


def _mime_type(path: Path) -> str:
    guessed, _ = mimetypes.guess_type(path.name)
    return guessed or "application/octet-stream"


def _assert_safe_file(path: Path, skill_root: Path) -> None:
    root = skill_root.resolve(strict=True)
    try:
        relative = path.relative_to(skill_root)
    except ValueError as exc:
        raise SkillCatalogError(f"resource escapes skill root: {path}") from exc

    current = skill_root
    for segment in relative.parts:
        current = current / segment
        if current.is_symlink():
            raise SkillCatalogError(f"symlinks are not allowed in skills: {current}")

    try:
        resolved = path.resolve(strict=True)
    except FileNotFoundError as exc:
        raise SkillCatalogError(f"skill resource does not exist: {path}") from exc

    if resolved != root and root not in resolved.parents:
        raise SkillCatalogError(f"resource escapes skill root: {path}")
    if not resolved.is_file():
        raise SkillCatalogError(f"skill resource is not a regular file: {path}")
