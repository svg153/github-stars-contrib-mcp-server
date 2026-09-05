import pytest

from github_stars_contrib_mcp.application.discovery.youtube_identity import (
    normalize_youtube_channel,
    source_channel_id,
)


def test_channel_url_is_canonical_and_stable() -> None:
    channel_id = "UC" + "a" * 22
    identity = normalize_youtube_channel(
        f"https://m.youtube.com/channel/{channel_id}/"
    )
    assert identity.channel_id == channel_id
    assert identity.registry_key == f"channel:{channel_id}"
    assert identity.canonical_url == f"https://www.youtube.com/channel/{channel_id}"
    assert not identity.needs_api_resolution


def test_handle_is_normalized_but_requires_api_resolution() -> None:
    identity = normalize_youtube_channel("https://youtube.com/@GitHub")
    assert identity.handle == "github"
    assert identity.registry_key == "handle:github"
    assert identity.canonical_url == "https://www.youtube.com/@github"
    assert identity.needs_api_resolution


def test_api_confirmed_channel_id_collapses_equivalent_urls() -> None:
    channel_id = "UC" + "b" * 22
    by_handle = normalize_youtube_channel(
        "https://www.youtube.com/@github",
        known_channel_id=channel_id,
    )
    by_custom = normalize_youtube_channel(
        "https://www.youtube.com/c/GitHub",
        known_channel_id=channel_id,
    )
    assert by_handle.registry_key == by_custom.registry_key == f"channel:{channel_id}"


def test_video_url_is_not_a_channel_identity() -> None:
    with pytest.raises(ValueError, match="video or playlist"):
        normalize_youtube_channel("https://www.youtube.com/watch?v=abc")


def test_source_channel_id_accepts_only_trusted_metadata_shape() -> None:
    channel_id = "UC" + "c" * 22
    assert source_channel_id(
        "https://www.youtube.com/@github",
        {"youtube_channel_id": channel_id},
    ) == channel_id
