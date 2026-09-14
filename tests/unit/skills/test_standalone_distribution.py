"""Contracts for standalone Agent Skills distribution without behavior copies."""

from __future__ import annotations

import json
import tomllib
from pathlib import Path

from github_stars_contrib_mcp.skills import SkillCatalog

ROOT = Path(__file__).resolve().parents[3]


def _plugin() -> dict[str, object]:
    return json.loads((ROOT / "plugin.json").read_text(encoding="utf-8"))


def test_agent_plugin_metadata_tracks_project_and_canonical_skills() -> None:
    plugin = _plugin()
    project = tomllib.loads((ROOT / "pyproject.toml").read_text(encoding="utf-8"))[
        "project"
    ]
    skill_names = {entry.name for entry in SkillCatalog(ROOT / "skills").list()}
    keywords = set(plugin["keywords"])

    assert plugin["$schema"] == (
        "https://agent-plugins.org/schemas/1.0.0/plugin.schema.json"
    )
    assert plugin["name"] == "github-stars-contributions"
    assert plugin["version"] == project["version"]
    assert plugin["repository"] == (
        "https://github.com/svg153/github-stars-contrib-mcp-server"
    )
    assert skill_names == {
        "discover-my-contributions",
        "publish-approved",
        "review-candidates",
        "sync-source",
    }
    assert skill_names <= keywords


def test_standalone_distribution_does_not_duplicate_skill_authoring_tree() -> None:
    """Agent Plugin discovery consumes root skills/ directly, not copied adapters."""

    forbidden_runtime_copies = (
        ROOT / ".agents" / "skills",
        ROOT / ".claude" / "skills",
        ROOT / ".github" / "skills",
        ROOT / ".codex" / "skills",
    )

    assert all(not path.exists() for path in forbidden_runtime_copies)
    assert sorted(path.name for path in (ROOT / "skills").iterdir() if path.is_dir()) == [
        "discover-my-contributions",
        "publish-approved",
        "review-candidates",
        "sync-source",
    ]
