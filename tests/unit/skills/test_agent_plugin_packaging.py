"""Safety contracts for Agent Plugins portable packaging."""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[3]
PLUGIN_SCHEMA = "https://agent-plugins.org/schemas/1.0.0/plugin.schema.json"
MCP_SCHEMA = "https://agent-plugins.org/schemas/1.0.0/mcp.schema.json"

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


def _load_json(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    assert isinstance(payload, dict)
    return payload


def _secret_findings(value: Any, path: str = "$") -> list[str]:
    findings: list[str] = []
    if isinstance(value, dict):
        for key, child in value.items():
            lowered = str(key).casefold()
            if any(part in lowered for part in SECRET_KEY_PARTS):
                findings.append(f"{path}.{key}: credential-like key")
            findings.extend(_secret_findings(child, f"{path}.{key}"))
    elif isinstance(value, list):
        for index, child in enumerate(value):
            findings.extend(_secret_findings(child, f"{path}[{index}]"))
    elif isinstance(value, str):
        for pattern in SECRET_VALUE_PATTERNS:
            if pattern.search(value):
                findings.append(f"{path}: credential-like value")
                break
    return findings


def test_agent_plugin_targets_published_1_0_schema() -> None:
    plugin = _load_json(ROOT / "plugin.json")
    assert plugin["$schema"] == PLUGIN_SCHEMA


def test_future_portable_mcp_metadata_is_version_aligned_and_secret_free() -> None:
    """Keep future mcp.json safe even before #60 is ready to ship it."""

    mcp_path = ROOT / "mcp.json"
    if not mcp_path.exists():
        return

    plugin = _load_json(ROOT / "plugin.json")
    mcp = _load_json(mcp_path)

    assert plugin["$schema"] == PLUGIN_SCHEMA
    assert mcp["$schema"] == MCP_SCHEMA
    assert set(mcp) == {"$schema", "mcpServers"}
    assert isinstance(mcp["mcpServers"], dict)

    findings = _secret_findings(mcp)
    assert not findings, (
        "portable plugin metadata must not contain secrets: " + "; ".join(findings)
    )

    for name, server in mcp["mcpServers"].items():
        assert isinstance(name, str) and name
        assert isinstance(server, dict)
        if server.get("type") == "stdio":
            env = server.get("env", {})
            assert isinstance(env, dict)
            assert "PLUGIN_ROOT" not in env
            assert "PLUGIN_DATA" not in env
            # Agent Plugins 1.0 permits clients to sanitize ambient variables. A
            # portable Stars launcher must not smuggle its auth dependency into
            # visible package metadata either.
            assert "STARS_API_TOKEN" not in env
            assert "GITHUB_DISCOVERY_TOKEN" not in env
            assert "YOUTUBE_API_KEY" not in env
