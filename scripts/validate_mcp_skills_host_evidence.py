#!/usr/bin/env python3
"""Validate sanitized host evidence for MCP-served Agent Skills."""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Any

SECRET_KEY_PARTS = (
    "authorization",
    "password",
    "secret",
    "token",
    "cookie",
    "api_key",
    "apikey",
    "access_key",
)
SECRET_VALUE_PATTERNS = (
    re.compile(r"(?i)\bbearer\s+[a-z0-9._~+/=-]{8,}"),
    re.compile(r"\bgithub_pat_[A-Za-z0-9_]{10,}"),
    re.compile(r"\bgh[pousr]_[A-Za-z0-9]{20,}"),
    re.compile(r"\bsk-[A-Za-z0-9_-]{20,}"),
)
COMMIT_RE = re.compile(r"^[0-9a-f]{40}$")


def _is_nonempty_string(value: Any) -> bool:
    return isinstance(value, str) and bool(value.strip())


def _find_secret_material(value: Any, path: str = "$") -> list[str]:
    errors: list[str] = []
    if isinstance(value, dict):
        for key, child in value.items():
            lowered = str(key).casefold()
            if any(part in lowered for part in SECRET_KEY_PARTS):
                errors.append(f"{path}.{key}: credential-bearing key is forbidden")
            errors.extend(_find_secret_material(child, f"{path}.{key}"))
    elif isinstance(value, list):
        for index, child in enumerate(value):
            errors.extend(_find_secret_material(child, f"{path}[{index}]"))
    elif isinstance(value, str):
        for pattern in SECRET_VALUE_PATTERNS:
            if pattern.search(value):
                errors.append(f"{path}: token-shaped value is forbidden")
                break
    return errors


def validate_payload(payload: Any) -> list[str]:
    errors: list[str] = []
    if not isinstance(payload, dict):
        return ["$: expected a JSON object"]

    errors.extend(_find_secret_material(payload))

    if payload.get("schema_version") != 1:
        errors.append("$.schema_version: must equal 1")

    for section in ("host", "server", "skill", "observations", "evidence"):
        if not isinstance(payload.get(section), dict):
            errors.append(f"$.{section}: expected an object")

    if errors and any("expected an object" in error for error in errors):
        return errors

    host = payload["host"]
    server = payload["server"]
    skill = payload["skill"]
    observations = payload["observations"]
    evidence = payload["evidence"]

    for key in ("name", "version", "model"):
        if not _is_nonempty_string(host.get(key)):
            errors.append(f"$.host.{key}: non-empty string required")

    if server.get("repository") != (
        "https://github.com/svg153/github-stars-contrib-mcp-server"
    ):
        errors.append("$.server.repository: unexpected repository")
    if not _is_nonempty_string(server.get("version")):
        errors.append("$.server.version: non-empty string required")
    commit = server.get("commit")
    if not isinstance(commit, str) or not COMMIT_RE.fullmatch(commit):
        errors.append("$.server.commit: full lowercase 40-character SHA required")
    if server.get("transport") not in {"streamable-http", "stdio"}:
        errors.append("$.server.transport: must be streamable-http or stdio")

    if not _is_nonempty_string(skill.get("name")):
        errors.append("$.skill.name: non-empty string required")
    uri = skill.get("uri")
    expected_uri = f"skill://{skill.get('name')}/SKILL.md"
    if uri != expected_uri:
        errors.append("$.skill.uri: must match skill://<name>/SKILL.md")

    observation_keys = (
        "extension_discovered",
        "skills_list_observed",
        "skills_get_observed",
        "resource_read_observed",
        "skill_entered_model_context",
        "native_skill_selected_automatically",
        "filesystem_copy_absent",
        "standalone_plugin_copy_absent",
        "server_tool_used_after_activation",
    )
    for key in observation_keys:
        if not isinstance(observations.get(key), bool):
            errors.append(f"$.observations.{key}: boolean required")

    level5 = evidence.get("level5_proven")
    strongest_level = evidence.get("strongest_level")
    if not isinstance(level5, bool):
        errors.append("$.evidence.level5_proven: boolean required")
    if not isinstance(strongest_level, int) or not 0 <= strongest_level <= 5:
        errors.append("$.evidence.strongest_level: integer 0..5 required")

    artifacts = evidence.get("artifacts")
    if not isinstance(artifacts, list) or not all(
        isinstance(item, str) for item in artifacts
    ):
        errors.append("$.evidence.artifacts: array of strings required")

    if level5 is True:
        requirements = {
            "extension_discovered": observations.get("extension_discovered"),
            "skills discovery/lookup": observations.get("skills_list_observed")
            or observations.get("skills_get_observed"),
            "resource_read_observed": observations.get("resource_read_observed"),
            "skill_entered_model_context": observations.get(
                "skill_entered_model_context"
            ),
            "native_skill_selected_automatically": observations.get(
                "native_skill_selected_automatically"
            ),
            "filesystem_copy_absent": observations.get("filesystem_copy_absent"),
            "standalone_plugin_copy_absent": observations.get(
                "standalone_plugin_copy_absent"
            ),
            "server_tool_used_after_activation": observations.get(
                "server_tool_used_after_activation"
            ),
        }
        if strongest_level != 5:
            errors.append(
                "$.evidence.strongest_level: must be 5 when level5_proven is true"
            )
        if commit == "0" * 40:
            errors.append("$.server.commit: placeholder SHA cannot prove level 5")
        for requirement, observed in requirements.items():
            if observed is not True:
                errors.append(
                    f"$.evidence.level5_proven: missing prerequisite {requirement}"
                )
    elif strongest_level == 5:
        errors.append(
            "$.evidence.strongest_level: cannot be 5 when level5_proven is false"
        )

    return errors


def validate_file(path: Path) -> list[str]:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except OSError as exc:
        return [f"{path}: cannot read file: {exc}"]
    except json.JSONDecodeError as exc:
        return [f"{path}: invalid JSON: {exc}"]
    return validate_payload(payload)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("paths", nargs="+", type=Path)
    args = parser.parse_args()

    failed = False
    for path in args.paths:
        errors = validate_file(path)
        if errors:
            failed = True
            for error in errors:
                print(f"ERROR: {path}: {error}", file=sys.stderr)
        else:
            print(f"OK: {path}")
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
