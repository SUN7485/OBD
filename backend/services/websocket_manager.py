"""WebSocket connection manager with room-based subscriptions."""

import asyncio
import logging
from typing import Dict, List, Set, Optional, Any
from dataclasses import dataclass, field
from datetime import datetime, timezone
import uuid

from fastapi import WebSocket

from services.redis_client import redis_client

logger = logging.getLogger(__name__)


@dataclass
class ConnectionMetadata:
    """Metadata for a WebSocket connection."""

    user_id: uuid.UUID
    organization_id: uuid.UUID
    role: str
    subscribed_rooms: Set[str] = field(default_factory=set)
    connected_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    last_ping: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    car_ids: List[uuid.UUID] = field(default_factory=list)


class ConnectionManager:
    """
    Manages WebSocket connections with room-based subscriptions.

    Supports rooms:
    - org:{organization_id} - Organization-wide broadcasts
    - car:{car_id} - Car-specific broadcasts
    - user:{user_id} - User-specific messages
    """

    def __init__(self):
        # Connection storage: websocket -> metadata
        self._connections: Dict[WebSocket, ConnectionMetadata] = {}
        # Room storage: room_name -> set of websockets
        self._rooms: Dict[str, Set[WebSocket]] = {}
        # Heartbeat task
        self._heartbeat_task: Optional[asyncio.Task] = None
        # Redis channel prefix
        self._redis_channel_prefix = "ws:"

    async def start(self) -> None:
        """Start the connection manager."""
        self._heartbeat_task = asyncio.create_task(self._heartbeat_loop())
        logger.info("WebSocket connection manager started")

    async def stop(self) -> None:
        """Stop the connection manager and cleanup."""
        if self._heartbeat_task:
            self._heartbeat_task.cancel()
            try:
                await self._heartbeat_task
            except asyncio.CancelledError:
                pass
        # Disconnect all
        for ws in list(self._connections.keys()):
            await self.disconnect(ws)
        logger.info("WebSocket connection manager stopped")

    async def connect(
        self,
        websocket: WebSocket,
        user_id: uuid.UUID,
        organization_id: uuid.UUID,
        role: str,
        car_ids: List[uuid.UUID] = None,
    ) -> ConnectionMetadata:
        """
        Accept a new WebSocket connection.

        Args:
            websocket: The WebSocket connection
            user_id: The authenticated user's ID
            organization_id: The user's organization ID
            role: The user's role
            car_ids: List of car IDs the user has access to

        Returns:
            The connection metadata
        """
        await websocket.accept()

        metadata = ConnectionMetadata(
            user_id=user_id,
            organization_id=organization_id,
            role=role,
            car_ids=car_ids or [],
        )

        self._connections[websocket] = metadata

        # Subscribe to org room
        await self._join_room(websocket, f"org:{organization_id}")

        # Subscribe to user room
        await self._join_room(websocket, f"user:{user_id}")

        # Subscribe to car rooms based on role
        if role in ["admin", "fleet_manager"]:
            # Admin/fleet manager gets all cars in org
            pass  # They'll receive via org room
        elif car_ids:
            for car_id in car_ids:
                await self._join_room(websocket, f"car:{car_id}")

        logger.info(
            f"WebSocket connected: user={user_id}, org={organization_id}, "
            f"role={role}, cars={len(car_ids or [])}"
        )

        return metadata

    async def disconnect(self, websocket: WebSocket) -> None:
        """
        Disconnect a WebSocket connection.

        Args:
            websocket: The WebSocket connection to close
        """
        if websocket not in self._connections:
            return

        metadata = self._connections[websocket]

        # Leave all rooms
        for room in list(metadata.subscribed_rooms):
            await self._leave_room(websocket, room)

        del self._connections[websocket]

        try:
            await websocket.close()
        except Exception:
            pass

        logger.info(f"WebSocket disconnected: user={metadata.user_id}")

    async def send_personal_message(self, message: Any, websocket: WebSocket) -> bool:
        """
        Send a message to a specific WebSocket connection.

        Args:
            message: The message to send (will be JSON serialized)
            websocket: The target WebSocket

        Returns:
            True if sent successfully
        """
        if websocket not in self._connections:
            return False

        try:
            await websocket.send_json(message)
            return True
        except Exception as e:
            logger.error(f"Error sending personal message: {e}")
            await self.disconnect(websocket)
            return False

    async def send_to_user(self, user_id: uuid.UUID, message: Any) -> int:
        """
        Send a message to all connections for a specific user.

        Args:
            user_id: The target user's ID
            message: The message to send

        Returns:
            Number of connections message was sent to
        """
        room = f"user:{user_id}"
        return await self.broadcast_to_room(room, message)

    async def broadcast_to_room(self, room: str, message: Any) -> int:
        """
        Broadcast a message to all connections in a room.

        Args:
            room: The room name (e.g., "car:uuid", "org:uuid")
            message: The message to broadcast

        Returns:
            Number of connections message was sent to
        """
        if room not in self._rooms:
            return 0

        # Also publish to Redis for cross-instance broadcasting
        redis_channel = f"{self._redis_channel_prefix}{room}"
        try:
            await redis_client.publish(redis_channel, message)
        except Exception as e:
            logger.error(f"Error publishing to Redis: {e}")

        # Send to local connections
        count = 0
        disconnected = []

        for ws in self._rooms[room]:
            if await self.send_personal_message(message, ws):
                count += 1
            else:
                disconnected.append(ws)

        # Clean up disconnected
        for ws in disconnected:
            await self.disconnect(ws)

        return count

    async def broadcast_to_org(self, organization_id: uuid.UUID, message: Any) -> int:
        """Broadcast to all users in an organization."""
        return await self.broadcast_to_room(f"org:{organization_id}", message)

    async def broadcast_to_car(self, car_id: uuid.UUID, message: Any) -> int:
        """Broadcast to all users monitoring a specific car."""
        return await self.broadcast_to_room(f"car:{car_id}", message)

    async def _join_room(self, websocket: WebSocket, room: str) -> None:
        """Add a WebSocket to a room."""
        if websocket not in self._connections:
            return

        metadata = self._connections[websocket]
        metadata.subscribed_rooms.add(room)

        if room not in self._rooms:
            self._rooms[room] = set()

        self._rooms[room].add(websocket)
        logger.debug(f"WebSocket joined room: {room}")

    async def _leave_room(self, websocket: WebSocket, room: str) -> None:
        """Remove a WebSocket from a room."""
        if room in self._rooms:
            self._rooms[room].discard(websocket)
            if not self._rooms[room]:
                del self._rooms[room]

        if websocket in self._connections:
            self._connections[websocket].subscribed_rooms.discard(room)

        logger.debug(f"WebSocket left room: {room}")

    async def _heartbeat_loop(self) -> None:
        """Send periodic pings to all connections."""
        while True:
            try:
                await asyncio.sleep(30)  # 30 second interval
                await self._check_connections()
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in heartbeat: {e}")

    async def _check_connections(self) -> None:
        """Check all connections and disconnect stale ones."""
        now = datetime.now(timezone.utc)
        disconnected = []

        for ws, metadata in self._connections.items():
            # Check if last ping is too old
            elapsed = (now - metadata.last_ping).total_seconds()
            if elapsed > 60:  # 60 second timeout
                disconnected.append(ws)
                logger.warning(
                    f"Connection stale, disconnecting: "
                    f"user={metadata.user_id}, elapsed={elapsed}s"
                )

        for ws in disconnected:
            await self.disconnect(ws)

    async def handle_pong(self, websocket: WebSocket) -> None:
        """Update last_ping timestamp on pong receipt."""
        if websocket in self._connections:
            self._connections[websocket].last_ping = datetime.now(timezone.utc)

    def get_active_connections_count(self) -> int:
        """Get the total number of active connections."""
        return len(self._connections)

    def get_room_count(self, room: str) -> int:
        """Get the number of connections in a room."""
        return len(self._rooms.get(room, set()))

    async def handle_incoming_message(
        self, websocket: WebSocket, message: dict
    ) -> None:
        """
        Handle incoming WebSocket messages.

        Expected message formats:
        - {"type": "ping"}
        - {"type": "subscribe", "room": "car:uuid"}
        - {"type": "unsubscribe", "room": "car:uuid"}
        """
        if websocket not in self._connections:
            return

        msg_type = message.get("type")

        if msg_type == "ping":
            await self.handle_pong(websocket)
            await websocket.send_json({"type": "pong"})

        elif msg_type == "subscribe":
            room = message.get("room")
            if room:
                await self._join_room(websocket, room)

        elif msg_type == "unsubscribe":
            room = message.get("room")
            if room:
                await self._leave_room(websocket, room)


# Global instance
manager = ConnectionManager()
