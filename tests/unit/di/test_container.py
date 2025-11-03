
from github_stars_contrib_mcp.di.container import (
    get_settings,
    get_stars_api,
    get_stars_client,
)


def test_settings_reads_environment(monkeypatch):
    monkeypatch.setenv("STARS_API_URL", "http://localhost/api")
    monkeypatch.setenv("STARS_API_TOKEN", "token123")
    settings = get_settings()
    assert settings.stars_api_url == "http://localhost/api"
    assert settings.stars_api_token == "token123"


def test_client_built_from_settings(monkeypatch):
    monkeypatch.setenv("STARS_API_URL", "http://localhost/api")
    monkeypatch.setenv("STARS_API_TOKEN", "token123")
    settings = get_settings()
    client = get_stars_client(settings)
    assert client.api_url == "http://localhost/api/"
    assert client.token == "token123"


def test_stars_api_adapter_is_constructed(monkeypatch):
    monkeypatch.setenv("STARS_API_URL", "http://localhost/api")
    monkeypatch.setenv("STARS_API_TOKEN", "token123")
    settings = get_settings()
    adapter = get_stars_api(settings)
    # It should expose an async get_user_data method
    assert hasattr(adapter, "get_user_data")
