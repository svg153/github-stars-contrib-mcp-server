"""Restricted social capability policy is explicit and has no scrape fallback."""

from github_stars_contrib_mcp.application.discovery.social_capabilities import (
    SocialAccessMode,
    assess_social_capability,
    is_supported_social_post_url,
    social_access_mode,
)
from github_stars_contrib_mcp.domain.discovery import (
    OwnershipStatus,
    SourceRecord,
    SourceType,
)
from github_stars_contrib_mcp.domain.ports.source_adapter import CapabilityStatus


def _source(url: str, source_type: SourceType, **metadata: object) -> SourceRecord:
    return SourceRecord(
        id=f"{source_type.value}:{url}",
        source_type=source_type,
        url=url,
        ownership=OwnershipStatus.EXPLICIT,
        metadata=dict(metadata),
    )


def test_capability_enum_deliberately_has_no_scrape_mode() -> None:
    assert "scrape" not in {mode.value for mode in SocialAccessMode}


def test_explicit_x_and_linkedin_post_urls_are_supported() -> None:
    x = _source("https://twitter.com/alice/status/123", SourceType.X)
    linkedin = _source(
        "https://www.linkedin.com/posts/alice_topic-activity-456-abcd",
        SourceType.LINKEDIN,
    )

    assert is_supported_social_post_url(SourceType.X, x.url)
    assert is_supported_social_post_url(SourceType.LINKEDIN, linkedin.url)
    assert assess_social_capability(x).status is CapabilityStatus.AVAILABLE
    assert assess_social_capability(linkedin).status is CapabilityStatus.AVAILABLE


def test_profile_url_is_actionably_unavailable_in_explicit_url_mode() -> None:
    source = _source("https://x.com/alice", SourceType.X)
    capability = assess_social_capability(source)

    assert capability.status is CapabilityStatus.UNAVAILABLE
    assert "exact" in (capability.user_action or "")


def test_import_path_selects_export_mode_and_official_api_never_falls_back() -> None:
    imported = _source(
        "https://x.com/alice",
        SourceType.X,
        import_path="/tmp/posts.json",
    )
    official = _source(
        "https://linkedin.com/in/alice",
        SourceType.LINKEDIN,
        social_mode="official_api",
    )

    assert social_access_mode(imported) is SocialAccessMode.EXPORT_IMPORT
    official_capability = assess_social_capability(official)
    assert official_capability.status is CapabilityStatus.UNAVAILABLE
    assert official_capability.requires_credentials is True
    assert "compliant" in (official_capability.user_action or "")


def test_inferred_social_source_is_not_silently_trusted() -> None:
    source = SourceRecord(
        id="x:https://x.com/alice/status/123",
        source_type=SourceType.X,
        url="https://x.com/alice/status/123",
        ownership=OwnershipStatus.INFERRED,
    )

    assert assess_social_capability(source).status is CapabilityStatus.UNAVAILABLE
