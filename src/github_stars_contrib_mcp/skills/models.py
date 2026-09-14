"""Protocol-independent models for canonical Agent Skills."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any


@dataclass(frozen=True, slots=True)
class SkillResource:
    """One immutable file in a skill manifest."""

    uri: str
    relative_path: str
    digest: str
    size: int
    mime_type: str
    file_path: Path


@dataclass(frozen=True, slots=True)
class SkillEntry:
    """A complete static skill entry derived from canonical repository bytes."""

    uri: str
    name: str
    description: str
    frontmatter: dict[str, Any]
    resources: tuple[SkillResource, ...]
    root_path: Path

    def resource(self, uri: str) -> SkillResource | None:
        """Return the manifest resource matching *uri*, if present."""
        return next((resource for resource in self.resources if resource.uri == uri), None)
