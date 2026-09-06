"""Provider-neutral session normalization tests."""

from github_stars_contrib_mcp.application.discovery.session_normalizer import (
    SessionDescriptor,
    build_session_item,
    normalize_session_format,
    verified_speaker_match,
)
from github_stars_contrib_mcp.domain.discovery import (
    OwnershipStatus,
    SourceRecord,
    SourceType,
)
from github_stars_contrib_mcp.models import ContributionType


def _source(metadata: dict[str, object]) -> SourceRecord:
    return SourceRecord(
        id="sessionize:https://sessionize.com/api/v2/event/view/All",
        source_type=SourceType.SESSIONIZE,
        url="https://sessionize.com/api/v2/event/view/All",
        ownership=OwnershipStatus.VERIFIED,
        metadata=metadata,
    )


def test_verified_speaker_match_prefers_stable_id_and_exact_name_only() -> None:
    source = _source(
        {
            "verified_speaker_ids": ["speaker-1"],
            "verified_speaker_names": ["Sergio Valverde"],
        }
    )

    by_id = verified_speaker_match(source, speaker_ids=("speaker-1",))
    by_name = verified_speaker_match(source, speaker_names=("SERGIO   VALVERDE",))
    fuzzy = verified_speaker_match(source, speaker_names=("Sergio V.",))

    assert by_id is not None and by_id.method == "speaker_id"
    assert by_name is not None and by_name.method == "speaker_name"
    assert fuzzy is None


def test_build_session_item_uses_stars_speaking_type_and_preserves_format() -> None:
    source = _source({"verified_speaker_ids": ["speaker-1"]})
    match = verified_speaker_match(source, speaker_ids=("speaker-1",))
    descriptor = SessionDescriptor(
        provider="sessionize",
        event_name="Community Day",
        external_id="sessionize:session:abc",
        title="Agentic workflows",
        speaker_ids=("speaker-1",),
        speaker_names=("Sergio Valverde",),
        session_url="https://event.example/sessions/abc",
        format_hint="Hands-on Workshop",
    )

    item = build_session_item(source, descriptor, speaker_match=match)

    assert item.type_hint is ContributionType.SPEAKING
    assert item.metadata["session_format"] == "workshop"
    assert item.metadata["event_name"] == "Community Day"


def test_unmatched_session_remains_review_only_without_speaking_type() -> None:
    source = _source({"verified_speaker_ids": ["speaker-1"]})
    descriptor = SessionDescriptor(
        provider="sessionize",
        event_name="Community Day",
        external_id="sessionize:session:other",
        title="Someone else's talk",
        speaker_ids=("speaker-2",),
    )

    item = build_session_item(source, descriptor, speaker_match=None)

    assert item.type_hint is None
    assert normalize_session_format("Keynote session") == "keynote"
