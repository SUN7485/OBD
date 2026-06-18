"""Rate limiting middleware using slowapi with Redis backend."""

import logging
from typing import Optional

from fastapi import Request, HTTPException, status
from slowapi import Limiter
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded

from backend.config.settings import settings

logger = logging.getLogger(__name__)


def get_user_identifier(request: Request) -> str:
    """
    Get user identifier for rate limiting.

    Uses user_id if authenticated, otherwise falls back to IP.
    """
    # Try to get user ID from request state (set by auth middleware)
    if hasattr(request.state, "user_id") and request.state.user_id:
        return f"user:{request.state.user_id}"

    # Fall back to IP address
    return get_remote_address(request)


# Create limiter with Redis storage
limiter = Limiter(key_func=get_user_identifier, storage_uri=settings.REDIS_URL)


# Rate limit configurations
RATE_LIMITS = {
    # Telemetry ingestion: 100/minute per car
    "telemetry_ingest": "100/minute",
    # AI chat: 10/minute per user
    "ai_chat": "10/minute",
    # General API: 1000/hour per user
    "default": "1000/hour",
    # WebSocket: 60/minute per user
    "websocket": "60/minute",
}


def get_rate_limit_key(endpoint: str, user_id: Optional[str] = None) -> str:
    """Get rate limit key for an endpoint."""
    if user_id:
        return f"{endpoint}:{user_id}"
    return endpoint


class RateLimiter:
    """Rate limiter wrapper with custom logic."""

    def __init__(self):
        self.limiter = limiter

    async def check_rate_limit(self, request: Request, limit: str) -> bool:
        """
        Check if request is within rate limit.

        Args:
            request: FastAPI request
            limit: Rate limit string (e.g., "100/minute")

        Returns:
            True if within limit

        Raises:
            RateLimitExceeded: If limit exceeded
        """
        # Check using slowapi's limiter
        if self.limiter._is_rate_limited(limit, request):
            raise RateLimitExceeded(detail=f"Rate limit exceeded: {limit}")
        return True


# Global instance
rate_limiter = RateLimiter()


async def rate_limit_exceeded_handler(request: Request, exc: RateLimitExceeded):
    """Custom handler for rate limit exceeded errors."""
    logger.warning(f"Rate limit exceeded for {get_user_identifier(request)}")
    return HTTPException(
        status_code=status.HTTP_429_TOO_MANY_REQUESTS,
        detail={
            "error": "rate_limit_exceeded",
            "message": str(exc.detail),
            "retry_after": getattr(exc, "retry_after", None),
        },
    )
