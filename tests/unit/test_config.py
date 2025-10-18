"""Unit tests for config module."""

import pytest
from unittest.mock import patch
from pydantic import ValidationError

from github_stars_contrib_mcp.config import Settings


class TestSettings:
    @patch.dict("os.environ", {}, clear=True)
    def test_default_settings(self):
        settings = Settings()
        assert settings.stars_api_token is None
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

    def test_with_token(self):
        settings = Settings(stars_api_token="test_token", log_level="DEBUG", dangerously_omit_auth=True)
        assert settings.stars_api_token == "test_token"
        assert settings.log_level == "DEBUG"
        assert settings.dangerously_omit_auth is True