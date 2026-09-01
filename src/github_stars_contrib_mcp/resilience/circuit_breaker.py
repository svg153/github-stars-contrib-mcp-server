"""
Circuit breaker pattern for API resilience.
Prevents cascading failures and provides fallback strategies.
"""

import asyncio
import time
from collections.abc import Callable
from enum import Enum
from typing import Any

import structlog

logger = structlog.get_logger(__name__)


class CircuitState(Enum):
    """Circuit breaker states."""

    CLOSED = "closed"
    OPEN = "open"
    HALF_OPEN = "half_open"


class CircuitBreakerException(Exception):
    """Raised when circuit breaker is open."""


class CircuitBreaker:
    """
    Circuit breaker for handling transient failures.

    States:
    - CLOSED: Normal operation, all calls proceed
    - OPEN: Failure threshold reached, calls fail immediately
    - HALF_OPEN: Testing if service recovered

    Configuration:
    - failure_threshold: Number of failures before opening (default: 5)
    - recovery_timeout: Seconds to wait before half-open (default: 60)
    - success_threshold: Successes in half-open to close (default: 2)
    """

    def __init__(
        self,
        name: str,
        failure_threshold: int = 5,
        recovery_timeout: int = 60,
        success_threshold: int = 2,
    ):
        self.name = name
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout
        self.success_threshold = success_threshold

        self.state = CircuitState.CLOSED
        self.failure_count = 0
        self.success_count = 0
        self.last_failure_time: float | None = None
        self._lock = asyncio.Lock()

    def call(self, func: Callable, *args: Any, **kwargs: Any) -> Any:
        """
        Execute function through circuit breaker.

        Raises:
            CircuitBreakerException: If circuit is open
        """
        if self.state == CircuitState.OPEN:
            if self._should_attempt_reset():
                self.state = CircuitState.HALF_OPEN
                self.success_count = 0
                logger.info(
                    "circuit_breaker_half_open",
                    name=self.name,
                    state=self.state.value,
                )
            else:
                raise CircuitBreakerException(f"Circuit breaker '{self.name}' is OPEN")

        try:
            result = func(*args, **kwargs)
            self._on_success()
            return result
        except Exception:
            self._on_failure()
            raise

    async def async_call(self, func: Callable, *args: Any, **kwargs: Any) -> Any:
        """
        Execute async function through circuit breaker.
        Provides thread-safe state management via asyncio.Lock.

        Raises:
            CircuitBreakerException: If circuit is open
        """
        async with self._lock:
            if self.state == CircuitState.OPEN:
                if self._should_attempt_reset():
                    self.state = CircuitState.HALF_OPEN
                    self.success_count = 0
                    logger.info(
                        "circuit_breaker_half_open",
                        name=self.name,
                        state=self.state.value,
                    )
                else:
                    raise CircuitBreakerException(
                        f"Circuit breaker '{self.name}' is OPEN"
                    )

        try:
            result = await func(*args, **kwargs)
            await self._on_success_async()
            return result
        except Exception:
            await self._on_failure_async()
            raise

    def _on_success(self) -> None:
        """Handle successful call."""
        self.failure_count = 0

        if self.state == CircuitState.HALF_OPEN:
            self.success_count += 1
            if self.success_count >= self.success_threshold:
                self.state = CircuitState.CLOSED
                logger.info(
                    "circuit_breaker_closed",
                    name=self.name,
                    state=self.state.value,
                )
        elif self.state == CircuitState.CLOSED:
            logger.debug(
                "circuit_breaker_success",
                name=self.name,
                failure_count=self.failure_count,
            )

    async def _on_success_async(self) -> None:
        """Handle successful async call (thread-safe)."""
        async with self._lock:
            self.failure_count = 0

            if self.state == CircuitState.HALF_OPEN:
                self.success_count += 1
                if self.success_count >= self.success_threshold:
                    self.state = CircuitState.CLOSED
                    logger.info(
                        "circuit_breaker_closed",
                        name=self.name,
                        state=self.state.value,
                    )
            elif self.state == CircuitState.CLOSED:
                logger.debug(
                    "circuit_breaker_success",
                    name=self.name,
                    failure_count=self.failure_count,
                )

    def _on_failure(self) -> None:
        """Handle failed call."""
        self.failure_count += 1
        self.last_failure_time = time.time()

        logger.warning(
            "circuit_breaker_failure",
            name=self.name,
            failure_count=self.failure_count,
            threshold=self.failure_threshold,
            state=self.state.value,
        )

        if self.failure_count >= self.failure_threshold:
            self.state = CircuitState.OPEN
            logger.error(
                "circuit_breaker_open",
                name=self.name,
                state=self.state.value,
                failures=self.failure_count,
            )

    async def _on_failure_async(self) -> None:
        """Handle failed async call (thread-safe)."""
        async with self._lock:
            self.failure_count += 1
            self.last_failure_time = time.time()

            logger.warning(
                "circuit_breaker_failure",
                name=self.name,
                failure_count=self.failure_count,
                threshold=self.failure_threshold,
                state=self.state.value,
            )

            if self.failure_count >= self.failure_threshold:
                self.state = CircuitState.OPEN
                logger.error(
                    "circuit_breaker_open",
                    name=self.name,
                    state=self.state.value,
                    failures=self.failure_count,
                )

    def _should_attempt_reset(self) -> bool:
        """Check if enough time has passed to attempt recovery."""
        if self.last_failure_time is None:
            return False

        elapsed = time.time() - self.last_failure_time
        return elapsed >= self.recovery_timeout

    def get_state(self) -> dict[str, Any]:
        """Get circuit breaker state for monitoring."""
        return {
            "name": self.name,
            "state": self.state.value,
            "failure_count": self.failure_count,
            "success_count": self.success_count,
            "last_failure_time": self.last_failure_time,
        }


class CircuitBreakerRegistry:
    """Registry to manage multiple circuit breakers."""

    def __init__(self):
        self._breakers: dict[str, CircuitBreaker] = {}

    def get_or_create(
        self,
        name: str,
        failure_threshold: int = 5,
        recovery_timeout: int = 60,
        success_threshold: int = 2,
    ) -> CircuitBreaker:
        """Get existing or create new circuit breaker."""
        if name not in self._breakers:
            self._breakers[name] = CircuitBreaker(
                name=name,
                failure_threshold=failure_threshold,
                recovery_timeout=recovery_timeout,
                success_threshold=success_threshold,
            )
        return self._breakers[name]

    def get_all_states(self) -> dict[str, dict[str, Any]]:
        """Get state of all circuit breakers."""
        return {name: breaker.get_state() for name, breaker in self._breakers.items()}

    def reset_all(self) -> None:
        """Reset all circuit breakers to CLOSED state."""
        for breaker in self._breakers.values():
            breaker.state = CircuitState.CLOSED
            breaker.failure_count = 0
            breaker.success_count = 0
        logger.info("circuit_breaker_reset_all", count=len(self._breakers))


# Global registry
circuit_breaker_registry = CircuitBreakerRegistry()
