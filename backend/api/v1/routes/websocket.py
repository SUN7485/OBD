"""WebSocket endpoint for real-time communication."""
import logging
from typing import List
import uuid

from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from config.settings import settings
from services.auth import decode_token
from services.websocket_manager import manager
from services.redis_client import redis_client
from db.session import session_manager
from domain.models import User, Car

logger = logging.getLogger(__name__)

router = APIRouter()


async def get_user_from_token(
    token: str,
    db: AsyncSession
) -> User:
    """
    Validate token and fetch user.
    
    Args:
        token: JWT token from query parameter
        db: Database session
        
    Returns:
        User object
        
    Raises:
        WebSocket close if invalid
    """
    credentials_exception = {"code": 4001, "message": "Invalid credentials"}
    
    try:
        payload = decode_token(token)
        user_id: str = payload.get("user_id")
        organization_id: str = payload.get("organization_id")
        
        if user_id is None or organization_id is None:
            raise ValueError("Invalid token payload")
    except Exception as e:
        logger.warning(f"Token decode error: {e}")
        raise WebSocketCloseException(credentials_exception)

    try:
        result = await db.execute(
            select(User).filter(
                User.id == user_id,
                User.organization_id == organization_id
            )
        )
        user = result.scalars().first()
        
        if user is None or not user.is_active:
            raise WebSocketCloseException(credentials_exception)
        
        return user
    except WebSocketCloseException:
        raise
    except Exception as e:
        logger.error(f"Database error: {e}")
        raise WebSocketCloseException({"code": 5000, "message": "Internal error"})


async def get_user_car_ids(
    user: User,
    db: AsyncSession
) -> List[uuid.UUID]:
    """
    Get list of car IDs the user can access.
    
    Args:
        user: The authenticated user
        db: Database session
        
    Returns:
        List of car UUIDs
    """
    car_ids = []
    
    # Admin and fleet manager can see all cars in org
    if user.role in ["admin", "fleet_manager"]:
        result = await db.execute(
            select(Car.id).filter(
                Car.organization_id == user.organization_id,
                Car.is_active == True
            )
        )
        car_ids = [row[0] for row in result.fetchall()]
    elif user.role == "driver":
        # Drivers can only see their assigned cars
        if user.assigned_cars:
            car_ids = [car.id for car in user.assigned_cars]
    
    return car_ids


class WebSocketCloseException(Exception):
    """Exception to signal WebSocket closure."""
    def __init__(self, close_data: dict):
        self.close_data = close_data


@router.websocket("/ws")
async def websocket_endpoint(
    websocket: WebSocket,
    token: str = Query(..., description="JWT authentication token")
):
    """
    WebSocket endpoint for real-time telemetry and messaging.
    
    Connect with: /api/v1/ws?token=<jwt_token>
    
    The token should be a valid JWT access token.
    
    Message format (client -> server):
    - {"type": "ping"} - Keep connection alive
    - {"type": "subscribe", "room": "car:uuid"} - Subscribe to car room
    - {"type": "unsubscribe", "room": "car:uuid"} - Unsubscribe from room
    
    Message format (server -> client):
    - {"type": "telemetry", "data": {...}} - Real-time OBD data
    - {"type": "alert", "data": {...}} - New alert notification
    - {"type": "message", "data": {...}} - New chat/system message
    - {"type": "ai_reply", "data": {...}} - AI response
    - {"type": "pong"} - Response to ping
    """
    user = None
    redis_channel = None
    
    async with session_manager() as db:
        # Authenticate user
        try:
            user = await get_user_from_token(token, db)
        except WebSocketCloseException as e:
            await websocket.close(code=4004, reason=str(e.close_data))
            return
        except Exception as e:
            logger.error(f"Auth error: {e}")
            await websocket.close(code=4004, reason='{"code": 4001, "message": "Authentication failed"}')
            return

        # Get accessible car IDs
        try:
            car_ids = await get_user_car_ids(user, db)
        except Exception as e:
            logger.error(f"Error getting car IDs: {e}")
            car_ids = []

        # Connect to manager
        try:
            metadata = await manager.connect(
                websocket=websocket,
                user_id=user.id,
                organization_id=user.organization_id,
                role=user.role.value,
                car_ids=car_ids
            )
            redis_channel = f"ws:user:{user.id}"
        except Exception as e:
            logger.error(f"Connection error: {e}")
            await websocket.close(code=4004, reason='{"code": 4002, "message": "Connection failed"}')
            return

        # Setup Redis subscription for this user's messages
        async def redis_handler(data: dict):
            """Handle messages from Redis."""
            try:
                await websocket.send_json(data)
            except Exception as e:
                logger.error(f"Error sending Redis message: {e}")

        try:
            await redis_client.subscribe(redis_channel, redis_handler)
        except Exception as e:
            logger.error(f"Redis subscription error: {e}")

    # Message handling loop (outside db session to avoid long-held connections)
    try:
        while True:
            data = await websocket.receive_json()
            await manager.handle_incoming_message(websocket, data)
    except WebSocketDisconnect:
        pass
    except Exception as e:
        logger.error(f"WebSocket error: {e}")
    finally:
        # Cleanup
        if redis_channel:
            try:
                await redis_client.unsubscribe(redis_channel)
            except Exception:
                pass
        if user:
            await manager.disconnect(websocket)