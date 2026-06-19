"""Rate limiting middleware using slowapi with Redis backend."""

import logging
from typing import Optional

from fastapi import Request, HTTPException, status
from fastapi.responses import JSONResponse
from slowapi import Limiter
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded

from config.settings import settings

logger = logging.getLogger(__name__)


def get_user_identifier(request: Request) -> str:
    if hasattr(request.state, "user_id") and request.state.user_id:
        return f"user:{request.state.user_id}"
    return get_remote_address(request)


limiter = Limiter(key_func=get_user_identifier, storage_uri=settings.REDIS_URL, default_limits=["1000/hour"])

RATE_LIMITS = {
    "telemetry_ingest": "100/minute",
    "ai_chat": "10/minute",
    "default": "1000/hour",
    "websocket": "60/minute",
}


async def rate_limit_exceeded_handler(request: Request, exc: RateLimitExceeded):
    logger.warning(f"Rate limit exceeded for {get_user_identifier(request)}")
    return JSONResponse(
        status_code=status.HTTP_429_TOO_MANY_REQUESTS,
        content={
            "error": "rate_limit_exceeded",
            "message": str(exc.detail),
            "retry_after": getattr(exc, "retry_after", None),
        },
    )


RateLimitExceeded = RateLimitExceeded
