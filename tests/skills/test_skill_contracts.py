"""Static contracts for repository skills and host-neutral agent guidance."""

from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SKILLS = ROOT / "skills"
AGENTS = ROOT / "agents"


def _read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def _assert_no_direct_provider_logic(text: str) -> None:
    lowered = text.lower()
    forbidden = (
        "import requests",
        "import httpx",
        "curl ",
        "api.github.com",
        "youtube.googleapis.com",
        "sessionize.com/api/",
        "linkedin.com/v2/",
        "api.x.com/",
    )
    for token in forbidden:
        assert token not in lowered


def test_discover_my_contributions_contract() -> None:
    text = _read(SKILLS / "discover-my-contributions" / "SKILL.md")
    tools = (
        "bootstrap_sources",
        "list_sources",
        "add_source",
        "sync_source",
        "discover_contributions",
        "list_candidates",
        "get_candidate",
    )
    for tool in tools:
        assert f"`{tool}" in text
    assert "UNTRUSTED_SOURCE_CONTENT" in text
    assert "Do not approve or publish candidates" in text
    assert "Never convert high confidence into approval automatically" in text
    _assert_no_direct_provider_logic(text)


def test_sync_source_contract() -> None:
    text = _read(SKILLS / "sync-source" / "SKILL.md")
    assert "`list_sources" in text
    assert "`sync_source" in text
    assert "`add_source" in text
    for token in ("auth", "rate_limit", "security", "unavailable"):
        assert token in text
    assert "Never invent or suggest a bypass" in text
    assert "UNTRUSTED_SOURCE_CONTENT" in text
    _assert_no_direct_provider_logic(text)


def test_review_candidates_contract() -> None:
    text = _read(SKILLS / "review-candidates" / "SKILL.md")
    for tool in ("list_candidates", "get_candidate", "review_candidate"):
        assert f"`{tool}" in text
    concepts = (
        "evidence",
        "provenance",
        "duplicate state",
        "contribution confidence",
        "ownership confidence",
    )
    for concept in concepts:
        assert concept in text
    assert "Never auto-approve because confidence is high" in text
    assert "**approve**" in text
    assert "**reject**" in text
    assert "**defer**" in text
    assert "**edit + approve**" in text
    _assert_no_direct_provider_logic(text)


def test_publish_approved_contract() -> None:
    text = _read(SKILLS / "publish-approved" / "SKILL.md")
    dry = "`publish_approved_candidates(candidate_ids, dry_run=true)`"
    real = "`publish_approved_candidates(candidate_ids, dry_run=false)`"
    assert dry in text
    assert real in text
    assert text.index("dry_run=true") < text.index("dry_run=false")
    assert "explicit user intent in the current interaction" in text
    assert "This skill never changes review state and never approves candidates" in text
    assert "Do not combine approval and publication" in text
    assert "review_candidate(" not in text
    _assert_no_direct_provider_logic(text)


def test_agent_guidance_contract() -> None:
    readme = _read(AGENTS / "README.md")
    agent = _read(AGENTS / "contribution-curator.md")
    combined = f"{readme}\n{agent}"
    for skill in (
        "discover-my-contributions",
        "sync-source",
        "review-candidates",
        "publish-approved",
    ):
        assert skill in combined
    assert "UNTRUSTED_SOURCE_CONTENT" in combined
    assert "X/LinkedIn scraping" in combined
    assert "direct Stars write authority" in combined
    assert "dry_run=true" in combined
