from github_stars_contrib_mcp.di.container import (
    get_settings,
    get_stars_api,
    get_stars_client,
)


def test_settings_reads_environment(monkeypatch):
    monkeypatch.setenv("STARS_API_URL", "http://localhost/graphql")
    monkeypatch.setenv(
        "STARS_CONTRIBUTIONS_API_URL", "http://localhost/api/contributions"
    )
    monkeypatch.setenv("STARS_API_TOKEN", "token123")
    settings = get_settings()
    assert settings.stars_api_url == "http://localhost/graphql"
    assert settings.stars_contributions_api_url == "http://localhost/api/contributions"
    assert settings.stars_api_token == "token123"


def test_client_built_from_settings(monkeypatch):
    monkeypatch.setenv("STARS_API_URL", "http://localhost/graphql")
    monkeypatch.setenv(
        "STARS_CONTRIBUTIONS_API_URL", "http://localhost/api/contributions"
    )
    monkeypatch.setenv("STARS_API_TOKEN", "token123")
    client = get_stars_client(get_settings())
    assert client.api_url == "http://localhost/graphql/"
    assert client.contributions_api_url == "http://localhost/api/contributions"
    assert client.token == "token123"


def test_stars_api_adapter_is_constructed(monkeypatch):
    monkeypatch.setenv("STARS_API_TOKEN", "token123")
    adapter = get_stars_api(get_settings())
    assert hasattr(adapter, "get_user_data")
    assert hasattr(adapter, "upsert_contribution")
