"""Capability policy for restricted social contribution sources."""

from __future__ import annotations

import re
from enum import StrEnum
from urllib.parse import urlsplit

from pydantic import BaseModel, ConfigDict

from github_stars_contrib_mcp.application.discovery.source_identity import (
    canonicalize_source_url,
)
from github_stars_contrib_mcp.domain.discovery import (
    OwnershipStatus,
    SourceRecord,
    SourceType,
)
from github_stars_contrib_mcp.domain.ports.source_adapter import (
    CapabilityStatus,
    SourceCapability,
)

_SOCIAL_TYPES = {SourceType.X, SourceType.LINKEDIN}
_X_STATUS_RE = re.compile(r"/(?:[^/]+/status|i/web/status)/(\d+)(?:/|$)")
_LINKEDIN_ACTIVITY_RE = re.compile(r"(?:activity[:-]|activity-)(\d+)")


class SocialAccessMode(StrEnum):
    """Supported access modes for restricted social providers.

    Deliberately no browser/scrape mode exists.
    """

    EXPLICIT_URL = "explicit_url"
    EXPORT_IMPORT = "export_import"
    OFFICIAL_API = "official_api"
    UNAVAILABLE = "unavailable"


class RestrictedSocialCapability(BaseModel):
    """Actionable provider capability without embedding credentials."""

    model_config = ConfigDict(extra="forbid")

    provider: SourceType
    mode: SocialAccessMode
    status: CapabilityStatus
    reason: str | None = None
    user_action: str | None = None
    requires_credentials: bool = False
    permissions: tuple[str, ...] = ()

    def as_source_capability(self) -> SourceCapability:
        return SourceCapability(
            status=self.status,
            reason=self.reason,
            user_action=self.user_action,
            requires_credentials=self.requires_credentials,
            permissions=self.permissions,
        )


def social_access_mode(source: SourceRecord) -> SocialAccessMode:
    """Resolve one source to exactly one social access mode."""

    raw = source.metadata.get("social_mode")
    if raw is None and source.metadata.get("import_path"):
        return SocialAccessMode.EXPORT_IMPORT
    if raw is None:
        return SocialAccessMode.EXPLICIT_URL
    try:
        return SocialAccessMode(str(raw).strip().lower())
    except ValueError:
        return SocialAccessMode.UNAVAILABLE


def is_supported_social_post_url(source_type: SourceType, url: str) -> bool:
    """Return whether URL identifies a concrete supported social post."""

    if source_type not in _SOCIAL_TYPES:
        return False
    try:
        canonical = canonicalize_source_url(url)
    except ValueError:
        return False
    if canonical.source_type is not source_type:
        return False
    path = urlsplit(canonical.canonical_url).path
    if source_type is SourceType.X:
        return _X_STATUS_RE.search(path) is not None
    lowered = path.lower()
    return (
        "/posts/" in lowered
        or "/feed/update/" in lowered
        or "/pulse/" in lowered
    )


def social_post_external_id(source_type: SourceType, url: str) -> str:
    """Extract a stable provider ID when present, otherwise hash canonical URL."""

    import hashlib

    canonical = canonicalize_source_url(url)
    path = urlsplit(canonical.canonical_url).path
    if source_type is SourceType.X:
        match = _X_STATUS_RE.search(path)
        if match:
            return f"x:{match.group(1)}"
    elif source_type is SourceType.LINKEDIN:
        match = _LINKEDIN_ACTIVITY_RE.search(path)
        if match:
            return f"linkedin:{match.group(1)}"
    digest = hashlib.sha256(canonical.canonical_url.encode()).hexdigest()[:32]
    return f"{source_type.value}:{digest}"


def assess_social_capability(source: SourceRecord) -> RestrictedSocialCapability:
    """Describe compliant access for one X/LinkedIn source, default-deny otherwise."""

    mode = social_access_mode(source)
    provider = source.source_type
    if provider not in _SOCIAL_TYPES:
        return RestrictedSocialCapability(
            provider=provider,
            mode=SocialAccessMode.UNAVAILABLE,
            status=CapabilityStatus.UNAVAILABLE,
            reason="source is not a restricted social provider",
        )
    if source.ownership not in {OwnershipStatus.EXPLICIT, OwnershipStatus.VERIFIED}:
        return RestrictedSocialCapability(
            provider=provider,
            mode=mode,
            status=CapabilityStatus.UNAVAILABLE,
            reason="restricted social discovery requires explicit or verified ownership",
            user_action="explicitly register or verify this social source first",
        )
    if mode is SocialAccessMode.EXPLICIT_URL:
        if is_supported_social_post_url(provider, source.url):
            return RestrictedSocialCapability(
                provider=provider,
                mode=mode,
                status=CapabilityStatus.AVAILABLE,
                reason="explicit post URL can be ingested without authenticated scraping",
            )
        return RestrictedSocialCapability(
            provider=provider,
            mode=mode,
            status=CapabilityStatus.UNAVAILABLE,
            reason="explicit URL mode requires a concrete post URL, not a profile/feed",
            user_action="register the exact X or LinkedIn post URL",
        )
    if mode is SocialAccessMode.EXPORT_IMPORT:
        if isinstance(source.metadata.get("import_path"), str) and str(
            source.metadata["import_path"]
        ).strip():
            return RestrictedSocialCapability(
                provider=provider,
                mode=mode,
                status=CapabilityStatus.AVAILABLE,
                reason="local user-provided export can be imported without upload",
            )
        return RestrictedSocialCapability(
            provider=provider,
            mode=mode,
            status=CapabilityStatus.UNAVAILABLE,
            reason="export/import mode requires a local import_path",
            user_action="set import_path to a local neutral JSON or CSV export",
        )
    if mode is SocialAccessMode.OFFICIAL_API:
        return RestrictedSocialCapability(
            provider=provider,
            mode=mode,
            status=CapabilityStatus.UNAVAILABLE,
            reason="no provider OAuth/API connector is configured in the v0.3 core",
            user_action="install/configure a compliant SourceAdapter for the provider API",
            requires_credentials=True,
        )
    return RestrictedSocialCapability(
        provider=provider,
        mode=mode,
        status=CapabilityStatus.UNAVAILABLE,
        reason="restricted social access is disabled or the requested mode is unsupported",
        user_action="use explicit_url, export_import, or a compliant official_api adapter",
    )
