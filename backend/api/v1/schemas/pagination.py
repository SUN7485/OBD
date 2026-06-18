"""Cursor-based pagination schemas."""

from typing import Generic, TypeVar, Optional, List
from pydantic import BaseModel, Field
import base64


T = TypeVar("T")


class PaginationParams(BaseModel):
    """Query parameters for cursor-based pagination."""

    cursor: Optional[str] = Field(
        default=None, description="Base64-encoded cursor (usually created_at timestamp)"
    )
    limit: int = Field(
        default=20, ge=1, le=100, description="Maximum number of items to return"
    )


class PaginatedResponse(BaseModel, Generic[T]):
    """Generic paginated response."""

    data: List[T]
    next_cursor: Optional[str] = Field(
        default=None, description="Cursor for next page, None if no more pages"
    )
    has_more: bool = Field(
        default=False, description="Whether more items exist after this page"
    )


def encode_cursor(timestamp: str) -> str:
    """Encode a timestamp string to a cursor."""
    return base64.b64encode(timestamp.encode()).decode()


def decode_cursor(cursor: str) -> Optional[str]:
    """Decode a cursor to timestamp string."""
    try:
        return base64.b64decode(cursor.encode()).decode()
    except Exception:
        return None
