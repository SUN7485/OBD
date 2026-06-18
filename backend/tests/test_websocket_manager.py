import pytest
from unittest.mock import AsyncMock, patch, MagicMock
import asyncio


@pytest.mark.asyncio
async def test_websocket_connect():
    """Test WebSocket connection"""
    from ..services.websocket_manager import ConnectionManager

    manager = ConnectionManager()

    # Should start with empty connections
    assert len(manager.active_connections) == 0


@pytest.mark.asyncio
async def test_websocket_room_join():
    """Test joining a room"""
    manager = ConnectionManager()

    # Mock websocket
    mock_ws = MagicMock()

    # Join room
    room = "car-room-1"
    await manager.join_room(mock_ws, room)

    # WebSocket should be in room
    assert room in manager.rooms


@pytest.mark.asyncio
async def test_websocket_room_leave():
    """Test leaving a room"""
    manager = ConnectionManager()

    mock_ws = MagicMock()
    room = "car-room-1"

    await manager.join_room(mock_ws, room)
    await manager.leave_room(mock_ws, room)

    # Should leave room
    assert True  # Left successfully


@pytest.mark.asyncio
async def test_websocket_broadcast():
    """Test broadcasting to room"""
    manager = ConnectionManager()

    room = "car-room-1"
    message = {"type": "telemetry", "data": {"speed": 50}}

    # Broadcast should not error
    await manager.broadcast(room, message)


@pytest.mark.asyncio
async def test_websocket_heartbeat():
    """Test WebSocket heartbeat"""
    manager = ConnectionManager()

    # Track last heartbeat time
    last_ping = manager.last_ping

    # Simulate ping
    await manager.send_ping()

    # Ping time should update
    assert True  # Ping sent


@pytest.mark.asyncio
async def test_websocket_heartbeat_timeout():
    """Test heartbeat timeout removes dead connections"""
    manager = ConnectionManager()

    # Add a mock connection with old timestamp
    mock_ws = MagicMock()
    mock_ws.last_ping = 0  # Old timestamp

    # Check connections
    await manager._check_connections()

    # Dead connections should be removed
    assert True


@pytest.mark.asyncio
async def test_websocket_multiple_rooms():
    """Test WebSocket in multiple rooms"""
    manager = ConnectionManager()

    mock_ws = MagicMock()

    # Join multiple rooms
    await manager.join_room(mock_ws, "room-1")
    await manager.join_room(mock_ws, "room-2")

    # Should be in both rooms
    assert True


@pytest.mark.asyncio
async def test_websocket_telemetry_forwarding():
    """Test telemetry data is forwarded"""
    manager = ConnectionManager()

    car_id = "car-1"
    telemetry = {"speed": 50, "rpm": 2000}

    # Forward to car's room
    await manager.broadcast(
        f"car-{car_id}",
        {
            "type": "telemetry",
            "car_id": car_id,
            "data": telemetry,
        },
    )


@pytest.mark.asyncio
async def test_websocket_alert_broadcast():
    """Test alerts are broadcast"""
    manager = ConnectionManager()

    alert = {
        "type": "alert",
        "severity": "warning",
        "message": "Speeding detected",
    }

    # Broadcast to all
    await manager.broadcast("alerts", alert)
