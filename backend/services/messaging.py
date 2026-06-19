"""Messaging service for car and organization messages."""
import logging
from datetime import datetime, timezone
from typing import Optional, List, Dict, Any
import uuid

from sqlalchemy import select, func, and_
from sqlalchemy.ext.asyncio import AsyncSession

from domain.models import Message, MessageScope, MessageType, SenderType, Car

logger = logging.getLogger(__name__)


class MessagingService:
    """Service for message management."""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def create_message(
        self,
        organization_id: uuid.UUID,
        scope: MessageScope,
        message_type: MessageType,
        sender_type: SenderType,
        content: str,
        car_id: Optional[uuid.UUID] = None,
        sender_id: Optional[uuid.UUID] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> Message:
        """
        Create a new message.
        
        Args:
            organization_id: The organization ID
            scope: Message scope (car or organization)
            message_type: Type of message
            sender_type: Who sent the message (user, ai, system)
            content: Message content
            car_id: Car ID if scope is car
            sender_id: Sender user ID if sender_type is user
            metadata: Optional additional metadata
            
        Returns:
            The created message
        """
        # Validate scope/car_id constraint
        if scope == MessageScope.car and not car_id:
            raise ValueError("car_id required for car-scoped messages")
        if scope == MessageScope.organization and car_id:
            raise ValueError("car_id must be null for organization-scoped messages")

        # Verify car exists if car_id provided
        if car_id:
            result = await self.db.execute(
                select(Car).filter(
                    Car.id == car_id,
                    Car.organization_id == organization_id,
                    Car.is_active == True
                )
            )
            car = result.scalars().first()
            if not car:
                raise ValueError(f"Car {car_id} not found or not accessible")

        message = Message(
            organization_id=organization_id,
            scope=scope,
            car_id=car_id,
            message_type=message_type,
            sender_type=sender_type,
            sender_id=sender_id,
            content=content,
            message_metadata=metadata or {}
        )

        self.db.add(message)
        await self.db.commit()
        await self.db.refresh(message)

        logger.info(
            f"Created message: {message.id} (type: {message_type.value}, scope: {scope.value})"
        )

        return message

    async def get_messages(
        self,
        organization_id: uuid.UUID,
        scope: Optional[MessageScope] = None,
        car_id: Optional[uuid.UUID] = None,
        message_type: Optional[MessageType] = None,
        sender_type: Optional[SenderType] = None,
        limit: int = 50,
        offset: int = 0
    ) -> tuple[List[Message], int]:
        """
        Get messages with filters.
        
        Args:
            organization_id: The organization ID
            scope: Optional scope filter
            car_id: Optional car filter
            message_type: Optional type filter
            sender_type: Optional sender type filter
            limit: Maximum results
            offset: Result offset
            
        Returns:
            Tuple of (messages list, total count)
        """
        filters = [Message.organization_id == organization_id]

        if scope:
            filters.append(Message.scope == scope)
        if car_id:
            filters.append(Message.car_id == car_id)
        if message_type:
            filters.append(Message.message_type == message_type)
        if sender_type:
            filters.append(Message.sender_type == sender_type)

        # Get total count
        count_query = select(func.count(Message.id)).filter(and_(*filters))
        total = await self.db.scalar(count_query) or 0

        # Get messages
        query = (
            select(Message)
            .filter(and_(*filters))
            .order_by(Message.created_at.desc())
            .limit(limit)
            .offset(offset)
        )

        result = await self.db.execute(query)
        messages = result.scalars().all()

        return messages, total

    async def get_car_messages(
        self,
        car_id: uuid.UUID,
        organization_id: uuid.UUID,
        limit: int = 50
    ) -> List[Message]:
        """Get recent messages for a specific car."""
        query = (
            select(Message)
            .filter(
                and_(
                    Message.car_id == car_id,
                    Message.organization_id == organization_id
                )
            )
            .order_by(Message.created_at.desc())
            .limit(limit)
        )

        result = await self.db.execute(query)
        return result.scalars().all()

    async def get_org_messages(
        self,
        organization_id: uuid.UUID,
        limit: int = 50
    ) -> List[Message]:
        """Get recent organization-wide messages."""
        query = (
            select(Message)
            .filter(
                and_(
                    Message.organization_id == organization_id,
                    Message.scope == MessageScope.organization
                )
            )
            .order_by(Message.created_at.desc())
            .limit(limit)
        )

        result = await self.db.execute(query)
        return result.scalars().all()

    async def get_conversation(
        self,
        car_id: uuid.UUID,
        organization_id: uuid.UUID,
        limit: int = 100
    ) -> List[Message]:
        """Get all messages for a car (chat and AI)."""
        query = (
            select(Message)
            .filter(
                and_(
                    Message.car_id == car_id,
                    Message.organization_id == organization_id,
                    Message.scope == MessageScope.car
                )
            )
            .order_by(Message.created_at.asc())
            .limit(limit)
        )

        result = await self.db.execute(query)
        return result.scalars().all()

    async def delete_message(
        self,
        message_id: uuid.UUID,
        organization_id: uuid.UUID
    ) -> bool:
        """Delete a message (only by sender or admin)."""
        result = await self.db.execute(
            select(Message).filter(
                and_(
                    Message.id == message_id,
                    Message.organization_id == organization_id
                )
            )
        )
        message = result.scalars().first()
        
        if not message:
            raise ValueError(f"Message {message_id} not found")

        await self.db.delete(message)
        await self.db.commit()

        logger.info(f"Deleted message: {message_id}")

        return True
