from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
VALIDATOR = ROOT / "scripts" / "validate_mcp_skills_host_evidence.py"
EVIDENCE_DIR = ROOT / "evidence" / "mcp-skills"
TEMPLATE = EVIDENCE_DIR / "TEMPLATE.json"


def _run(path: Path) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, str(VALIDATOR), str(path)],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=False,
    )


def _payload() -> dict[str, object]:
    return json.loads(TEMPLATE.read_text(encoding="utf-8"))


def test_all_committed_host_evidence_is_valid() -> None:
    paths = sorted(EVIDENCE_DIR.glob("*.json"))
    assert paths

    for path in paths:
        result = _run(path)
        assert result.returncode == 0, f"{path}: {result.stderr}"


def test_level5_claim_requires_activation_prerequisites(tmp_path: Path) -> None:
    payload = _payload()
    payload["evidence"]["level5_proven"] = True  # type: ignore[index]
    payload["evidence"]["strongest_level"] = 5  # type: ignore[index]
    path = tmp_path / "claim.json"
    path.write_text(json.dumps(payload), encoding="utf-8")

    result = _run(path)

    assert result.returncode == 1
    assert "missing prerequisite extension_discovered" in result.stderr
    assert "placeholder SHA cannot prove level 5" in result.stderr


def test_level5_claim_passes_with_complete_sanitized_evidence(
    tmp_path: Path,
) -> None:
    payload = _payload()
    payload["server"]["commit"] = "a" * 40  # type: ignore[index]
    observations = payload["observations"]  # type: ignore[assignment]
    assert isinstance(observations, dict)
    for key in observations:
        observations[key] = True
    evidence = payload["evidence"]
    assert isinstance(evidence, dict)
    evidence["level5_proven"] = True
    evidence["strongest_level"] = 5
    path = tmp_path / "claim.json"
    path.write_text(json.dumps(payload), encoding="utf-8")

    result = _run(path)

    assert result.returncode == 0, result.stderr


def test_credential_bearing_fields_are_rejected(tmp_path: Path) -> None:
    payload = _payload()
    payload["debug"] = {"access_token": "redacted"}
    path = tmp_path / "unsafe.json"
    path.write_text(json.dumps(payload), encoding="utf-8")

    result = _run(path)

    assert result.returncode == 1
    assert "credential-bearing key is forbidden" in result.stderr


def test_token_shaped_values_are_rejected(tmp_path: Path) -> None:
    payload = _payload()
    evidence = payload["evidence"]
    assert isinstance(evidence, dict)
    evidence["notes"] = "Bearer abcdefghijklmnopqrstuvwxyz"
    path = tmp_path / "unsafe.json"
    path.write_text(json.dumps(payload), encoding="utf-8")

    result = _run(path)

    assert result.returncode == 1
    assert "token-shaped value is forbidden" in result.stderr
