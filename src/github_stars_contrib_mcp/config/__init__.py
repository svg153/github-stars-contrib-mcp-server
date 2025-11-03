"""Configuration utilities (12-factor friendly).

This package exposes a single `settings` instance loaded from environment
using pydantic-settings to avoid ambiguity between different settings modules.
"""

from .settings import Settings, settings  # re-export for convenient import

__all__ = ["Settings", "settings"]
