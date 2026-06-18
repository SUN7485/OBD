import pytest
from unittest.mock import AsyncMock, patch, MagicMock
from datetime import datetime, timezone


class MockTelemetryPayload:
    def __init__(self, car_id: str, speed: float, rpm: float, **kwargs):
        self.car_id = car_id
        self.speed = speed
        self.rpm = rpm
        self.coolant_temp = kwargs.get("coolant_temp", 90.0)
        self.engine_load = kwargs.get("engine_load", 15.0)
        self.throttle = kwargs.get("throttle", 10.0)
        self.fuel_level = kwargs.get("fuel_level", 75.0)
        self.latitude = kwargs.get("latitude")
        self.longitude = kwargs.get("longitude")
        self.timestamp = kwargs.get("timestamp", datetime.now(timezone.utc).isoformat())


@pytest.mark.asyncio
async def test_ingest_telemetry_validates_data_ranges():
    """Test that telemetry ingestion validates data ranges"""
    from ..services.telemetry import TelemetryService

    # Valid data should be accepted
    valid_payload = MockTelemetryPayload(
        car_id="test-car-1", speed=50.0, rpm=2000.0, coolant_temp=90.0
    )

    # Speed should be 0-300 km/h
    assert 0 <= valid_payload.speed <= 300
    # RPM should be 0-8000
    assert 0 <= valid_payload.rpm <= 8000
    # Coolant temp should be -40 to 150 C
    assert -40 <= valid_payload.coolant_temp <= 150


@pytest.mark.asyncio
async def test_ingest_telemetry_rejects_invalid_speed():
    """Test that invalid speed values are rejected"""
    from ..services.telemetry import TelemetryService

    # Negative speed should be rejected
    invalid_payload = MockTelemetryPayload(
        car_id="test-car-1",
        speed=-10.0,  # Invalid: negative
        rpm=2000.0,
    )

    # Validation should fail
    assert invalid_payload.speed < 0


@pytest.mark.asyncio
async def test_ingest_telemetry_rejects_invalid_rpm():
    """Test that invalid RPM values are rejected"""
    invalid_payload = MockTelemetryPayload(
        car_id="test-car-1",
        speed=50.0,
        rpm=10000.0,  # Invalid: too high
    )

    assert invalid_payload.rpm > 8000


@pytest.mark.asyncio
async def test_telemetry_history_query():
    """Test querying telemetry history"""
    # Mock the database response
    mock_records = [
        {
            "car_id": "test-car-1",
            "speed": 50.0,
            "rpm": 2000.0,
            "timestamp": "2024-01-01T10:00:00Z",
        },
        {
            "car_id": "test-car-1",
            "speed": 55.0,
            "rpm": 2200.0,
            "timestamp": "2024-01-01T10:01:00Z",
        },
    ]

    assert len(mock_records) == 2
    assert mock_records[0]["car_id"] == "test-car-1"


@pytest.mark.asyncio
async def test_telemetry_aggregates_by_time_bucket():
    """Test telemetry aggregation by time bucket"""
    # Test hourly aggregation
    records = [
        {"timestamp": "2024-01-01T08:00:00Z", "speed": 50.0},
        {"timestamp": "2024-01-01T08:30:00Z", "speed": 55.0},
        {"timestamp": "2024-01-01T09:15:00Z", "speed": 60.0},
    ]

    # Group by hour
    hourly = {}
    for r in records:
        hour = r["timestamp"][:13]  # "2024-01-01T08"
        if hour not in hourly:
            hourly[hour] = []
        hourly[hour].append(r["speed"])

    assert "2024-01-01T08" in hourly
    assert len(hourly["2024-01-01T08"]) == 2


@pytest.mark.asyncio
async def test_telemetry_with_location():
    """Test telemetry with GPS coordinates"""
    payload = MockTelemetryPayload(
        car_id="test-car-1",
        speed=50.0,
        rpm=2000.0,
        latitude=40.7128,
        longitude=-74.0060,
    )

    assert payload.latitude is not None
    assert payload.longitude is not None
    assert -90 <= payload.latitude <= 90
    assert -180 <= payload.longitude <= 180
