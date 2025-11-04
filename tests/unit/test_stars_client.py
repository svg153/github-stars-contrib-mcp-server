"""Unit tests for stars_client module."""

import json
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from github_stars_contrib_mcp.utils.stars_client import StarsClient


class TestStarsClient:
    def test_init(self):
        client = StarsClient("https://api.example.com", "token123")
        assert client.api_url == "https://api.example.com/"
        assert client.token == "token123"

    @pytest.fixture
    def mock_client_class(self):
        with patch("httpx.AsyncClient") as mock_class:
            yield mock_class

    def _setup_mock_response(
        self,
        mock_client_class,
        status_code=200,
        json_data=None,
        json_error=None,
        text="",
    ):
        mock_instance = AsyncMock()
        mock_resp = MagicMock()
        mock_resp.status_code = status_code
        if json_error:
            mock_resp.json.side_effect = json_error
        elif json_data is not None:
            mock_resp.json.return_value = json_data
        mock_resp.text = text
        mock_instance.post.return_value = mock_resp
        mock_client_class.return_value.__aenter__.return_value = mock_instance
        return mock_resp

    @pytest.mark.asyncio
    async def test_create_contributions_success(self, mock_client_class):
        client = StarsClient("https://api.example.com", "token")

        self._setup_mock_response(
            mock_client_class,
            json_data={"data": {"createContributions": [{"id": "1"}, {"id": "2"}]}},
        )

        result = await client.create_contributions([{"title": "Test"}])
        assert result.ok is True
        assert result.data["ids"] == ["1", "2"]

    @pytest.mark.asyncio
    async def test_create_contributions_http_error(self, mock_client_class):
        client = StarsClient("https://api.example.com", "token")

        self._setup_mock_response(
            mock_client_class, status_code=400, text="Bad Request"
        )

        result = await client.create_contributions([{"title": "Test"}])
        assert result.ok is False
        assert result.data is None
        assert "HTTP 400" in result.error

    @pytest.mark.asyncio
    async def test_create_contributions_invalid_json(self, mock_client_class):
        client = StarsClient("https://api.example.com", "token")

        self._setup_mock_response(
            mock_client_class, json_error=json.JSONDecodeError("Invalid", "", 0)
        )

        result = await client.create_contributions([{"title": "Test"}])
        assert result.ok is False
        assert result.error == "Invalid JSON response"

    @pytest.mark.asyncio
    async def test_create_contributions_graphql_error(self, mock_client_class):
        client = StarsClient("https://api.example.com", "token")

        self._setup_mock_response(
            mock_client_class, json_data={"errors": [{"message": "GraphQL error"}]}
        )

        result = await client.create_contributions([{"title": "Test"}])
        assert result.ok is False
        assert result.error == "GraphQL error"

    @pytest.mark.asyncio
    async def test_get_user_data_success(self, mock_client_class):
        client = StarsClient("https://api.example.com", "token")

        self._setup_mock_response(
            mock_client_class, json_data={"data": {"loggedUser": {"id": "u1"}}}
        )

        result = await client.get_user_data()
        assert result.ok is True
        assert result.data == {"loggedUser": {"id": "u1"}}

    @pytest.mark.asyncio
    async def test_update_contribution_success(self, mock_client_class):
        client = StarsClient("https://api.example.com", "token")

        self._setup_mock_response(
            mock_client_class,
            json_data={
                "data": {"updateContribution": {"id": "c1", "title": "Updated"}}
            },
        )

        result = await client.update_contribution("c1", {"title": "Updated"})
        assert result.ok is True
        assert result.data == {"updateContribution": {"id": "c1", "title": "Updated"}}

    @pytest.mark.asyncio
    async def test_delete_contribution_success(self, mock_client_class):
        client = StarsClient("https://api.example.com", "token")

        self._setup_mock_response(
            mock_client_class, json_data={"data": {"deleteContribution": {"id": "c1"}}}
        )

        result = await client.delete_contribution("c1")
        assert result.ok is True
        assert result.data == {"deleteContribution": {"id": "c1"}}

    @pytest.mark.asyncio
    async def test_get_stars_success(self, mock_client_class):
        client = StarsClient("https://api.example.com", "token")

        self._setup_mock_response(
            mock_client_class, json_data={"data": {"publicProfile": {"username": "u"}}}
        )

        result = await client.get_stars("u")
        assert result.ok is True
        assert result.data["publicProfile"]["username"] == "u"

    @pytest.mark.asyncio
    async def test_get_user_success(self, mock_client_class):
        client = StarsClient("https://api.example.com", "token")

        self._setup_mock_response(
            mock_client_class, json_data={"data": {"loggedUser": {"id": "u1"}}}
        )

        result = await client.get_user()
        assert result.ok is True
        assert result.data["loggedUser"]["id"] == "u1"

    @pytest.mark.asyncio
    async def test_update_profile_success(self, mock_client_class):
        client = StarsClient("https://api.example.com", "token")

        self._setup_mock_response(
            mock_client_class, json_data={"data": {"updateProfile": {"id": "p1"}}}
        )

        result = await client.update_profile({"bio": "hi"})
        assert result.ok is True
        assert result.data["updateProfile"]["id"] == "p1"

    # Parametrized error tests
    @pytest.mark.parametrize(
        "method_name, args, expected_key",
        [
            ("get_user_data", (), None),
            ("get_stars", ("u",), "publicProfile"),
            ("get_user", (), "loggedUser"),
            ("update_profile", ({"bio": "hi"},), "updateProfile"),
            ("update_contribution", ("c1", {"title": "Test"}), "updateContribution"),
            ("delete_contribution", ("c1",), "deleteContribution"),
        ],
    )
    @pytest.mark.parametrize(
        "error_type, status_code, json_data, json_error, text, expected_error",
        [
            ("http", 500, None, None, "Server Error", "HTTP 500"),
            ("invalid_json", 200, None, "json_error", "", "Invalid JSON response"),
            (
                "graphql",
                200,
                {"errors": [{"message": "GraphQL error"}]},
                None,
                "",
                "GraphQL error",
            ),
        ],
    )
    @pytest.mark.asyncio
    async def test_method_errors(
        self,
        mock_client_class,
        method_name,
        args,
        expected_key,
        error_type,
        status_code,
        json_data,
        json_error,
        text,
        expected_error,
    ):
        client = StarsClient("https://api.example.com", "token")

        if json_error == "json_error":
            json_error = json.JSONDecodeError("Invalid", "", 0)
        else:
            json_error = None

        self._setup_mock_response(
            mock_client_class,
            status_code=status_code,
            json_data=json_data,
            json_error=json_error,
            text=text,
        )

        method = getattr(client, method_name)
        result = await method(*args)

        assert result.ok is False
        assert expected_error in result.error
