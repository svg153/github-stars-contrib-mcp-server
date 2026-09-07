"""Stable, explainable fingerprints for discovered contribution candidates."""

from __future__ import annotations

import hashlib
import re
import unicodedata
from dataclasses import dataclass
from datetime import datetime
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

from github_stars_contrib_mcp.domain.discovery import CandidateContribution

_TRACKING_QUERY_PREFIXES = ("utm_",)
_TRACKING_QUERY_KEYS = {"fbclid", "gclid", "mc_cid", "mc_eid"}
_SPACE_RE = re.compile(r"\s+")


@dataclass(frozen=True, slots=True)
class CandidateFingerprints:
    source: str
    url: str
    content: str | None
    canonical_url: str
    normalized_title: str


def _digest(kind: str, value: str) -> str:
    return f"{kind}:{hashlib.sha256(value.encode('utf-8')).hexdigest()}"


def normalize_text(value: str) -> str:
    value = unicodedata.normalize("NFKC", value)
    return _SPACE_RE.sub(" ", value).strip().casefold()


def canonicalize_url(value: str) -> str:
    """Canonicalize identity-relevant URL parts without guessing redirects."""

    split = urlsplit(value.strip())
    scheme = split.scheme.lower() or "https"
    hostname = (split.hostname or "").lower()
    port = split.port
    netloc = hostname
    if port and not (
        (scheme == "https" and port == 443) or (scheme == "http" and port == 80)
    ):
        netloc = f"{hostname}:{port}"

    path = split.path or "/"
    if path != "/":
        path = path.rstrip("/")

    query_pairs = [
        (key, val)
        for key, val in parse_qsl(split.query, keep_blank_values=True)
        if key.casefold() not in _TRACKING_QUERY_KEYS
        and not key.casefold().startswith(_TRACKING_QUERY_PREFIXES)
    ]
    query_pairs.sort()
    return urlunsplit((scheme, netloc, path, urlencode(query_pairs, doseq=True), ""))


def _date_key(value: datetime | None) -> str | None:
    return value.date().isoformat() if value is not None else None


def fingerprint_candidate(candidate: CandidateContribution) -> CandidateFingerprints:
    canonical_url = canonicalize_url(candidate.url)
    normalized_title = normalize_text(candidate.title)
    source_material = f"{candidate.source_id}\0{candidate.external_id}"
    source_fp = _digest("source", source_material)
    url_fp = _digest("url", canonical_url)

    contribution_type = (
        candidate.contribution_type.value
        if candidate.contribution_type is not None
        else None
    )
    date_key = _date_key(candidate.date)
    content_fp: str | None = None
    if normalized_title and date_key and contribution_type:
        content_fp = _digest(
            "content", f"{normalized_title}\0{date_key}\0{contribution_type}"
        )

    return CandidateFingerprints(
        source=source_fp,
        url=url_fp,
        content=content_fp,
        canonical_url=canonical_url,
        normalized_title=normalized_title,
    )
