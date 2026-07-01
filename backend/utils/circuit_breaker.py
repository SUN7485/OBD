"""Circuit breaker utility for resilient external service calls."""
import time
import logging
from enum import Enum
from typing import Callable, Any, Optional
from dataclasses import dataclass, field

logger = logging.getLogger(__name__)


class CircuitBreakerState(Enum):
    CLOSED = "closed"
    OPEN = "open"
    HALF_OPEN = "half_open"


@dataclass
class CircuitBreaker:
    """Generic circuit breaker with state management."""

    name: str
    failure_threshold: int = 5
    recovery_timeout: float = 30.0
    half_open_max_calls: int = 3

    state: CircuitBreakerState = field(default=CircuitBreakerState.CLOSED, init=False)
    failure_count: int = field(default=0, init=False)
    last_failure_time: float = field(default=0.0, init=False)
    half_open_calls: int = field(default=0, init=False)
    _next_allowed_time: float = field(default=0.0, init=False)

    def can_execute(self) -> bool:
        """Check if execution is allowed based on current state."""
        now = time.time()

        if self.state == CircuitBreakerState.CLOSED:
            return True

        if self.state == CircuitBreakerState.OPEN:
            if now >= self._next_allowed_time:
                self.state = CircuitBreakerState.HALF_OPEN
                self.half_open_calls = 0
                logger.info(f"Circuit breaker {self.name} transitioning to HALF_OPEN")
                return True
            logger.debug(f"Circuit breaker {self.name} is OPEN, retry in {self._next_allowed_time - now:.1f}s")
            return False

        if self.state == CircuitBreakerState.HALF_OPEN:
            if self.half_open_calls < self.half_open_max_calls:
                return True
            logger.debug(f"Circuit breaker {self.name} HALF_OPEN limit reached")
            return False

        return False

    def record_success(self) -> None:
        """Record a successful execution."""
        if self.state == CircuitBreakerState.HALF_OPEN:
            self.half_open_calls += 1
            if self.half_open_calls >= self.half_open_max_calls:
                self.state = CircuitBreakerState.CLOSED
                self.failure_count = 0
                self.last_failure_time = 0.0
                logger.info(f"Circuit breaker {self.name} closed after successful recovery")
        else:
            self.failure_count = 0
            self.last_failure_time = 0.0

    def record_failure(self) -> None:
        """Record a failed execution."""
        self.failure_count += 1
        self.last_failure_time = time.time()

        if self.state == CircuitBreakerState.HALF_OPEN:
            self.state = CircuitBreakerState.OPEN
            self._next_allowed_time = time.time() + self.recovery_timeout
            logger.warning(
                f"Circuit breaker {self.name} re-opened after failure in HALF_OPEN, "
                f"retry in {self.recovery_timeout}s"
            )
            return

        if self.failure_count >= self.failure_threshold:
            self.state = CircuitBreakerState.OPEN
            self._next_allowed_time = time.time() + self.recovery_timeout
            logger.error(
                f"Circuit breaker {self.name} opened after {self.failure_count} failures, "
                f"retry in {self.recovery_timeout}s"
            )

    def get_state(self) -> dict:
        """Get current state for monitoring."""
        return {
            "name": self.name,
            "state": self.state.value,
            "failure_count": self.failure_count,
            "last_failure_ago": (
                time.time() - self.last_failure_time if self.last_failure_time else None
            ),
        }


# Global circuit breakers for key external dependencies
_redis_breaker = CircuitBreaker(name="redis", failure_threshold=5, recovery_timeout=15.0)
_llm_breaker = CircuitBreaker(name="llm", failure_threshold=3, recovery_timeout=60.0)
_db_breaker = CircuitBreaker(name="database", failure_threshold=10, recovery_timeout=10.0)


def get_redis_breaker() -> CircuitBreaker:
    return _redis_breaker


def get_llm_breaker() -> CircuitBreaker:
    return _llm_breaker


def get_db_breaker() -> CircuitBreaker:
    return _db_breaker


async def execute_with_circuit_breaker(
    breaker: CircuitBreaker,
    func: Callable,
    *args: Any,
    fallback: Optional[Callable] = None,
    **kwargs: Any
) -> Any:
    """Execute a callable with circuit breaker protection.

    Args:
        breaker: The circuit breaker instance
        func: The async or sync callable to execute
        *args: Positional arguments for func
        fallback: Optional fallback callable if breaker is open
        **kwargs: Keyword arguments for func

    Returns:
        Result of func or fallback

    Raises:
        RuntimeError: If breaker is open and no fallback provided
    """
    if not breaker.can_execute():
        if fallback is not None:
            logger.warning(f"Circuit breaker {breaker.name} open, using fallback")
            if callable(fallback):
                return await fallback() if asyncio_iscoroutine(fallback) else fallback()
            return fallback
        raise RuntimeError(f"Circuit breaker {breaker.name} is open")

    import asyncio
    try:
        if asyncio.iscoroutinefunction(func):
            result = await func(*args, **kwargs)
        else:
            result = func(*args, **kwargs)
        breaker.record_success()
        return result
    except Exception as e:
        breaker.record_failure()
        raise


def asyncio_iscoroutine(func) -> bool:
    """Check if a function is a coroutine."""
    import asyncio
    import inspect
    return inspect.iscoroutinefunction(func)