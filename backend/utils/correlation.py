"""Correlation ID management for request tracing across services."""
import uuid
import logging
from typing import Optional
from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware

logger = logging.getLogger(__name__)

# Header names for correlation ID propagation
CORRELATION_ID_HEADER = "X-Correlation-ID"
CORRELATION_ID_STATE = "correlation_id"


def generate_correlation_id() -> str:
    """Generate a new correlation ID."""
    return str(uuid.uuid4())


def get_correlation_id(request: Request) -> Optional[str]:
    """Get correlation ID from request state."""
    return getattr(request.state, CORRELATION_ID_STATE, None)


def set_correlation_id(request: Request, correlation_id: str) -> None:
    """Set correlation ID on request state."""
    request.state.correlation_id = correlation_id


class CorrelationMiddleware(BaseHTTPMiddleware):
    """Middleware to generate and propagate correlation IDs.
    
    Generates a new correlation ID for each request if not provided,
    and adds it to request state and response headers for tracing.
    """

    async def dispatch(self, request: Request, call_next):
        # Check for existing correlation ID from upstream service
        correlation_id = request.headers.get(CORRELATION_ID_HEADER)
        
        if not correlation_id:
            correlation_id = generate_correlation_id()
        
        # Set on request state for downstream access
        set_correlation_id(request, correlation_id)
        
        # Process request
        response = await call_next(request)
        
        # Add to response headers for client-side tracing
        response.headers[CORRELATION_ID_HEADER] = correlation_id
        
        return response


def get_correlation_context(request: Request) -> dict:
    """Get correlation context dict for logging."""
    return {
        "correlation_id": getattr(request.state, CORRELATION_ID_STATE, None),
    }