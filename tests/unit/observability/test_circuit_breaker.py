"""Tests for circuit breaker and resilience patterns."""

import time

import pytest

from github_stars_contrib_mcp.resilience import (
    CircuitBreaker,
    CircuitBreakerException,
    CircuitState,
)


class TestCircuitBreaker:
    """Tests for CircuitBreaker."""

    def test_closed_state_allows_calls(self):
        """Test that CLOSED state allows function calls."""
        breaker = CircuitBreaker("test", failure_threshold=3)

        def success_func():
            return "success"

        result = breaker.call(success_func)
        assert result == "success"
        assert breaker.state == CircuitState.CLOSED

    def test_failure_threshold_opens_circuit(self):
        """Test circuit opens after failure threshold."""
        breaker = CircuitBreaker("test", failure_threshold=3)

        def failing_func():
            raise Exception("Service error")

        # First 3 calls fail
        for i in range(3):
            with pytest.raises(Exception):
                breaker.call(failing_func)

        # Circuit should be OPEN
        assert breaker.state == CircuitState.OPEN
        assert breaker.failure_count == 3

    def test_open_circuit_rejects_calls(self):
        """Test that OPEN circuit rejects new calls."""
        breaker = CircuitBreaker("test", failure_threshold=1)

        def failing_func():
            raise Exception("Error")

        # Open the circuit
        with pytest.raises(Exception):
            breaker.call(failing_func)

        assert breaker.state == CircuitState.OPEN

        # Further calls should fail immediately
        with pytest.raises(CircuitBreakerException):
            breaker.call(failing_func)

    def test_half_open_retries_after_timeout(self):
        """Test HALF_OPEN state retries after recovery timeout."""
        breaker = CircuitBreaker(
            "test",
            failure_threshold=1,
            recovery_timeout=0.1,  # type: ignore[arg-type]
            success_threshold=1,
        )

        def failing_func():
            raise Exception("Error")

        # Open the circuit
        with pytest.raises(Exception):
            breaker.call(failing_func)

        assert breaker.state == CircuitState.OPEN

        # Wait for recovery timeout
        time.sleep(0.15)

        # Next call should attempt recovery (HALF_OPEN)
        def success_func():
            return "recovered"

        result = breaker.call(success_func)
        assert result == "recovered"
        assert breaker.state == CircuitState.CLOSED

    def test_get_state(self):
        """Test get_state returns correct info."""
        breaker = CircuitBreaker("test_service")
        state = breaker.get_state()

        assert state["name"] == "test_service"
        assert state["state"] == "closed"
        assert state["failure_count"] == 0

    def test_success_resets_failure_count(self):
        """Test success resets failure count."""
        breaker = CircuitBreaker("test", failure_threshold=3)

        def failing_func():
            raise Exception("Error")

        # Fail once
        with pytest.raises(Exception):
            breaker.call(failing_func)

        assert breaker.failure_count == 1

        # Success resets count
        def success_func():
            return "ok"

        breaker.call(success_func)
        assert breaker.failure_count == 0

    def test_half_open_requires_success_threshold(self):
        """Test HALF_OPEN needs multiple successes to close."""
        breaker = CircuitBreaker(
            "test",
            failure_threshold=1,
            recovery_timeout=0.1,  # type: ignore[arg-type]
            success_threshold=2,
        )

        # Open the circuit
        def failing_func():
            raise Exception("Error")

        with pytest.raises(Exception):
            breaker.call(failing_func)

        time.sleep(0.15)

        # First success doesn't close (need 2)
        def success_func():
            return "ok"

        breaker.call(success_func)
        assert breaker.state == CircuitState.HALF_OPEN

        # Second success closes
        breaker.call(success_func)
        assert breaker.state == CircuitState.CLOSED


class TestCircuitBreakerIntegration:
    """Integration tests for circuit breaker."""

    def test_real_world_pattern(self):
        """Test realistic usage pattern."""
        call_count = {"fails": 0, "success": 0}

        def api_call():
            if call_count["fails"] < 2:
                call_count["fails"] += 1
                raise Exception("API error")
            call_count["success"] += 1
            return "result"

        breaker = CircuitBreaker(
            "api",
            failure_threshold=2,
            recovery_timeout=0.1,  # type: ignore[arg-type]
            success_threshold=1,
        )

        # First 2 calls fail, circuit opens
        for _ in range(2):
            with pytest.raises(Exception):
                breaker.call(api_call)

        assert breaker.state == CircuitState.OPEN

        # Wait and retry
        time.sleep(0.15)

        # This should succeed
        result = breaker.call(api_call)
        assert result == "result"
        assert breaker.state == CircuitState.CLOSED
        assert call_count["success"] == 1
