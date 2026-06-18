"""API routes for telemetry ingestion and retrieval."""

import logging
from datetime import datetime, timedelta
from typing import Optional, Union
import uuid

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from ....db.session import get_db
from ....middleware.auth import get_current_user, get_current_device
from ....domain.models import User, DeviceAPIKey
from backend.api.v1.schemas.telemetry import (
    TelemetryIngestRequest,
    TelemetryIngestResponse,
    TelemetryHistoryRequest,
    TelemetryHistoryResponse,
    TelemetryLatestResponse,
)
from backend.services.telemetry import TelemetryService
from backend.services.websocket_manager import manager

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/telemetry", tags=["telemetry"])


async def get_telemetry_auth(
    user: User = Depends(get_current_user),
    device: DeviceAPIKey = Depends(get_current_device),
) -> tuple[Union[User, DeviceAPIKey], bool]:
    return (user, True) if user else (device, False)


async def get_optional_auth(
    user: Optional[User] = Depends(get_current_user),
    device: Optional[DeviceAPIKey] = Depends(get_current_device),
) -> tuple[Optional[Union[User, DeviceAPIKey]], bool]:
    return (user, True) if user else (device, False)


@router.post(
    "/ingest",
    response_model=TelemetryIngestResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Ingest telemetry data",
    description="Ingest OBD telemetry data from a vehicle. Triggers background threshold checking and broadcasts to WebSocket subscribers.",
)
async def ingest_telemetry(
    data: TelemetryIngestRequest,
    auth: tuple[Optional[Union[User, DeviceAPIKey]], bool] = Depends(get_optional_auth),
    db: AsyncSession = Depends(get_db),
):
    """
    Ingest telemetry data from a vehicle.

    - Validates JWT or API key and extracts organization_id
    - Verifies car belongs to organization (multi-tenant isolation)
    - Stores telemetry in database
    - Triggers background tasks for threshold checking
    - Broadcasts to WebSocket subscribers in car:{car_id} room
    """
    auth_user, is_user = auth

    if is_user and auth_user:
        organization_id = auth_user.organization_id
        current_user: User = auth_user
    elif auth_user:
        organization_id = auth_user.organization_id
        current_user = None
    else:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Authentication required"
        )

    service = TelemetryService(db)

    try:
        obd_data = await service.ingest_telemetry(data, organization_id)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except Exception as e:
        logger.error(f"Error ingesting telemetry: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to ingest telemetry data",
        )

    # Broadcast to WebSocket subscribers
    try:
        await manager.broadcast_to_car(
            data.car_id,
            {
                "type": "telemetry",
                "data": {
                    "car_id": str(data.car_id),
                    "time": data.time.isoformat(),
                    "rpm": data.rpm,
                    "speed": data.speed,
                    "coolant_temp": data.coolant_temp,
                    "engine_load": data.engine_load,
                    "fuel_level": data.fuel_level,
                    "latitude": data.latitude,
                    "longitude": data.longitude,
                    "dtc_codes": data.dtc_codes,
                    "mil_status": data.mil_status,
                },
            },
        )
    except Exception as e:
        logger.error(f"WebSocket broadcast error: {e}")

    return TelemetryIngestResponse(
        success=True,
        message="Telemetry data ingested successfully",
        time=obd_data.time,
        car_id=obd_data.car_id,
    )


@router.get(
    "/history",
    response_model=TelemetryHistoryResponse,
    summary="Get telemetry history",
    description="Query historical telemetry data with time range and optional aggregation.",
)
async def get_telemetry_history(
    car_id: uuid.UUID = Query(..., description="UUID of the car"),
    start: datetime = Query(..., description="Start time (ISO 8601)"),
    end: datetime = Query(..., description="End time (ISO 8601)"),
    metrics: Optional[str] = Query(None, description="Comma-separated list of metrics"),
    limit: int = Query(1000, ge=1, le=10000),
    offset: int = Query(0, ge=0),
    aggregate: Optional[str] = Query(None, description="Aggregation: hourly, daily"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Query historical telemetry data.

    - Supports query parameters: car_id, start, end, metrics (comma-separated)
    - Validates user has access to requested car
    - Returns paginated time-series data
    - Supports TimescaleDB time_bucket for aggregated queries
    """
    if end <= start:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="End time must be after start time",
        )

    # Parse metrics
    metrics_list = None
    if metrics:
        metrics_list = [m.strip() for m in metrics.split(",")]

    service = TelemetryService(db)

    try:
        result = await service.get_history(
            car_id=car_id,
            organization_id=current_user.organization_id,
            start=start,
            end=end,
            metrics=metrics_list,
            limit=limit,
            offset=offset,
            aggregate=aggregate,
        )
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except Exception as e:
        logger.error(f"Error getting telemetry history: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve telemetry history",
        )

    return result


@router.get(
    "/latest/{car_id}",
    response_model=TelemetryLatestResponse,
    summary="Get latest telemetry",
    description="Get the most recent telemetry data for a specific car.",
)
async def get_latest_telemetry(
    car_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Get the latest telemetry data for a car.
    """
    service = TelemetryService(db)

    try:
        result = await service.get_latest(car_id, current_user.organization_id)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except Exception as e:
        logger.error(f"Error getting latest telemetry: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve latest telemetry",
        )

    if result is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No telemetry data found for this car",
        )

    return result


@router.get(
    "/cars",
    summary="List cars with telemetry",
    description="List all cars in the organization that have telemetry data.",
)
async def list_cars_with_telemetry(
    current_user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)
):
    """
    List all cars in the organization with their latest telemetry timestamps.
    """
    from sqlalchemy import select, func, and_
    from backend.domain.models import Car, OBDData

    # Get cars with latest telemetry time
    subquery = (
        select(OBDData.car_id, func.max(OBDData.time).label("last_telemetry"))
        .filter(OBDData.organization_id == current_user.organization_id)
        .group_by(OBDData.car_id)
        .subquery()
    )

    query = (
        select(
            Car.id,
            Car.vin,
            Car.license_plate,
            Car.make,
            Car.model,
            Car.year,
            subquery.c.last_telemetry,
        )
        .outerjoin(subquery, Car.id == subquery.c.car_id)
        .filter(
            Car.organization_id == current_user.organization_id, Car.is_active == True
        )
        .order_by(subquery.c.last_telemetry.desc().nullslast())
    )

    result = await db.execute(query)
    rows = result.fetchall()

    cars = [
        {
            "id": str(row.id),
            "vin": row.vin,
            "license_plate": row.license_plate,
            "make": row.make,
            "model": row.model,
            "year": row.year,
            "last_telemetry": row.last_telemetry.isoformat()
            if row.last_telemetry
            else None,
        }
        for row in rows
    ]

    return {"cars": cars}
