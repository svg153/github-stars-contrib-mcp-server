"""Integration-level pytest fixtures."""

from __future__ import annotations

import os
import socket
import subprocess
import sys
import time
from collections.abc import Iterator
from contextlib import closing

import pytest

from github_stars_contrib_mcp import shared
from github_stars_contrib_mcp.utils.stars_client import StarsClient


@pytest.fixture
def require_token():
    if not os.getenv("STARS_API_TOKEN"):
        pytest.skip("STARS_API_TOKEN not set; skipping integration test")


@pytest.fixture
def mutations_enabled(require_token):
    allow = os.getenv("STARS_E2E_MUTATE", "0") in ("1", "true", "True")
    if not allow:
        pytest.skip(
            "Mutation e2e disabled; set STARS_API_TOKEN and STARS_E2E_MUTATE=1 to run"
        )


@pytest.fixture
def stars_client_real(require_token) -> StarsClient:
    api_url = os.getenv("STARS_API_URL", "https://api-stars.github.com/")
    contributions_api_url = os.getenv(
        "STARS_CONTRIBUTIONS_API_URL",
        "https://stars.github.com/api/contributions",
    )
    token = os.getenv("STARS_API_TOKEN") or ""
    return StarsClient(
        api_url=api_url,
        contributions_api_url=contributions_api_url,
        token=token,
    )


@pytest.fixture
def wire_shared_real_client(stars_client_real):
    original = shared.stars_client
    shared.stars_client = stars_client_real
    try:
        yield stars_client_real
    finally:
        shared.stars_client = original


def _find_free_port() -> int:
    with closing(socket.socket(socket.AF_INET, socket.SOCK_STREAM)) as sock:
        sock.bind(("127.0.0.1", 0))
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        return sock.getsockname()[1]


def _wait_for_port(host: str, port: int, timeout: float = 10.0) -> bool:
    deadline = time.time() + timeout
    while time.time() < deadline:
        try:
            with closing(socket.create_connection((host, port), timeout=0.5)):
                return True
        except OSError:
            time.sleep(0.1)
    return False


@pytest.fixture(scope="session")
def mcp_server() -> Iterator[str]:
    host = os.getenv("MCP_HOST", "127.0.0.1")
    port = int(os.getenv("MCP_PORT", str(_find_free_port())))
    path = os.getenv("MCP_PATH", "/mcp")

    env = os.environ.copy()
    env.setdefault("MCP_TRANSPORT", "streamable-http")
    env["MCP_HOST"] = host
    env["MCP_PORT"] = str(port)
    env["MCP_PATH"] = path
    if not env.get("STARS_API_TOKEN"):
        env["DANGEROUSLY_OMIT_AUTH"] = "true"

    proc = subprocess.Popen(
        [sys.executable, "-m", "github_stars_contrib_mcp.server"],
        env=env,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )

    if not _wait_for_port(host, port, timeout=15.0):
        proc.kill()
        try:
            out, err = proc.communicate(timeout=2)
        except Exception as exc:
            pytest.fail(
                f"MCP server failed to start on {host}:{port}; output unavailable: {exc}"
            )
        pytest.fail(
            f"MCP server failed to start on {host}:{port}.\n"
            f"STDOUT:\n{out.decode()}\nSTDERR:\n{err.decode()}"
        )

    try:
        yield f"http://{host}:{port}{path}"
    finally:
        proc.terminate()
        try:
            proc.wait(timeout=5)
        except subprocess.TimeoutExpired:
            proc.kill()
