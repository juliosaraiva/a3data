"""Retry mechanism with exponential backoff for LLM clients."""

from __future__ import annotations

import asyncio
import logging
import random
import time
from collections.abc import Callable
from typing import Any, TypeVar

T = TypeVar("T")

logger = logging.getLogger(__name__)


class RetryConfig:
    """Configuration for retry mechanism."""

    def __init__(
        self,
        max_attempts: int = 3,
        base_delay: float = 1.0,
        max_delay: float = 60.0,
        exponential_base: float = 2.0,
        jitter: bool = True,
        retryable_exceptions: tuple[type[Exception], ...] = (Exception,),
    ):
        """Initialize retry configuration.

        Args:
            max_attempts: Maximum number of retry attempts
            base_delay: Base delay in seconds for first retry
            max_delay: Maximum delay in seconds
            exponential_base: Base for exponential backoff calculation
            jitter: Whether to add random jitter to delay
            retryable_exceptions: Exception types that should trigger retry
        """
        self.max_attempts = max_attempts
        self.base_delay = base_delay
        self.max_delay = max_delay
        self.exponential_base = exponential_base
        self.jitter = jitter
        self.retryable_exceptions = retryable_exceptions


class RetryAttempt:
    """Information about a retry attempt."""

    def __init__(self, attempt_number: int, delay: float, exception: Exception | None = None):
        """Initialize retry attempt info.

        Args:
            attempt_number: Current attempt number (1-based)
            delay: Delay before this attempt in seconds
            exception: Exception from previous attempt
        """
        self.attempt_number = attempt_number
        self.delay = delay
        self.exception = exception
        self.timestamp = time.time()


class RetryExhaustedError(Exception):
    """Raised when all retry attempts are exhausted."""

    def __init__(self, attempts: list[RetryAttempt], last_exception: Exception):
        """Initialize retry exhausted error.

        Args:
            attempts: List of all retry attempts made
            last_exception: Final exception that caused failure
        """
        super().__init__(f"Retry attempts exhausted after {len(attempts)} attempts. Last error: {last_exception}")
        self.attempts = attempts
        self.last_exception = last_exception


async def retry_with_backoff[T](func: Callable[..., T], config: RetryConfig, *args: Any, **kwargs: Any) -> T:
    """Execute function with retry and exponential backoff.

    Args:
        func: Function to execute
        config: Retry configuration
        *args: Positional arguments for function
        **kwargs: Keyword arguments for function

    Returns:
        Function result

    Raises:
        RetryExhaustedError: If all retry attempts fail
        Original exception: If it's not retryable
    """
    attempts: list[RetryAttempt] = []
    last_exception: Exception | None = None

    for attempt in range(config.max_attempts):
        try:
            # Calculate delay for this attempt
            if attempt == 0:
                delay = 0.0  # No delay for first attempt
            else:
                delay = min(config.base_delay * (config.exponential_base ** (attempt - 1)), config.max_delay)

                if config.jitter:
                    # Add random jitter (±25% of delay)
                    jitter_amount = delay * 0.25
                    delay += random.uniform(-jitter_amount, jitter_amount)

            # Record attempt
            attempt_info = RetryAttempt(attempt_number=attempt + 1, delay=delay, exception=last_exception)
            attempts.append(attempt_info)

            # Apply delay if not first attempt
            if delay > 0:
                logger.debug(f"Retrying after {delay:.2f}s (attempt {attempt + 1}/{config.max_attempts})")
                await asyncio.sleep(delay)

            # Execute function
            if asyncio.iscoroutinefunction(func):
                result = await func(*args, **kwargs)
            else:
                result = func(*args, **kwargs)

            # Success
            if attempts:
                logger.info(f"Function succeeded after {len(attempts)} attempts")
            return result

        except config.retryable_exceptions as e:
            last_exception = e
            logger.warning(f"Attempt {attempt + 1}/{config.max_attempts} failed: {e}")

            # If this was the last attempt, raise RetryExhaustedError
            if attempt == config.max_attempts - 1:
                raise RetryExhaustedError(attempts, e) from e

        except Exception as e:
            # Non-retryable exception, re-raise immediately
            logger.error(f"Non-retryable exception occurred: {e}")
            raise e

    # This should not be reached, but just in case
    raise RetryExhaustedError(attempts, last_exception or Exception("Unknown error"))


class RetryableClient:
    """Mixin class to add retry functionality to LLM clients."""

    def __init__(self, retry_config: RetryConfig | None = None):
        """Initialize retryable client.

        Args:
            retry_config: Configuration for retry behavior
        """
        self.retry_config = retry_config or RetryConfig()

    async def execute_with_retry(self, func: Callable[..., T], *args: Any, **kwargs: Any) -> T:
        """Execute function with retry logic.

        Args:
            func: Function to execute
            *args: Positional arguments for function
            **kwargs: Keyword arguments for function

        Returns:
            Function result
        """
        return await retry_with_backoff(func, self.retry_config, *args, **kwargs)
