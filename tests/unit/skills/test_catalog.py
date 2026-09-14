"""Tests for the transport-independent MCP Skills catalog foundation."""

from __future__ import annotations

import hashlib
from pathlib import Path

import pytest

from github_stars_contrib_mcp.skills import SkillCatalog, SkillCatalogError


def _write_skill(
    root: Path,
    name: str,
    *,
    frontmatter_name: str | None = None,
    description: str = "Test skill for deterministic catalog behavior.",
    extra_frontmatter: str = "",
) -> Path:
    skill = root / name
    skill.mkdir(parents=True)
    declared_name = frontmatter_name or name
    (skill / "SKILL.md").write_text(
        "---\n"
        f"name: {declared_name}\n"
        f"description: {description}\n"
        f"{extra_frontmatter}"
        "---\n\n"
        f"# {name}\n",
        encoding="utf-8",
    )
    return skill


def test_repository_catalog_discovers_the_four_canonical_skills() -> None:
    catalog = SkillCatalog()

    assert [entry.name for entry in catalog.list()] == [
        "discover-my-contributions",
        "publish-approved",
        "review-candidates",
        "sync-source",
    ]
    assert all(
        entry.uri == f"skill://{entry.name}/SKILL.md" for entry in catalog.list()
    )
    assert all(
        any(resource.relative_path == "SKILL.md" for resource in entry.resources)
        for entry in catalog.list()
    )


def test_manifest_digest_and_size_match_exact_served_bytes(tmp_path: Path) -> None:
    skill = _write_skill(tmp_path, "demo-skill")
    reference = skill / "references" / "guide.md"
    reference.parent.mkdir()
    reference.write_bytes(b"# Guide\n\nExact bytes.\n")

    catalog = SkillCatalog(tmp_path)
    entry = catalog.get("skill://demo-skill/SKILL.md")

    resources = {resource.relative_path: resource for resource in entry.resources}
    assert list(resources) == ["SKILL.md", "references/guide.md"]

    for relative, resource in resources.items():
        data = (skill / relative).read_bytes()
        assert resource.size == len(data)
        assert resource.digest == f"sha256:{hashlib.sha256(data).hexdigest()}"
        assert catalog.read(resource.uri) == data


def test_nested_resources_receive_stable_percent_encoded_uris(tmp_path: Path) -> None:
    skill = _write_skill(tmp_path, "demo-skill")
    asset = skill / "references" / "with space.md"
    asset.parent.mkdir()
    asset.write_text("reference\n", encoding="utf-8")

    first = SkillCatalog(tmp_path)
    second = SkillCatalog(tmp_path)

    first_entry = first.get("skill://demo-skill/SKILL.md")
    second_entry = second.get("skill://demo-skill/SKILL.md")
    first_manifest = [
        (item.uri, item.digest, item.size) for item in first_entry.resources
    ]
    second_manifest = [
        (item.uri, item.digest, item.size) for item in second_entry.resources
    ]

    assert first_manifest == second_manifest
    assert "skill://demo-skill/references/with%20space.md" in {
        item.uri for item in first_entry.resources
    }


def test_catalog_preserves_all_json_serializable_frontmatter(tmp_path: Path) -> None:
    _write_skill(
        tmp_path,
        "demo-skill",
        extra_frontmatter=(
            "license: MIT\n"
            "compatibility: Requires an MCP connection.\n"
            "metadata:\n"
            "  author: svg153\n"
            '  version: "1.0"\n'
            "allowed-tools: Read\n"
        ),
    )

    entry = SkillCatalog(tmp_path).get("skill://demo-skill/SKILL.md")

    assert entry.frontmatter == {
        "name": "demo-skill",
        "description": "Test skill for deterministic catalog behavior.",
        "license": "MIT",
        "compatibility": "Requires an MCP connection.",
        "metadata": {"author": "svg153", "version": "1.0"},
        "allowed-tools": "Read",
    }


def test_name_must_match_parent_directory_and_agent_skills_rules(
    tmp_path: Path,
) -> None:
    _write_skill(tmp_path, "demo-skill", frontmatter_name="other-skill")

    with pytest.raises(SkillCatalogError, match="must match parent directory"):
        SkillCatalog(tmp_path)


def test_malformed_frontmatter_fails_closed(tmp_path: Path) -> None:
    skill = tmp_path / "broken-skill"
    skill.mkdir()
    (skill / "SKILL.md").write_text(
        "---\nname: broken-skill\n# no closing delimiter\n",
        encoding="utf-8",
    )

    with pytest.raises(SkillCatalogError, match="frontmatter is not terminated"):
        SkillCatalog(tmp_path)


def test_symlinked_skill_content_is_rejected(tmp_path: Path) -> None:
    skill = _write_skill(tmp_path, "demo-skill")
    outside = tmp_path / "outside.txt"
    outside.write_text("outside\n", encoding="utf-8")
    link = skill / "references" / "escape.txt"
    link.parent.mkdir()
    try:
        link.symlink_to(outside)
    except (OSError, NotImplementedError):
        pytest.skip("symlinks are unavailable on this platform")

    with pytest.raises(SkillCatalogError, match="symlinks are not allowed"):
        SkillCatalog(tmp_path)


def test_resource_reads_are_manifest_bound_and_reject_traversal(tmp_path: Path) -> None:
    _write_skill(tmp_path, "demo-skill")
    catalog = SkillCatalog(tmp_path)

    with pytest.raises(SkillCatalogError, match="unknown skill resource URI"):
        catalog.read("skill://demo-skill/../outside.txt")


def test_manifest_drift_requires_refresh_before_resource_use(tmp_path: Path) -> None:
    skill = _write_skill(tmp_path, "demo-skill")
    catalog = SkillCatalog(tmp_path)
    uri = "skill://demo-skill/SKILL.md"

    with (skill / "SKILL.md").open("a", encoding="utf-8") as handle:
        handle.write("\nChanged after manifest creation.\n")

    with pytest.raises(SkillCatalogError, match="changed after manifest creation"):
        catalog.read(uri)

    refreshed = SkillCatalog(tmp_path)
    assert refreshed.read(uri) == (skill / "SKILL.md").read_bytes()
