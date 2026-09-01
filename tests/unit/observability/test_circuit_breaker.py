"""Tests for synchronous and asynchronous circuit-breaker behavior."""

import asyncio

import pytest

from github_stars_contrib_mcp.resilience import (
    CircuitBreaker,
    CircuitBreakerException,
    CircuitState,
)


def test_closed_state_allows_calls():
    breaker = CircuitBreaker("unit", failure_threshold=2)
    assert breaker.call(lambda: "ok") == "ok"
    assert breaker.state == CircuitState.CLOSED


def test_failure_threshold_opens_and_rejects_calls():
    breaker = CircuitBreaker("unit", failure_threshold=2)

    def fail() -> None:
        raise RuntimeError("boom")

    for _ in range(2):
        with pytest.raises(RuntimeError):
            breaker.call(fail)
    assert breaker.state == CircuitState.OPEN
    with pytest.raises(CircuitBreakerException):
        breaker.call(fail)


@pytest.mark.asyncio
async def test_async_call_recovers_after_timeout():
    breaker = CircuitBreaker(
        "async-unit", failure_threshold=1, recovery_timeout=0.01, success_threshold=1
    )

    async def fail() -> None:
        raise RuntimeError("boom")

    with pytest.raises(RuntimeError):
        await breaker.async_call(fail)
    assert breaker.state == CircuitState.OPEN
    await asyncio.sleep(0.02)

    async def succeed() -> str:
        return "recovered"

    assert await breaker.async_call(succeed) == "recovered"
    assert breaker.state == CircuitState.CLOSED


def test_get_state_exposes_health_fields():
    state = CircuitBreaker("service").get_state()
    assert state["name"] == "service"
    assert state["state"] == "closed"
    assert state["failure_count"] == 0
