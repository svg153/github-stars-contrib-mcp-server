import json

import pytest

import github_stars_contrib_mcp.utils.stars_client as sc_mod
from github_stars_contrib_mcp.utils.stars_client import StarsClient


class _DummyResp:
    def __init__(self, status_code=200, data=None, text="{}"):
        self.status_code = status_code
        self._data = data if data is not None else {"data": {"ok": True}}
        self.text = text

    def json(self):
        return self._data


class _DummyClient:
    def __init__(self, resp: _DummyResp):
        self._resp = resp

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc, tb):
        return False

    async def post(self, url, json=None):  # noqa: A002 - shadowing json param acceptable in test
        return self._resp


class _LogCapture:
    def __init__(self):
        self.debugs = []
        self.infos = []
        self.warnings = []
        self.errors = []

    def debug(self, event, **kwargs):
        self.debugs.append((event, kwargs))

    def info(self, event, **kwargs):
        self.infos.append((event, kwargs))

    def warning(self, event, **kwargs):
        self.warnings.append((event, kwargs))

    def error(self, event, **kwargs):
        self.errors.append((event, kwargs))


@pytest.mark.asyncio
async def test_execute_graphql_success_logs_op_and_duration(monkeypatch):
    log = _LogCapture()
    monkeypatch.setattr(sc_mod, "logger", log)
    dummy = _DummyResp(
        status_code=200,
        data={"data": {"ok": True}},
        text=json.dumps({"data": {"ok": True}}),
    )
    monkeypatch.setattr(
        sc_mod.httpx, "AsyncClient", lambda **kwargs: _DummyClient(dummy)
    )

    client = StarsClient(api_url="https://api-stars.local/graphql", token="t")
    res = await client._execute_graphql("query Q{ ok }", op="unitOp")

    assert res["ok"] is True
    assert log.infos, "expected an info log"
    event, fields = log.infos[-1]
    assert event == "stars_client.request_ok"
    assert fields.get("op") == "unitOp"
    assert isinstance(fields.get("duration_ms"), int)
    assert fields.get("http_status") == 200


@pytest.mark.asyncio
async def test_execute_graphql_debug_log_redacts_sensitive_variables(monkeypatch):
    log = _LogCapture()
    monkeypatch.setattr(sc_mod, "logger", log)
    dummy = _DummyResp(status_code=200, data={"data": {"ok": True}})
    monkeypatch.setattr(
        sc_mod.httpx, "AsyncClient", lambda **kwargs: _DummyClient(dummy)
    )

    client = StarsClient(api_url="https://api-stars.local/graphql", token="t")
    await client._execute_graphql(
        "query Q($input: JSON){ ok }",
        variables={
            "token": "secret-token",
            "name": "visible",
            "nested": {"password": "secret-password"},
        },
        op="redaction",
    )

    assert log.debugs, "expected a debug log"
    event, fields = log.debugs[-1]
    assert event == "stars_client.graphql_request"
    assert fields["variables"] == {
        "token": "<redacted>",
        "name": "visible",
        "nested": {"password": "<redacted>"},
    }


@pytest.mark.asyncio
async def test_execute_graphql_permanent_http_error_logs_failed(monkeypatch):
    log = _LogCapture()
    monkeypatch.setattr(sc_mod, "logger", log)
    # 4xx is intentionally permanent. 429 and 5xx are covered by retry tests.
    dummy = _DummyResp(status_code=400, data={"message": "bad request"}, text="boom")
    monkeypatch.setattr(
        sc_mod.httpx, "AsyncClient", lambda **kwargs: _DummyClient(dummy)
    )

    client = StarsClient(api_url="https://api-stars.local/graphql", token="t")
    res = await client._execute_graphql("mutation M{ ok }", op="unitOpErr")

    assert res["ok"] is False
    assert log.warnings, "expected a warning log"
    event, fields = log.warnings[-1]
    assert event == "stars_client.request_failed"
    assert fields.get("op") == "unitOpErr"
    assert fields.get("http_status") == 400
    assert isinstance(fields.get("duration_ms"), int)
    assert fields.get("error_kind") == "http_error"
