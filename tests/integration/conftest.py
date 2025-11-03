"""Integration-level pytest fixtures.

These fixtures wire a real StarsClient into shared.stars_client for tool impl
tests, provide gating for token presence and mutation allowance, and can boot
the MCP server for end-to-end scenarios.
"""

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
    """Skip test if STARS_API_TOKEN is not present."""
    if not os.getenv("STARS_API_TOKEN"):
        pytest.skip("STARS_API_TOKEN not set; skipping integration test")


@pytest.fixture
def mutations_enabled(require_token):  # depends on token check
    """Skip test if STARS_E2E_MUTATE is not truthy (1/true/True)."""
    allow = os.getenv("STARS_E2E_MUTATE", "0") in ("1", "true", "True")
    if not allow:
        pytest.skip("Mutation e2e disabled; set STARS_API_TOKEN and STARS_E2E_MUTATE=1 to run")


@pytest.fixture
def stars_client_real(require_token) -> StarsClient:
    """Provide a real StarsClient configured from env vars."""
    api_url = os.getenv("STARS_API_URL", "https://api-stars.github.com/")
    token = os.getenv("STARS_API_TOKEN")
    return StarsClient(api_url=api_url, token=token)


@pytest.fixture
def wire_shared_real_client(stars_client_real):
    """Set shared.stars_client to real client for the duration of the test."""
    original = shared.stars_client
    shared.stars_client = stars_client_real
    try:
        yield stars_client_real
    finally:
        shared.stars_client = original


def _find_free_port() -> int:
    with closing(socket.socket(socket.AF_INET, socket.SOCK_STREAM)) as s:
        s.bind(("127.0.0.1", 0))
        s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        return s.getsockname()[1]


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
    """Start the MCP server with HTTP transport on a free port and yield its URL.

    This fixture does not exercise any tool itself; it only ensures the server
    boots successfully so tests can hit it if they implement an MCP client.
    If STARS_API_TOKEN is not present, it sets DANGEROUSLY_OMIT_AUTH=true to
    allow the server to start with tools disabled.
    """

    host = os.getenv("MCP_HOST", "127.0.0.1")
    port = int(os.getenv("MCP_PORT", str(_find_free_port())))
    path = os.getenv("MCP_PATH", "/mcp")

    env = os.environ.copy()
    env.setdefault("MCP_TRANSPORT", "http")
    env["MCP_HOST"] = host
    env["MCP_PORT"] = str(port)
    env["MCP_PATH"] = path
    # Allow startup without token for read-only/no-op tools
    if not env.get("STARS_API_TOKEN"):
        env["DANGEROUSLY_OMIT_AUTH"] = "true"

    cmd = [sys.executable, "-m", "github_stars_contrib_mcp.server"]
    proc = subprocess.Popen(cmd, env=env, stdout=subprocess.PIPE, stderr=subprocess.PIPE)

    # Wait for port to be ready
    if not _wait_for_port(host, port, timeout=15.0):
        proc.kill()
        try:
            try:
                out, err = proc.communicate(timeout=2)
            except Exception as e:
                pytest.fail(f"MCP server failed to start on {host}:{port}.\nCould not retrieve output: {e}")
            else:
                pytest.fail(f"MCP server failed to start on {host}:{port}.\nSTDOUT:\n{out.decode()}\nSTDERR:\n{err.decode()}")
        except Exception as e:
            pytest.fail(f"MCP server failed to start on {host}:{port}.\nCould not retrieve output: {e}")

    server_url = f"http://{host}:{port}{path}"
    try:
        yield server_url
    finally:
        proc.terminate()
        try:
            proc.wait(timeout=5)
        except subprocess.TimeoutExpired:
            proc.kill()
