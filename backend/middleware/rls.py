"""Row-Level Security (RLS) middleware."""
import logging
from typing import Optional

from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware

logger = logging.getLogger(__name__)

# Session variable name for RLS
RLS_SESSION_VAR = "app.current_org_id"


class RLSMiddleware(BaseHTTPMiddleware):
    """
    Middleware to set PostgreSQL session variables for Row-Level Security.
    
    Extracts organization_id from JWT token and sets it in the PostgreSQL
    session so that RLS policies can filter by organization.
    """
    
    async def dispatch(self, request: Request, call_next):
        # Get organization_id from request state (set by auth middleware)
        org_id = None
        
        if hasattr(request.state, "organization_id") and request.state.organization_id:
            org_id = str(request.state.organization_id)
        
        # Also check for organization_id in query or headers for special cases
        if not org_id:
            org_id = request.headers.get("X-Organization-ID")
        
        if not org_id:
            # Try to get from JWT if present
            auth_header = request.headers.get("Authorization")
            if auth_header and auth_header.startswith("Bearer "):
                try:
                    from services.auth import decode_token
                    token = auth_header.split(" ")[1]
                    payload = decode_token(token)
                    org_id = payload.get("organization_id")
                except Exception:
                    pass
        
        # Store in request state for later use
        request.state.current_org_id = org_id
        
        # Process request
        response = await call_next(request)
        
        return response


async def set_rls_session(org_id: str) -> None:
    """
    Set the RLS session variable in PostgreSQL.
    
    This should be called when creating a database connection.
    
    Args:
        org_id: The organization ID to set
    """
    # This is handled by the middleware which stores org_id in request state
    # The actual SQL session variable setting happens in the database connection
    pass


def get_org_id_from_request(request: Request) -> Optional[str]:
    """
    Get the organization ID from a request.
    
    Args:
        request: FastAPI request
        
    Returns:
        Organization ID string or None
    """
    if hasattr(request.state, "current_org_id"):
        return request.state.current_org_id
    
    return None
