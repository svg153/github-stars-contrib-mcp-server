from pathlib import Path

import pytest

from github_stars_contrib_mcp.release_version import (
    canonical_tag,
    normalize_tag,
    package_version_from,
    validate_tag,
)


def test_normalize_tag_accepts_plain_and_ref_forms() -> None:
    assert normalize_tag("v0.3.1") == "0.3.1"
    assert normalize_tag("refs/tags/v0.3.1") == "0.3.1"
    assert normalize_tag("0.3.1") == "0.3.1"


def test_canonical_tag_removes_only_ref_prefix() -> None:
    assert canonical_tag("refs/tags/v0.3.1") == "v0.3.1"
    assert canonical_tag("v0.3.1") == "v0.3.1"


def test_package_version_from_reads_project_version(tmp_path: Path) -> None:
    pyproject = tmp_path / "pyproject.toml"
    pyproject.write_text(
        '[project]\nname = "demo"\nversion = "1.2.3"\n', encoding="utf-8"
    )
    assert package_version_from(pyproject) == "1.2.3"


def test_validate_tag_rejects_version_mismatch() -> None:
    with pytest.raises(ValueError, match="must be exactly"):
        validate_tag("v0.3.0", "0.3.1")


def test_validate_tag_rejects_noncanonical_tag() -> None:
    with pytest.raises(ValueError, match="must be exactly"):
        validate_tag("0.3.1", "0.3.1")


def test_validate_tag_accepts_exact_match() -> None:
    validate_tag("v0.3.1", "0.3.1")
