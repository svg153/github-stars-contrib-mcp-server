"""Regression coverage for lazy discovery runtime composition."""

from github_stars_contrib_mcp import shared


def test_initialize_discovery_runtime_keeps_default_adapters(monkeypatch) -> None:
    sentinel_repository = object()
    sentinel_runtime = object()
    captured = {}

    monkeypatch.setattr(shared, "discovery_runtime", None)
    monkeypatch.setattr(
        shared,
        "initialize_discovery_repository",
        lambda: sentinel_repository,
    )

    def fake_build_discovery_runtime(**kwargs):
        captured.update(kwargs)
        return sentinel_runtime

    monkeypatch.setattr(shared, "build_discovery_runtime", fake_build_discovery_runtime)

    result = shared.initialize_discovery_runtime()

    assert result is sentinel_runtime
    assert captured["repository"] is sentinel_repository
    assert captured["adapters"] is None
