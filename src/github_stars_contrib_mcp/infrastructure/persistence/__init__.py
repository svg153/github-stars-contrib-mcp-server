"""Persistence adapters for local discovery state."""

from .discovery_sqlite import SQLiteDiscoveryRepository

__all__ = ["SQLiteDiscoveryRepository"]
