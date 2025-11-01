"""Unit tests for stars_client module."""

import json
from unittest.mock import AsyncMock, patch, MagicMock

import pytest

from github_stars_contrib_mcp.utils.stars_client import StarsClient


class TestStarsClient:
    def test_init(self):
        client = StarsClient("https://api.example.com", "token123")
        assert client.api_url == "https://api.example.com/"
        assert client.token == "token123"

    @pytest.mark.asyncio
    async def test_create_contributions_success(self):
        client = StarsClient("https://api.example.com", "token")
        
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = {"data": {"createContributions": [{"id": "1"}, {"id": "2"}]}}
        
        with patch("httpx.AsyncClient") as mock_client_class:
            mock_client_instance = AsyncMock()
            mock_client_instance.post.return_value = mock_resp
            mock_client_class.return_value.__aenter__.return_value = mock_client_instance
            
            result = await client.create_contributions([{"title": "Test"}])
            assert result.ok is True
            assert result.ids == ["1", "2"]

    @pytest.mark.asyncio
    async def test_create_contributions_http_error(self):
        client = StarsClient("https://api.example.com", "token")
        
        mock_resp = MagicMock()
        mock_resp.status_code = 400
        mock_resp.text = "Bad Request"
        
        with patch("httpx.AsyncClient") as mock_client_class:
            mock_client_instance = AsyncMock()
            mock_client_instance.post.return_value = mock_resp
            mock_client_class.return_value.__aenter__.return_value = mock_client_instance
            
            result = await client.create_contributions([{"title": "Test"}])
            assert result.ok is False
            assert result.ids == []
            assert "HTTP 400" in result.error

    @pytest.mark.asyncio
    async def test_create_contributions_invalid_json(self):
        client = StarsClient("https://api.example.com", "token")
        
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.side_effect = json.JSONDecodeError("Invalid", "", 0)
        
        with patch("httpx.AsyncClient") as mock_client_class:
            mock_client_instance = AsyncMock()
            mock_client_instance.post.return_value = mock_resp
            mock_client_class.return_value.__aenter__.return_value = mock_client_instance
            
            result = await client.create_contributions([{"title": "Test"}])
            assert result.ok is False
            assert result.error == "Invalid JSON response"

    @pytest.mark.asyncio
    async def test_create_contributions_graphql_error(self):
        client = StarsClient("https://api.example.com", "token")
        
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = {"errors": [{"message": "GraphQL error"}]}
        
        with patch("httpx.AsyncClient") as mock_client_class:
            mock_client_instance = AsyncMock()
            mock_client_instance.post.return_value = mock_resp
            mock_client_class.return_value.__aenter__.return_value = mock_client_instance
            
            result = await client.create_contributions([{"title": "Test"}])
            assert result.ok is False
            assert result.error == "GraphQL error"

    @pytest.mark.asyncio
    async def test_get_user_data_success(self):
        client = StarsClient("https://api.example.com", "token")
        
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = {"data": {"loggedUser": {"id": "u1"}}}
        
        with patch("httpx.AsyncClient") as mock_client_class:
            mock_client_instance = AsyncMock()
            mock_client_instance.post.return_value = mock_resp
            mock_client_class.return_value.__aenter__.return_value = mock_client_instance
            
            result = await client.get_user_data()
            assert result["ok"] is True
            assert result["data"] == {"loggedUser": {"id": "u1"}}

    @pytest.mark.asyncio
    async def test_get_user_data_http_error(self):
        client = StarsClient("https://api.example.com", "token")
        
        mock_resp = MagicMock()
        mock_resp.status_code = 500
        mock_resp.text = "Server Error"
        
        with patch("httpx.AsyncClient") as mock_client_class:
            mock_client_instance = AsyncMock()
            mock_client_instance.post.return_value = mock_resp
            mock_client_class.return_value.__aenter__.return_value = mock_client_instance
            
            result = await client.get_user_data()
            assert result["ok"] is False
            assert "HTTP 500" in result["error"]

    @pytest.mark.asyncio
    async def test_get_user_data_invalid_json(self):
        client = StarsClient("https://api.example.com", "token")
        
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.side_effect = json.JSONDecodeError("Invalid", "", 0)
        
        with patch("httpx.AsyncClient") as mock_client_class:
            mock_client_instance = AsyncMock()
            mock_client_instance.post.return_value = mock_resp
            mock_client_class.return_value.__aenter__.return_value = mock_client_instance
            
            result = await client.get_user_data()
            assert result["ok"] is False
            assert result["error"] == "Invalid JSON response"

    @pytest.mark.asyncio
    async def test_get_user_data_graphql_error(self):
        client = StarsClient("https://api.example.com", "token")
        
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = {"errors": [{"message": "GraphQL error"}]}
        
        with patch("httpx.AsyncClient") as mock_client_class:
            mock_client_instance = AsyncMock()
            mock_client_instance.post.return_value = mock_resp
            mock_client_class.return_value.__aenter__.return_value = mock_client_instance
            
            result = await client.get_user_data()
            assert result["ok"] is False
            assert result["error"] == "GraphQL error"

    @pytest.mark.asyncio
    async def test_update_contribution_success(self):
        client = StarsClient("https://api.example.com", "token")
        
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = {"data": {"updateContribution": {"id": "c1", "title": "Updated"}}}
        
        with patch("httpx.AsyncClient") as mock_client_class:
            mock_client_instance = AsyncMock()
            mock_client_instance.post.return_value = mock_resp
            mock_client_class.return_value.__aenter__.return_value = mock_client_instance
            
            result = await client.update_contribution("c1", {"title": "Updated"})
            assert result["ok"] is True
            assert result["data"] == {"updateContribution": {"id": "c1", "title": "Updated"}}

    @pytest.mark.asyncio
    async def test_update_contribution_http_error(self):
        client = StarsClient("https://api.example.com", "token")
        
        mock_resp = MagicMock()
        mock_resp.status_code = 400
        mock_resp.text = "Bad Request"
        
        with patch("httpx.AsyncClient") as mock_client_class:
            mock_client_instance = AsyncMock()
            mock_client_instance.post.return_value = mock_resp
            mock_client_class.return_value.__aenter__.return_value = mock_client_instance
            
            result = await client.update_contribution("c1", {"title": "Test"})
            assert result["ok"] is False
            assert "HTTP 400" in result["error"]

    @pytest.mark.asyncio
    async def test_update_contribution_invalid_json(self):
        client = StarsClient("https://api.example.com", "token")
        
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.side_effect = json.JSONDecodeError("Invalid", "", 0)
        
        with patch("httpx.AsyncClient") as mock_client_class:
            mock_client_instance = AsyncMock()
            mock_client_instance.post.return_value = mock_resp
            mock_client_class.return_value.__aenter__.return_value = mock_client_instance
            
            result = await client.update_contribution("c1", {"title": "Test"})
            assert result["ok"] is False
            assert result["error"] == "Invalid JSON response"

    @pytest.mark.asyncio
    async def test_update_contribution_graphql_error(self):
        client = StarsClient("https://api.example.com", "token")
        
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = {"errors": [{"message": "GraphQL error"}]}
        
        with patch("httpx.AsyncClient") as mock_client_class:
            mock_client_instance = AsyncMock()
            mock_client_instance.post.return_value = mock_resp
            mock_client_class.return_value.__aenter__.return_value = mock_client_instance
            
            result = await client.update_contribution("c1", {"title": "Test"})
            assert result["ok"] is False
            assert result["error"] == "GraphQL error"

    @pytest.mark.asyncio
    async def test_delete_contribution_success(self):
        client = StarsClient("https://api.example.com", "token")
        
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = {"data": {"deleteContribution": {"id": "c1"}}}
        
        with patch("httpx.AsyncClient") as mock_client_class:
            mock_client_instance = AsyncMock()
            mock_client_instance.post.return_value = mock_resp
            mock_client_class.return_value.__aenter__.return_value = mock_client_instance
            
            result = await client.delete_contribution("c1")
            assert result["ok"] is True
            assert result["data"] == {"deleteContribution": {"id": "c1"}}

    @pytest.mark.asyncio
    async def test_delete_contribution_http_error(self):
        client = StarsClient("https://api.example.com", "token")
        
        mock_resp = MagicMock()
        mock_resp.status_code = 500
        mock_resp.text = "Server Error"
        
        with patch("httpx.AsyncClient") as mock_client_class:
            mock_client_instance = AsyncMock()
            mock_client_instance.post.return_value = mock_resp
            mock_client_class.return_value.__aenter__.return_value = mock_client_instance
            
            result = await client.delete_contribution("c1")
            assert result["ok"] is False
            assert "HTTP 500" in result["error"]

    @pytest.mark.asyncio
    async def test_delete_contribution_invalid_json(self):
        client = StarsClient("https://api.example.com", "token")
        
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.side_effect = json.JSONDecodeError("Invalid", "", 0)
        
        with patch("httpx.AsyncClient") as mock_client_class:
            mock_client_instance = AsyncMock()
            mock_client_instance.post.return_value = mock_resp
            mock_client_class.return_value.__aenter__.return_value = mock_client_instance
            
            result = await client.delete_contribution("c1")
            assert result["ok"] is False
            assert result["error"] == "Invalid JSON response"

    @pytest.mark.asyncio
    async def test_delete_contribution_graphql_error(self):
        client = StarsClient("https://api.example.com", "token")
        
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = {"errors": [{"message": "GraphQL error"}]}
        
        with patch("httpx.AsyncClient") as mock_client_class:
            mock_client_instance = AsyncMock()
            mock_client_instance.post.return_value = mock_resp
            mock_client_class.return_value.__aenter__.return_value = mock_client_instance
            
            result = await client.delete_contribution("c1")
            assert result["ok"] is False
            assert result["error"] == "GraphQL error"

    @pytest.mark.asyncio
    async def test_get_stars_success(self):
        client = StarsClient("https://api.example.com", "token")

        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = {"data": {"publicProfile": {"username": "u"}}}

        with patch("httpx.AsyncClient") as mock_client_class:
            mock_client_instance = AsyncMock()
            mock_client_instance.post.return_value = mock_resp
            mock_client_class.return_value.__aenter__.return_value = mock_client_instance

            result = await client.get_stars("u")
            assert result["ok"] is True
            assert result["data"]["publicProfile"]["username"] == "u"

        
    @pytest.mark.asyncio
    async def test_get_user_success(self):
        client = StarsClient("https://api.example.com", "token")

        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = {"data": {"loggedUser": {"id": "u1"}}}

        with patch("httpx.AsyncClient") as mock_client_class:
            mock_client_instance = AsyncMock()
            mock_client_instance.post.return_value = mock_resp
            mock_client_class.return_value.__aenter__.return_value = mock_client_instance

            result = await client.get_user()
            assert result["ok"] is True
            assert result["data"]["loggedUser"]["id"] == "u1"

    @pytest.mark.asyncio
    async def test_update_profile_success(self):
        client = StarsClient("https://api.example.com", "token")

        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = {"data": {"updateProfile": {"id": "p1"}}}

        with patch("httpx.AsyncClient") as mock_client_class:
            mock_client_instance = AsyncMock()
            mock_client_instance.post.return_value = mock_resp
            mock_client_class.return_value.__aenter__.return_value = mock_client_instance

            result = await client.update_profile({"bio": "hi"})
            assert result["ok"] is True
            assert result["data"]["updateProfile"]["id"] == "p1"