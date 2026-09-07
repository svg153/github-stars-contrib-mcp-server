"""Contract tests for provider-neutral source adapters."""

from collections.abc import AsyncIterator
from typing import Any

from github_stars_contrib_mcp.domain.discovery import (
    Evidence,
    OwnershipStatus,
    SourceItem,
    SourceRecord,
    SourceType,
)
from github_stars_contrib_mcp.domain.ports.source_adapter import (
    AdapterEmission,
    CapabilityStatus,
    SourceAdapter,
    SourceBatch,
    SourceCapability,
)


class FakeAdapter:
    name = "fake"
    version = "1"

    def supports(self, source: SourceRecord) -> bool:
        return source.source_type is SourceType.WEBSITE

    def capabilities(self, source: SourceRecord) -> SourceCapability:
        return SourceCapability(
            status=CapabilityStatus.AVAILABLE,
            user_action="optional next step",
        )

    async def iter_items(
        self,
        source: SourceRecord,
        cursor: dict[str, Any] | None,
    ) -> AsyncIterator[SourceBatch]:
        item = SourceItem(
            source_id=source.id,
            external_id="item-1",
            title="Example",
            url="https://example.com/post",
        )
        evidence = Evidence(
            id="evidence-1",
            source_id=source.id,
            source_item_id=item.external_id,
            url=item.url,
        )
        yield SourceBatch(
            emissions=(AdapterEmission(item=item, evidence=(evidence,)),),
            next_cursor={"after": "item-1"},
        )


def test_contract_is_runtime_fakeable_and_capabilities_can_be_actionable() -> None:
    source = SourceRecord(
        id="website:https://example.com",
        source_type=SourceType.WEBSITE,
        url="https://example.com",
        ownership=OwnershipStatus.VERIFIED,
    )
    adapter = FakeAdapter()
    assert isinstance(adapter, SourceAdapter)
    assert adapter.supports(source)
    capability = adapter.capabilities(source)
    assert capability.status is CapabilityStatus.AVAILABLE
    assert capability.user_action == "optional next step"
