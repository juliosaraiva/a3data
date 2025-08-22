"""Circuit breaker implementation for LLM client resilience."""

from __future__ import annotations

import asyncio
import time
from collections.abc import Callable
from enum import Enum
from typing import Any, TypeVar

T = TypeVar("T")


class CircuitState(Enum):
    """Circuit breaker states."""

    CLOSED = "closed"  # Normal operation
    OPEN = "open"  # Failing, rejecting requests
    HALF_OPEN = "half_open"  # Testing if service recovered


class CircuitBreakerError(Exception):
    """Raised when circuit breaker is open."""

    def __init__(self, name: str, failure_count: int, last_failure_time: float):
        """Initialize circuit breaker error.

        Args:
            name: Circuit breaker name
            failure_count: Number of consecutive failures
            last_failure_time: Timestamp of last failure
        """
        super().__init__(f"Circuit breaker '{name}' is OPEN. Failures: {failure_count}, Last failure: {last_failure_time}")
        self.name = name
        self.failure_count = failure_count
        self.last_failure_time = last_failure_time


class CircuitBreaker:
    """Circuit breaker pattern implementation for LLM clients."""

    def __init__(
        self,
        name: str,
        failure_threshold: int = 5,
        recovery_timeout: float = 60.0,
        expected_exception: type[Exception] | tuple[type[Exception], ...] = Exception,
    ):
        """Initialize circuit breaker.

        Args:
            name: Unique name for this circuit breaker
            failure_threshold: Number of failures before opening circuit
            recovery_timeout: Seconds to wait before attempting recovery
            expected_exception: Exception types that should trigger circuit breaker
        """
        self.name = name
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout
        self.expected_exception = expected_exception

        self._state = CircuitState.CLOSED
        self._failure_count = 0
        self._last_failure_time = 0.0
        self._next_attempt_time = 0.0

    @property
    def state(self) -> CircuitState:
        """Get current circuit breaker state."""
        return self._state

    @property
    def failure_count(self) -> int:
        """Get current failure count."""
        return self._failure_count

    async def call(self, func: Callable[..., T], *args: Any, **kwargs: Any) -> T:
        """Execute function with circuit breaker protection.

        Args:
            func: Function to execute
            *args: Positional arguments for function
            **kwargs: Keyword arguments for function

        Returns:
            Function result

        Raises:
            CircuitBreakerError: If circuit is open
            Original exception: If function fails but circuit remains closed
        """
        if self._state == CircuitState.OPEN:
            if time.time() < self._next_attempt_time:
                raise CircuitBreakerError(self.name, self._failure_count, self._last_failure_time)
            else:
                self._state = CircuitState.HALF_OPEN

        try:
            result = await func(*args, **kwargs) if asyncio.iscoroutinefunction(func) else func(*args, **kwargs)
            self._on_success()
            return result
        except self.expected_exception as e:
            self._on_failure()
            raise e

    def _on_success(self) -> None:
        """Handle successful function execution."""
        self._failure_count = 0
        self._state = CircuitState.CLOSED

    def _on_failure(self) -> None:
        """Handle failed function execution."""
        self._failure_count += 1
        self._last_failure_time = time.time()

        if self._failure_count >= self.failure_threshold:
            self._state = CircuitState.OPEN
            self._next_attempt_time = time.time() + self.recovery_timeout

    def reset(self) -> None:
        """Reset circuit breaker to closed state."""
        self._state = CircuitState.CLOSED
        self._failure_count = 0
        self._last_failure_time = 0.0
        self._next_attempt_time = 0.0

    def get_status(self) -> dict[str, Any]:
        """Get circuit breaker status information.

        Returns:
            Status dictionary with state, failure count, and timing info
        """
        return {
            "name": self.name,
            "state": self._state.value,
            "failure_count": self._failure_count,
            "failure_threshold": self.failure_threshold,
            "last_failure_time": self._last_failure_time,
            "next_attempt_time": self._next_attempt_time if self._state == CircuitState.OPEN else None,
            "recovery_timeout": self.recovery_timeout,
        }
