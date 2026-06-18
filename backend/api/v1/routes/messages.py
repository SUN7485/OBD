"""API routes for messaging."""
import logging
from typing import Optional, List
import uuid

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession
from pydantic import BaseModel

from backend.db.session import get_db
from backend.middleware.auth import get_current_user
from backend.domain.models import User, MessageScope, MessageType, SenderType
from backend.services.messaging import MessagingService
from backend.services.websocket_manager import manager

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/messages", tags=["messages"])


class MessageCreateRequest(BaseModel):
    """Message creation request."""
    scope: str = MessageScope.car.value  # "car" or "organization"
    car_id: Optional[uuid.UUID] = None
    message_type: str = MessageType.chat.value
    content: str


class MessageResponse(BaseModel):
    """Message response schema."""
    id: str
    scope: str
    car_id: Optional[str]
    message_type: str
    sender_type: str
    sender_id: Optional[str]
    content: str
    created_at: str
    metadata: dict

    class Config:
        from_attributes = True


class MessageListResponse(BaseModel):
    """Message list response."""
    messages: List[MessageResponse]
    total: int
    limit: int
    offset: int


@router.get(
    "",
    response_model=MessageListResponse,
    summary="List messages",
    description="Get messages with filtering and pagination."
)
async def list_messages(
    scope: Optional[str] = Query(None, description="Filter by scope (car, organization)"),
    car_id: Optional[uuid.UUID] = Query(None, description="Filter by car ID"),
    message_type: Optional[str] = Query(None, description="Filter by message type"),
    sender_type: Optional[str] = Query(None, description="Filter by sender type"),
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    List messages with filters.
    
    - Supports query params: scope, car_id, message_type, sender_type, limit, offset
    - Filters by organization_id for multi-tenant isolation
    - Returns messages in descending order by created_at
    """
    # Parse scope
    scope_enum = None
    if scope:
        try:
            scope_enum = MessageScope(scope)
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid scope: {scope}"
            )

    # Parse message type
    message_type_enum = None
    if message_type:
        try:
            message_type_enum = MessageType(message_type)
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid message type: {message_type}"
            )

    # Parse sender type
    sender_type_enum = None
    if sender_type:
        try:
            sender_type_enum = SenderType(sender_type)
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid sender type: {sender_type}"
            )

    service = MessagingService(db)

    try:
        messages, total = await service.get_messages(
            organization_id=current_user.organization_id,
            scope=scope_enum,
            car_id=car_id,
            message_type=message_type_enum,
            sender_type=sender_type_enum,
            limit=limit,
            offset=offset
        )
    except Exception as e:
        logger.error(f"Error getting messages: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve messages"
        )

    message_responses = [
        MessageResponse(
            id=str(m.id),
            scope=m.scope.value,
            car_id=str(m.car_id) if m.car_id else None,
            message_type=m.message_type.value,
            sender_type=m.sender_type.value,
            sender_id=str(m.sender_id) if m.sender_id else None,
            content=m.content,
            created_at=m.created_at.isoformat(),
            metadata=m.message_metadata
        )
        for m in messages
    ]

    return MessageListResponse(
        messages=message_responses,
        total=total,
        limit=limit,
        offset=offset
    )


@router.post(
    "",
    response_model=MessageResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create message",
    description="Create a new message."
)
async def create_message(
    request: MessageCreateRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Create a new message.
    
    - Validates scope and car_id
    - Stores in database
    - Broadcasts to WebSocket subscribers in appropriate room
    """
    # Parse scope
    try:
        scope = MessageScope(request.scope)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid scope: {request.scope}"
        )

    # Parse message type
    try:
        message_type = MessageType(request.message_type)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid message type: {request.message_type}"
        )

    service = MessagingService(db)

    try:
        message = await service.create_message(
            organization_id=current_user.organization_id,
            scope=scope,
            message_type=message_type,
            sender_type=SenderType.user,
            content=request.content,
            car_id=request.car_id,
            sender_id=current_user.id
        )
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"Error creating message: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create message"
        )

    # Broadcast to WebSocket
    try:
        if scope == MessageScope.car and message.car_id:
            await manager.broadcast_to_car(
                message.car_id,
                {
                    "type": "message",
                    "data": {
                        "id": str(message.id),
                        "message_type": message.message_type.value,
                        "sender_type": message.sender_type.value,
                        "sender_name": current_user.full_name,
                        "content": message.content,
                        "created_at": message.created_at.isoformat()
                    }
                }
            )
        else:
            await manager.broadcast_to_org(
                current_user.organization_id,
                {
                    "type": "message",
                    "data": {
                        "id": str(message.id),
                        "scope": message.scope.value,
                        "message_type": message.message_type.value,
                        "sender_type": message.sender_type.value,
                        "sender_name": current_user.full_name,
                        "content": message.content,
                        "created_at": message.created_at.isoformat()
                    }
                }
            )
    except Exception as e:
        logger.error(f"WebSocket broadcast error: {e}")

    return MessageResponse(
        id=str(message.id),
        scope=message.scope.value,
        car_id=str(message.car_id) if message.car_id else None,
        message_type=message.message_type.value,
        sender_type=message.sender_type.value,
        sender_id=str(message.sender_id) if message.sender_id else None,
        content=message.content,
        created_at=message.created_at.isoformat(),
        metadata=message.message_metadata
    )


@router.get(
    "/car/{car_id}",
    summary="Get car messages",
    description="Get chat and AI messages for a specific car."
)
async def get_car_messages(
    car_id: uuid.UUID,
    limit: int = Query(50, ge=1, le=100),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Get conversation messages for a car."""
    service = MessagingService(db)

    try:
        messages = await service.get_conversation(
            car_id=car_id,
            organization_id=current_user.organization_id,
            limit=limit
        )
    except Exception as e:
        logger.error(f"Error getting car messages: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve messages"
        )

    return {
        "messages": [
            {
                "id": str(m.id),
                "message_type": m.message_type.value,
                "sender_type": m.sender_type.value,
                "sender_id": str(m.sender_id) if m.sender_id else None,
                "content": m.content,
                "created_at": m.created_at.isoformat()
            }
            for m in messages
        ]
    }
