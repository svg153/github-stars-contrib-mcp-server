"""Security and integrity contract tests for MCP-served Agent Skills."""

from __future__ import annotations

from pathlib import Path

import pytest

from github_stars_contrib_mcp.skills import SkillCatalog, SkillCatalogError, SkillsExtension


def _write_skill(
    root: Path,
    name: str,
    *,
    declared_name: str | None = None,
    description: str = "Deterministic test skill.",
    extra_frontmatter: str = "",
) -> Path:
    skill = root / name
    skill.mkdir(parents=True)
    (skill / "SKILL.md").write_text(
        "---\n"
        f"name: {declared_name or name}\n"
        f"description: {description}\n"
        f"{extra_frontmatter}"
        "---\n\n"
        "# Test skill\n",
        encoding="utf-8",
    )
    return skill


def test_encoded_traversal_and_unlisted_resource_aliases_fail_closed(
    tmp_path: Path,
) -> None:
    _write_skill(tmp_path, "demo-skill")
    catalog = SkillCatalog(tmp_path)

    for uri in (
        "skill://demo-skill/%2e%2e/outside.txt",
        "skill://demo-skill/%2E%2E/outside.txt",
        "skill://demo-skill/references/%2Fetc%2Fpasswd",
        "skill://demo-skill/references/..%2Foutside.txt",
    ):
        with pytest.raises(SkillCatalogError, match="unknown skill resource URI"):
            catalog.read(uri)


def test_duplicate_declared_identity_across_directories_fails_closed(
    tmp_path: Path,
) -> None:
    _write_skill(tmp_path, "alpha")
    _write_skill(tmp_path, "beta", declared_name="alpha")

    with pytest.raises(SkillCatalogError, match="must match parent directory"):
        SkillCatalog(tmp_path)


def test_refresh_changes_integrity_metadata_after_canonical_bytes_change(
    tmp_path: Path,
) -> None:
    skill = _write_skill(tmp_path, "demo-skill")
    uri = "skill://demo-skill/SKILL.md"
    catalog = SkillCatalog(tmp_path)
    before = catalog.get(uri).resource(uri)
    assert before is not None

    with (skill / "SKILL.md").open("a", encoding="utf-8") as handle:
        handle.write("\nChanged canonical bytes.\n")

    with pytest.raises(SkillCatalogError, match="changed after manifest creation"):
        catalog.read(uri)

    refreshed = SkillCatalog(tmp_path)
    after = refreshed.get(uri).resource(uri)
    assert after is not None
    assert after.digest != before.digest
    assert after.size != before.size
    assert refreshed.read(uri) == (skill / "SKILL.md").read_bytes()


def test_skill_allowed_tools_is_metadata_not_an_execution_grant(tmp_path: Path) -> None:
    _write_skill(
        tmp_path,
        "demo-skill",
        extra_frontmatter="allowed-tools: create_contribution publish_candidates\n",
    )
    catalog = SkillCatalog(tmp_path)
    extension = SkillsExtension(catalog)
    entry = catalog.get("skill://demo-skill/SKILL.md")

    assert entry.frontmatter["allowed-tools"] == (
        "create_contribution publish_candidates"
    )
    assert extension.tools() == ()
    assert {binding.method for binding in extension.methods()} == {
        "skills/list",
        "skills/get",
    }


def test_skill_manifest_resource_uses_frontmatter_metadata(tmp_path: Path) -> None:
    description = "Human-readable skill description from canonical frontmatter."
    _write_skill(tmp_path, "demo-skill", description=description)
    extension = SkillsExtension(SkillCatalog(tmp_path))

    resources = {binding.resource.uri: binding.resource for binding in extension.resources()}
    manifest = resources["skill://demo-skill/SKILL.md"]

    assert manifest.name == "demo-skill"
    assert manifest.description == description
    assert manifest.mime_type == "text/markdown"
