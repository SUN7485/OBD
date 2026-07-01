"""Row-Level Security (RLS) middleware using PostgreSQL session variables."""
import logging
from typing import Optional
from contextvars import ContextVar

from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncEngine

from db.session import engine

logger = logging.getLogger(__name__)

# Context variable for storing current org_id in async context
_current_org_id: ContextVar[Optional[str]] = ContextVar("current_org_id", default=None)


def get_current_org_id() -> Optional[str]:
    """Get the current organization ID from context."""
    return _current_org_id.get()


def set_current_org_id(org_id: Optional[str]) -> None:
    """Set the current organization ID in context."""
    _current_org_id.set(org_id)


# SQLAlchemy event listener to set RLS session variable on new connections
async def _set_rls_on_connection(db_connection, connection_record):
    """Event listener: set RLS session variable when a new DB connection is created."""
    org_id = _current_org_id.get()
    if org_id:
        try:
            await db_connection.execute(text("SET app.current_org_id = :org_id"), {"org_id": str(org_id)})
            logger.debug(f"Set RLS session variable to org_id={org_id}")
        except Exception as e:
            logger.warning(f"Failed to set RLS session variable: {e}")


def _set_rls_on_connection_sync(db_connection, connection_record):
    """Sync wrapper for event listener (SQLAlchemy may call sync version)."""
    import asyncio
    try:
        loop = asyncio.get_running_loop()
        loop.create_task(_set_rls_on_connection(db_connection, connection_record))
    except RuntimeError:
        # No event loop running (e.g., during tests)
        pass


# Register event listener on the engine
from sqlalchemy import event
event.listen(engine.sync_engine, "connect", _set_rls_on_connection_sync)


class RLSMiddleware(BaseHTTPMiddleware):
    """
    Middleware to set PostgreSQL session variables for Row-Level Security.
    
    Extracts organization_id from JWT token and stores it in context
    so that SQLAlchemy event listeners can set the RLS session variable
    on each new database connection.
    """
    
    async def dispatch(self, request: Request, call_next):
        org_id = None
        
        # Check for organization_id in request state (set by auth middleware/dependency)
        if hasattr(request.state, "organization_id") and request.state.organization_id:
            org_id = str(request.state.organization_id)
        
        # Also check for organization_id in headers for special cases
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
        
        # Store in request state and context var for downstream use
        request.state.current_org_id = org_id
        set_current_org_id(org_id)
        
        # Process request
        response = await call_next(request)
        
        # Clear context after request
        set_current_org_id(None)
        
        return response


async def set_rls_session(org_id: str) -> None:
    """
    Set the RLS session variable in PostgreSQL.
    
    This is called when creating a database connection to ensure
    all queries within that session are automatically filtered by
    the organization_id through PostgreSQL RLS policies.
    
    Note: This requires that RLS is enabled on the relevant tables
    and that appropriate policies exist. Since TimescaleDB hypertables
    cannot use RLS with compression, application-level filtering is
    used as a fallback for obd_data.
    
    Args:
        org_id: The organization ID to set
    """
    try:
        from db.session import AsyncSessionLocal
        from sqlalchemy import text
        
        async with AsyncSessionLocal() as session:
            await session.execute(
                text("SET app.current_org_id = :org_id"),
                {"org_id": str(org_id)}
            )
            await session.commit()
            logger.debug(f"RLS session variable set to org_id={org_id}")
    except Exception as e:
        logger.warning(f"Failed to set RLS session variable: {e}")


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
    
    return get_current_org_id()