"""Offline RSS 2.0 and Atom parsing for discovery adapters."""

from __future__ import annotations

import re
from datetime import UTC, datetime
from email.utils import parsedate_to_datetime
from html.parser import HTMLParser
from typing import Any
from xml.etree import ElementTree

from pydantic import BaseModel, ConfigDict

_UNSAFE_XML_RE = re.compile(r"<!\s*(?:DOCTYPE|ENTITY)\b", re.IGNORECASE)


class FeedParseError(ValueError):
    """Raised when the feed document cannot be parsed safely."""


class FeedEntry(BaseModel):
    """Provider-neutral representation of one feed entry."""

    model_config = ConfigDict(extra="forbid")

    stable_id: str
    title: str
    link: str
    published_at: datetime | None = None
    updated_at: datetime | None = None
    author: str | None = None
    summary: str | None = None


class FeedParseResult(BaseModel):
    """Parsed entries plus item-level diagnostics."""

    model_config = ConfigDict(extra="forbid")

    entries: tuple[FeedEntry, ...] = ()
    errors: tuple[str, ...] = ()


class _TextExtractor(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.parts: list[str] = []

    def handle_data(self, data: str) -> None:
        value = data.strip()
        if value:
            self.parts.append(value)

    def text(self) -> str:
        return " ".join(self.parts)


def _plain_text(value: str | None) -> str | None:
    if value is None:
        return None
    parser = _TextExtractor()
    parser.feed(value)
    parser.close()
    normalized = " ".join(parser.text().split())
    return normalized or None


def _local_name(tag: str) -> str:
    return tag.rsplit("}", 1)[-1].lower()


def _children(element: ElementTree.Element, name: str) -> list[ElementTree.Element]:
    wanted = name.lower()
    return [child for child in element if _local_name(child.tag) == wanted]


def _child(element: ElementTree.Element, name: str) -> ElementTree.Element | None:
    matches = _children(element, name)
    return matches[0] if matches else None


def _text(element: ElementTree.Element, name: str) -> str | None:
    child = _child(element, name)
    if child is None:
        return None
    value = "".join(child.itertext()).strip()
    return value or None


def _parse_rss_datetime(value: str | None) -> datetime | None:
    if not value:
        return None
    try:
        parsed = parsedate_to_datetime(value)
    except (TypeError, ValueError):
        return None
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=UTC)
    return parsed.astimezone(UTC)


def _parse_iso_datetime(value: str | None) -> datetime | None:
    if not value:
        return None
    candidate = value.strip()
    if candidate.endswith("Z"):
        candidate = f"{candidate[:-1]}+00:00"
    try:
        parsed = datetime.fromisoformat(candidate)
    except ValueError:
        return None
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=UTC)
    return parsed.astimezone(UTC)


def _rss_entry(item: ElementTree.Element) -> FeedEntry:
    title = _plain_text(_text(item, "title"))
    link = _text(item, "link")
    guid = _text(item, "guid")
    if not title:
        raise ValueError("RSS item is missing title")
    if not link:
        raise ValueError("RSS item is missing link")
    stable_id = (guid or link).strip()
    if not stable_id:
        raise ValueError("RSS item is missing a stable id")
    author = _text(item, "author") or _text(item, "creator")
    summary = _plain_text(_text(item, "description") or _text(item, "summary"))
    published = _parse_rss_datetime(_text(item, "pubDate"))
    updated = _parse_iso_datetime(_text(item, "updated"))
    return FeedEntry(
        stable_id=stable_id,
        title=title,
        link=link.strip(),
        published_at=published,
        updated_at=updated,
        author=author.strip() if author else None,
        summary=summary,
    )


def _atom_link(entry: ElementTree.Element) -> str | None:
    links = _children(entry, "link")
    preferred: list[ElementTree.Element] = []
    fallback: list[ElementTree.Element] = []
    for link in links:
        rel = (link.attrib.get("rel") or "alternate").lower()
        if rel == "alternate":
            preferred.append(link)
        else:
            fallback.append(link)
    for link in [*preferred, *fallback]:
        href = (link.attrib.get("href") or "").strip()
        if href:
            return href
    return None


def _atom_author(entry: ElementTree.Element) -> str | None:
    author = _child(entry, "author")
    if author is None:
        return None
    name = _text(author, "name")
    return name.strip() if name else None


def _atom_entry(entry: ElementTree.Element) -> FeedEntry:
    title = _plain_text(_text(entry, "title"))
    link = _atom_link(entry)
    stable_id = (_text(entry, "id") or link or "").strip()
    if not title:
        raise ValueError("Atom entry is missing title")
    if not link:
        raise ValueError("Atom entry is missing link")
    if not stable_id:
        raise ValueError("Atom entry is missing a stable id")
    summary = _plain_text(_text(entry, "summary") or _text(entry, "content"))
    return FeedEntry(
        stable_id=stable_id,
        title=title,
        link=link,
        published_at=_parse_iso_datetime(_text(entry, "published")),
        updated_at=_parse_iso_datetime(_text(entry, "updated")),
        author=_atom_author(entry),
        summary=summary,
    )


def parse_feed(payload: bytes | str) -> FeedParseResult:
    """Parse RSS 2.0 or Atom without network access or entity expansion."""

    raw = payload.decode("utf-8", errors="replace") if isinstance(payload, bytes) else payload
    if _UNSAFE_XML_RE.search(raw):
        raise FeedParseError("DTD/entity declarations are not allowed in discovery feeds")
    try:
        root = ElementTree.fromstring(raw)
    except ElementTree.ParseError as exc:
        raise FeedParseError(f"malformed feed XML: {exc}") from exc

    root_name = _local_name(root.tag)
    if root_name == "rss":
        channel = _child(root, "channel")
        if channel is None:
            raise FeedParseError("RSS feed is missing channel")
        raw_entries = _children(channel, "item")
        parser = _rss_entry
    elif root_name == "feed":
        raw_entries = _children(root, "entry")
        parser = _atom_entry
    else:
        raise FeedParseError(f"unsupported feed root: {root_name}")

    entries: list[FeedEntry] = []
    errors: list[str] = []
    seen: set[str] = set()
    for index, raw_entry in enumerate(raw_entries):
        try:
            entry = parser(raw_entry)
        except ValueError as exc:
            errors.append(f"entry[{index}]: {exc}")
            continue
        if entry.stable_id in seen:
            errors.append(f"entry[{index}]: duplicate stable id {entry.stable_id}")
            continue
        seen.add(entry.stable_id)
        entries.append(entry)
    return FeedParseResult(entries=tuple(entries), errors=tuple(errors))
