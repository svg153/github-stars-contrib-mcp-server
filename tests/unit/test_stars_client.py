"""Unit tests for the hybrid Stars client after the Contributions REST migration."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from github_stars_contrib_mcp.utils.stars_client import StarsClient


@pytest.fixture
def mock_httpx_client():
    with patch("httpx.AsyncClient") as mock_class:
        client = AsyncMock()
        mock_class.return_value.__aenter__.return_value = client
        yield client


def response(status: int, body: dict | None = None, text: str = "") -> MagicMock:
    resp = MagicMock()
    resp.status_code = status
    resp.text = text
    if body is not None:
        resp.json.return_value = body
    return resp


def make_client(**kwargs) -> StarsClient:
    return StarsClient(
        "https://graphql.example",
        "token",
        "https://stars.example/api/contributions",
        **kwargs,
    )


def test_auth_mode_and_user_agent_configuration():
    bearer = make_client(auth_mode="bearer", user_agent="agent/1")
    assert bearer._headers["Authorization"] == "Bearer token"
    assert bearer._headers["User-Agent"] == "agent/1"
    assert bearer._cookies == {}

    cookie = make_client(auth_mode="cookie")
    assert "Authorization" not in cookie._headers
    assert cookie._cookies == {"token": "token"}

    both = make_client(auth_mode="both")
    assert both._headers["Authorization"] == "Bearer token"
    assert both._cookies == {"token": "token"}


def test_invalid_auth_mode_is_rejected():
    with pytest.raises(ValueError, match="auth_mode"):
        make_client(auth_mode="invalid")


@pytest.mark.asyncio
async def test_list_contributions_uses_rest_get(mock_httpx_client):
    mock_httpx_client.request.return_value = response(
        200,
        {
            "data": [{"id": "one", "title": "Hello"}],
            "pagination": {"page": 2, "totalPages": 3},
        },
    )

    result = await make_client().list_contributions(page=2)

    assert result.ok is True
    assert result.data["pagination"]["page"] == 2
    mock_httpx_client.request.assert_awaited_once_with(
        "GET",
        "https://stars.example/api/contributions",
        params={"page": 2},
        json=None,
    )


@pytest.mark.asyncio
async def test_list_contributions_retries_429(mock_httpx_client):
    mock_httpx_client.request.side_effect = [
        response(429, {"message": "rate limited"}),
        response(200, {"data": [], "pagination": {"page": 1}}),
    ]

    result = await make_client().list_contributions(page=1)

    assert result.ok is True
    assert mock_httpx_client.request.await_count == 2


@pytest.mark.asyncio
async def test_rest_retry_exhaustion_returns_controlled_error(mock_httpx_client):
    mock_httpx_client.request.return_value = response(503, {"message": "unavailable"})

    result = await make_client().list_contributions(page=1)

    assert result.ok is False
    assert result.error == "HTTP 503: unavailable"
    assert mock_httpx_client.request.await_count == 3


@pytest.mark.asyncio
async def test_list_contributions_rejects_invalid_page(mock_httpx_client):
    result = await make_client().list_contributions(page=0)

    assert result.ok is False
    assert result.error == "page must be >= 1"
    mock_httpx_client.request.assert_not_awaited()


@pytest.mark.asyncio
async def test_create_contributions_posts_batch(mock_httpx_client):
    mock_httpx_client.request.return_value = response(
        200, {"data": [{"id": "one"}, {"id": "two"}]}
    )
    items = [{"title": "A"}, {"title": "B"}]

    result = await make_client().create_contributions(items)

    assert result.ok is True
    assert result.data["ids"] == ["one", "two"]
    mock_httpx_client.request.assert_awaited_once_with(
        "POST",
        "https://stars.example/api/contributions",
        params=None,
        json={"data": items},
    )


@pytest.mark.asyncio
async def test_create_one_keeps_existing_result_shape(mock_httpx_client):
    mock_httpx_client.request.return_value = response(
        200, {"data": [{"id": "one", "title": "A"}]}
    )

    result = await make_client().create_contribution(
        type="BLOGPOST",
        date="2026-08-25T00:00:00+00:00",
        title="A",
        url="https://example.com?source=test",
        description="",
    )

    assert result.ok is True
    assert result.data["createContribution"]["id"] == "one"


@pytest.mark.asyncio
async def test_upsert_uses_client_id_put(mock_httpx_client):
    mock_httpx_client.request.return_value = response(
        200, {"data": [{"id": "server-id", "title": "A"}]}
    )
    payload = {
        "type": "BLOGPOST",
        "date": "2026-08-25T00:00:00+00:00",
        "title": "A",
        "url": "https://example.com",
        "description": "D",
    }

    result = await make_client().upsert_contribution("stable:blog-1", payload)

    assert result.ok is True
    assert result.data["upsertContribution"]["id"] == "server-id"
    mock_httpx_client.request.assert_awaited_once_with(
        "PUT",
        "https://stars.example/api/contributions/stable%3Ablog-1",
        params=None,
        json=payload,
    )


@pytest.mark.asyncio
async def test_upsert_rejects_invalid_client_id_without_request(mock_httpx_client):
    result = await make_client().upsert_contribution("bad/id", {"title": "A"})

    assert result.ok is False
    assert "client ID" in result.error
    mock_httpx_client.request.assert_not_awaited()


@pytest.mark.asyncio
async def test_legacy_update_is_rejected_to_avoid_duplicate_creation(mock_httpx_client):
    result = await make_client().update_contribution("old-server-id", {"title": "A"})

    assert result.ok is False
    assert "retired" in result.error
    assert "stable caller-controlled client ID" in result.error
    mock_httpx_client.request.assert_not_awaited()


@pytest.mark.asyncio
async def test_delete_is_explicitly_unsupported(mock_httpx_client):
    result = await make_client().delete_contribution("one")

    assert result.ok is False
    assert "does not provide DELETE" in result.error
    mock_httpx_client.request.assert_not_awaited()


@pytest.mark.asyncio
async def test_rest_204_is_accepted(mock_httpx_client):
    mock_httpx_client.request.return_value = response(204)

    result = await make_client().list_contributions(page=1)

    assert result.ok is True
    assert result.data == {}


@pytest.mark.asyncio
async def test_profile_read_stays_on_graphql(mock_httpx_client):
    mock_httpx_client.post.return_value = response(
        200, {"data": {"loggedUser": {"id": "user-1"}}}
    )

    result = await make_client().get_user_data()

    assert result.ok is True
    assert result.data["loggedUser"]["id"] == "user-1"
    mock_httpx_client.post.assert_awaited_once()


@pytest.mark.asyncio
async def test_graphql_retries_429(mock_httpx_client):
    mock_httpx_client.post.side_effect = [
        response(429, {"message": "slow down"}),
        response(200, {"data": {"loggedUser": {"id": "user-1"}}}),
    ]

    result = await make_client().get_user_data()

    assert result.ok is True
    assert mock_httpx_client.post.await_count == 2


@pytest.mark.asyncio
async def test_graphql_invalid_platform_enum_has_hint(mock_httpx_client):
    mock_httpx_client.post.return_value = response(
        200,
        {"errors": [{"message": "PlatformType received invalid enum value"}]},
    )

    result = await make_client().create_link("https://example.com", "INVALID")

    assert result.ok is False
    assert "Valid PlatformType values:" in result.error
    assert "LINKEDIN" in result.error
    assert "DEV_TO" in result.error
