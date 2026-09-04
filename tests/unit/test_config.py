"""Unit tests for config module."""

from pathlib import Path
from unittest.mock import patch

import pytest
from pydantic import ValidationError

from github_stars_contrib_mcp.config import Settings


class TestSettings:
    @patch.dict("os.environ", {}, clear=True)
    def test_default_settings(self):
        settings = Settings()
        assert settings.stars_api_token is None
        assert settings.github_discovery_token is None
        assert settings.stars_auth_mode == "both"
        assert settings.stars_user_agent == "github-stars-contrib-mcp-server/0.3.1"
        assert Path(settings.discovery_db_path).parts[-2:] == (
            "github-stars-contrib-mcp-server",
            "discovery.db",
        )
        assert settings.log_level == "INFO"
        assert settings.dangerously_omit_auth is False

    @pytest.mark.parametrize("level", ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"])
    def test_valid_log_levels(self, level):
        settings = Settings(log_level=level)
        assert settings.log_level == level

    def test_log_level_normalization(self):
        settings = Settings(log_level="debug")
        assert settings.log_level == "DEBUG"

    def test_invalid_log_level(self):
        with pytest.raises(ValidationError):
            Settings(log_level="INVALID")

    @pytest.mark.parametrize("auth_mode", ["both", "bearer", "cookie"])
    def test_valid_auth_modes(self, auth_mode):
        assert Settings(stars_auth_mode=auth_mode).stars_auth_mode == auth_mode

    def test_invalid_auth_mode(self):
        with pytest.raises(ValidationError):
            Settings(stars_auth_mode="invalid")

    def test_user_agent_must_not_be_empty(self):
        with pytest.raises(ValidationError):
            Settings(stars_user_agent="   ")

    def test_discovery_db_path_can_be_overridden(self):
        settings = Settings(discovery_db_path="/tmp/stars-discovery.db")
        assert settings.discovery_db_path == "/tmp/stars-discovery.db"

    def test_with_token(self):
        settings = Settings(
            stars_api_token="test_token",
            github_discovery_token="github_token",
            log_level="DEBUG",
            dangerously_omit_auth=True,
            stars_auth_mode="bearer",
            stars_user_agent="custom-agent/1.0",
        )
        assert settings.stars_api_token == "test_token"
        assert settings.github_discovery_token == "github_token"
        assert settings.log_level == "DEBUG"
        assert settings.dangerously_omit_auth is True
        assert settings.stars_auth_mode == "bearer"
        assert settings.stars_user_agent == "custom-agent/1.0"

    @patch.dict(
        "os.environ",
        {"GITHUB_DISCOVERY_TOKEN": "github-env-token"},
        clear=True,
    )
    def test_github_discovery_token_uses_its_own_environment_variable(self):
        settings = Settings()
        assert settings.github_discovery_token == "github-env-token"
        assert settings.stars_api_token is None
