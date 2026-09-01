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


def make_client() -> StarsClient:
    return StarsClient(
        "https://graphql.example",
        "token",
        "https://stars.example/api/contributions",
    )


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
        url="https://example.com",
        description="D",
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
