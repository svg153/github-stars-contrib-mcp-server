"""Resilience patterns for fault tolerance."""

from .circuit_breaker import (
    CircuitBreaker,
    CircuitBreakerException,
    CircuitBreakerRegistry,
    CircuitState,
    circuit_breaker_registry,
)

__all__ = [
    "CircuitBreaker",
    "CircuitBreakerException",
    "CircuitBreakerRegistry",
    "CircuitState",
    "circuit_breaker_registry",
]
