"""API routes for geofencing, driver scoring, maintenance, and fuel anomalies."""

import logging
from typing import Optional
from datetime import datetime, timedelta, timezone
import uuid

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession
from pydantic import BaseModel

from db.session import get_db
from middleware.auth import get_current_user
from domain.models import User, UserRole, GeofenceType, MaintenanceType
from services.geofence import GeofenceService
from services.driver import DriverScoreService, MaintenanceService
from services.fuel_anomaly import FuelAnomalyService
from services.trips import TripDetectionService

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/fleet", tags=["fleet_operations"])


# ==================== GEOFENCING ====================


class GeofenceCreateRequest(BaseModel):
    name: str
    geofence_type: str  # warehouse, job_site, restricted, customer_location, home
    geometry: dict  # {"type": "Point", "coordinates": [lng, lat], "radius": 500}
    description: Optional[str] = None
    notify_on_entry: bool = True
    notify_on_exit: bool = True


class LocationCheckRequest(BaseModel):
    car_id: uuid.UUID
    latitude: float
    longitude: float


@router.post("/geofences", summary="Create geofence")
async def create_geofence(
    request: GeofenceCreateRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Create a new geofence."""
    if current_user.role not in [UserRole.admin, UserRole.fleet_manager]:
        raise HTTPException(status_code=403, detail="Admin or fleet manager required")

    service = GeofenceService(db)

    try:
        geofence = await service.create_geofence(
            organization_id=current_user.organization_id,
            name=request.name,
            geofence_type=request.geofence_type,
            geometry=request.geometry,
            description=request.description,
            notify_on_entry=request.notify_on_entry,
            notify_on_exit=request.notify_on_exit,
        )
    except Exception as e:
        logger.error(f"Error creating geofence: {e}")
        raise HTTPException(status_code=500, detail="Failed to create geofence")

    return {
        "id": str(geofence.id),
        "name": geofence.name,
        "type": geofence.geofence_type.value,
        "geometry": geofence.geometry,
    }


@router.get("/geofences", summary="List geofences")
async def list_geofences(
    geofence_type: Optional[str] = Query(None),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get all geofences for the organization."""
    service = GeofenceService(db)

    geofences = await service.get_geofences(
        organization_id=current_user.organization_id, geofence_type=geofence_type
    )

    return {
        "geofences": [
            {
                "id": str(g.id),
                "name": g.name,
                "type": g.geofence_type.value,
                "geometry": g.geometry,
                "description": g.description,
                "is_active": g.is_active,
            }
            for g in geofences
        ]
    }


@router.post("/geofences/check", summary="Check location against geofences")
async def check_location(
    request: LocationCheckRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Check if a location triggers any geofence events."""
    service = GeofenceService(db)

    events = await service.check_location(
        car_id=request.car_id,
        latitude=request.latitude,
        longitude=request.longitude,
        organization_id=current_user.organization_id,
    )

    # Broadcast events to WebSocket
    if events:
        try:
            from services.websocket_manager import manager

            for event in events:
                if event.get("notify"):
                    await manager.broadcast_to_car(
                        request.car_id, {"type": "geofence_event", "data": event}
                    )
        except Exception as e:
            logger.error(f"WebSocket error: {e}")

    return {"events": events}


# ==================== DRIVER SCORING ====================


@router.get("/drivers/leaderboard", summary="Get driver leaderboard")
async def get_driver_leaderboard(
    days: int = Query(7, ge=1, le=90),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get driver leaderboard sorted by score."""
    if current_user.role not in [UserRole.admin, UserRole.fleet_manager]:
        raise HTTPException(status_code=403, detail="Admin or fleet manager required")

    service = DriverScoreService(db)

    end = datetime.now(timezone.utc)
    start = end - timedelta(days=days)

    leaderboard = await service.get_driver_leaderboard(
        organization_id=current_user.organization_id, period_start=start, period_end=end
    )

    return {"leaderboard": leaderboard}


@router.post("/drivers/scores/calculate", summary="Calculate driver scores")
async def calculate_driver_scores(
    date: Optional[datetime] = Query(None),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Calculate daily driver scores."""
    if current_user.role not in [UserRole.admin, UserRole.fleet_manager]:
        raise HTTPException(status_code=403, detail="Admin or fleet manager required")

    service = DriverScoreService(db)

    scores = await service.calculate_daily_scores(
        organization_id=current_user.organization_id, date=date
    )

    return {"scores_count": len(scores)}


# ==================== MAINTENANCE ====================


class MaintenanceScheduleRequest(BaseModel):
    car_id: uuid.UUID
    maintenance_type: str
    scheduled_date: datetime
    description: Optional[str] = None
    estimated_cost: Optional[float] = None


@router.post("/maintenance", summary="Schedule maintenance")
async def schedule_maintenance(
    request: MaintenanceScheduleRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Schedule vehicle maintenance."""
    if current_user.role not in [UserRole.admin, UserRole.fleet_manager]:
        raise HTTPException(status_code=403, detail="Admin or fleet manager required")

    service = MaintenanceService(db)

    try:
        schedule = await service.create_maintenance_schedule(
            organization_id=current_user.organization_id,
            car_id=request.car_id,
            maintenance_type=request.maintenance_type,
            scheduled_date=request.scheduled_date,
            description=request.description,
            estimated_cost=request.estimated_cost,
        )
    except Exception as e:
        logger.error(f"Error scheduling maintenance: {e}")
        raise HTTPException(status_code=500, detail="Failed to schedule maintenance")

    return {"id": str(schedule.id), "status": schedule.status.value}


@router.get("/maintenance/upcoming", summary="Get upcoming maintenance")
async def get_upcoming_maintenance(
    days: int = Query(30, ge=1, le=365),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get upcoming maintenance schedules."""
    service = MaintenanceService(db)

    schedules = await service.get_upcoming_maintenance(
        organization_id=current_user.organization_id, days_ahead=days
    )

    return {"maintenance": schedules}


@router.post("/maintenance/{car_id}/predict", summary="Predict maintenance needs")
async def predict_maintenance(
    car_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Predict maintenance needs based on telemetry."""
    service = MaintenanceService(db)

    predictions = await service.predict_maintenance_needs(
        car_id=car_id, organization_id=current_user.organization_id
    )

    return {"predictions": predictions}


# ==================== FUEL ANOMALIES ====================


@router.post("/fuel/analyze", summary="Analyze fuel consumption")
async def analyze_fuel(
    car_id: uuid.UUID,
    days: int = Query(7, ge=1, le=30),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Analyze fuel consumption and detect anomalies."""
    service = FuelAnomalyService(db)

    result = await service.analyze_fuel_consumption(
        car_id=car_id, organization_id=current_user.organization_id, days=days
    )

    return result


@router.get("/fuel/anomalies", summary="Get fuel anomalies")
async def get_fuel_anomalies(
    car_id: Optional[uuid.UUID] = Query(None),
    anomaly_type: Optional[str] = Query(None),
    is_confirmed: Optional[bool] = Query(None),
    limit: int = Query(50, ge=1, le=200),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get fuel anomaly records."""
    service = FuelAnomalyService(db)

    anomalies = await service.get_fuel_anomalies(
        organization_id=current_user.organization_id,
        car_id=car_id,
        anomaly_type=anomaly_type,
        is_confirmed=is_confirmed,
        limit=limit,
    )

    return {
        "anomalies": [
            {
                "id": str(a.id),
                "car_id": str(a.car_id),
                "type": a.anomaly_type.value,
                "severity": a.severity.value,
                "detected_at": a.detected_at.isoformat(),
                "expected_fuel_l": a.expected_fuel_l,
                "actual_fuel_l": a.actual_fuel_l,
                "description": a.description,
                "is_investigated": a.is_investigated,
                "is_confirmed": a.is_confirmed,
            }
            for a in anomalies
        ]
    }


@router.post(
    "/fuel/anomalies/{anomaly_id}/investigate", summary="Mark anomaly as investigated"
)
async def investigate_anomaly(
    anomaly_id: uuid.UUID,
    is_confirmed: bool = Query(False),
    notes: Optional[str] = Query(None),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Mark a fuel anomaly as investigated."""
    service = FuelAnomalyService(db)

    try:
        anomaly = await service.mark_anomaly_investigated(
            anomaly_id=anomaly_id,
            organization_id=current_user.organization_id,
            is_confirmed=is_confirmed,
            notes=notes,
        )
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))

    return {"id": str(anomaly.id), "is_confirmed": anomaly.is_confirmed}


# ==================== TRIPS ====================


@router.get("/trips/{car_id}", summary="Get detected trips")
async def get_trips(
    car_id: uuid.UUID,
    days: int = Query(30, ge=1, le=90),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Detect and analyze vehicle trips."""
    from datetime import timedelta

    service = TripDetectionService(db)

    end_time = datetime.now(timezone.utc)
    start_time = end_time - timedelta(days=days)

    trips = await service.detect_trips(car_id, start_time, end_time)

    return {
        "trips": [
            {
                "start_time": t["start_time"].isoformat(),
                "end_time": t["end_time"].isoformat(),
                "start_location": t.get("start_location"),
                "end_location": t.get("end_location"),
                "distance_km": round(t["total_distance_km"], 2),
                "max_speed": t["max_speed"],
                "location_count": len(t["locations"]),
            }
            for t in trips
        ]
    }


@router.get("/trips/{car_id}/summary", summary="Get trip summary")
async def get_trip_summary(
    car_id: uuid.UUID,
    days: int = Query(30, ge=1, le=90),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get trip summary statistics."""
    service = TripDetectionService(db)

    summary = await service.get_trip_summary(car_id, days)

    return summary


# ==================== DEVICE API KEYS ====================


class DeviceAPIKeyCreateRequest(BaseModel):
    car_id: uuid.UUID
    name: str


class DeviceAPIKeyResponse(BaseModel):
    id: str
    car_id: str
    name: str
    key: str
    is_active: bool
    created_at: str


@router.post("/api-keys", summary="Create device API key")
async def create_api_key(
    request: DeviceAPIKeyCreateRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Create a new API key for a car. Admin only."""
    if current_user.role not in [UserRole.admin, UserRole.fleet_manager]:
        raise HTTPException(status_code=403, detail="Admin or fleet manager required")

    from sqlalchemy.future import select
    from domain.models import Car

    result = await db.execute(
        select(Car).filter(
            Car.id == request.car_id,
            Car.organization_id == current_user.organization_id,
        )
    )
    car = result.scalars().first()
    if not car:
        raise HTTPException(status_code=404, detail="Car not found")

    from services import api_keys as api_key_service

    raw_key = api_key_service.generate_api_key()
    key_hash = api_key_service.hash_api_key(raw_key)

    from domain.models import DeviceAPIKey

    api_key = DeviceAPIKey(
        organization_id=current_user.organization_id,
        car_id=request.car_id,
        key_hash=key_hash,
        name=request.name,
        is_active=True,
    )
    db.add(api_key)
    await db.flush()

    return DeviceAPIKeyResponse(
        id=str(api_key.id),
        car_id=str(api_key.car_id),
        name=api_key.name,
        key=raw_key,
        is_active=api_key.is_active,
        created_at=api_key.created_at.isoformat(),
    )


@router.get("/api-keys", summary="List device API keys")
async def list_api_keys(
    car_id: Optional[uuid.UUID] = Query(None),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """List all API keys for the organization. Admin only."""
    if current_user.role not in [UserRole.admin, UserRole.fleet_manager]:
        raise HTTPException(status_code=403, detail="Admin or fleet manager required")

    from sqlalchemy.future import select
    from domain.models import DeviceAPIKey

    query = select(DeviceAPIKey).filter(
        DeviceAPIKey.organization_id == current_user.organization_id
    )
    if car_id:
        query = query.filter(DeviceAPIKey.car_id == car_id)

    result = await db.execute(query.order_by(DeviceAPIKey.created_at.desc()))
    keys = result.scalars().all()

    return {
        "api_keys": [
            {
                "id": str(k.id),
                "car_id": str(k.car_id),
                "name": k.name,
                "is_active": k.is_active,
                "last_used_at": k.last_used_at.isoformat() if k.last_used_at else None,
                "created_at": k.created_at.isoformat(),
            }
            for k in keys
        ]
    }


@router.delete("/api-keys/{key_id}", summary="Revoke device API key")
async def revoke_api_key(
    key_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Revoke an API key. Admin only."""
    if current_user.role not in [UserRole.admin, UserRole.fleet_manager]:
        raise HTTPException(status_code=403, detail="Admin or fleet manager required")

    from sqlalchemy.future import select
    from domain.models import DeviceAPIKey

    result = await db.execute(
        select(DeviceAPIKey).filter(
            DeviceAPIKey.id == key_id,
            DeviceAPIKey.organization_id == current_user.organization_id,
        )
    )
    api_key = result.scalars().first()
    if not api_key:
        raise HTTPException(status_code=404, detail="API key not found")

    api_key.is_active = False
    await db.flush()

    return {"message": "API key revoked successfully"}


# ==================== ADMIN USER MANAGEMENT ====================


class UserCreateRequest(BaseModel):
    email: str
    full_name: str
    role: str
    password: str


class UserUpdateRequest(BaseModel):
    full_name: Optional[str] = None
    role: Optional[str] = None
    is_active: Optional[bool] = None


class AssignCarRequest(BaseModel):
    user_id: uuid.UUID
    car_id: uuid.UUID


@router.post("/users", summary="Create user (admin)")
async def create_user(
    request: UserCreateRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Create a new user (admin only)."""
    if current_user.role != UserRole.admin:
        raise HTTPException(status_code=403, detail="Admin role required")

    from sqlalchemy.future import select
    from passlib.hash import bcrypt

    result = await db.execute(
        select(User).filter(
            User.email == request.email,
            User.organization_id == current_user.organization_id,
        )
    )
    existing = result.scalars().first()
    if existing:
        raise HTTPException(status_code=400, detail="Email already in use")

    new_user = User(
        email=request.email,
        full_name=request.full_name,
        organization_id=current_user.organization_id,
        password_hash=bcrypt.hash(request.password),
        role=UserRole(request.role)
        if request.role in [r.value for r in UserRole]
        else UserRole.driver,
        is_active=True,
    )
    db.add(new_user)
    await db.commit()
    await db.refresh(new_user)

    return {
        "id": str(new_user.id),
        "email": new_user.email,
        "full_name": new_user.full_name,
        "role": new_user.role.value,
    }


@router.get("/users", summary="List users (admin)")
async def list_users(
    role: Optional[str] = Query(None),
    is_active: Optional[bool] = Query(None),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """List all users in organization (admin only)."""
    if current_user.role != UserRole.admin:
        raise HTTPException(status_code=403, detail="Admin role required")

    from sqlalchemy.future import select

    filters = [User.organization_id == current_user.organization_id]

    if role:
        filters.append(User.role == role)
    if is_active is not None:
        filters.append(User.is_active == is_active)

    result = await db.execute(select(User).filter(*filters).order_by(User.full_name))
    users = result.scalars().all()

    return [
        {
            "id": str(u.id),
            "email": u.email,
            "full_name": u.full_name,
            "role": u.role.value,
            "is_active": u.is_active,
            "created_at": u.created_at.isoformat(),
        }
        for u in users
    ]


@router.get("/users/{user_id}", summary="Get user details (admin)")
async def get_user(
    user_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get user details (admin only)."""
    if current_user.role != UserRole.admin:
        raise HTTPException(status_code=403, detail="Admin role required")

    from sqlalchemy.future import select
    from domain.models import Car

    result = await db.execute(
        select(User).filter(
            User.id == user_id, User.organization_id == current_user.organization_id
        )
    )
    user = result.scalars().first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    cars_result = await db.execute(
        select(Car).filter(
            Car.assigned_driver_id == user_id,
            Car.organization_id == current_user.organization_id,
        )
    )
    cars = cars_result.scalars().all()

    return {
        "id": str(user.id),
        "email": user.email,
        "full_name": user.full_name,
        "role": user.role.value,
        "is_active": user.is_active,
        "created_at": user.created_at.isoformat(),
        "assigned_cars": [
            {
                "id": str(c.id),
                "license_plate": c.license_plate,
                "make": c.make,
                "model": c.model,
            }
            for c in cars
        ],
    }


@router.patch("/users/{user_id}", summary="Update user (admin)")
async def update_user(
    user_id: uuid.UUID,
    request: UserUpdateRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Update user details (admin only)."""
    if current_user.role != UserRole.admin:
        raise HTTPException(status_code=403, detail="Admin role required")

    from sqlalchemy.future import select

    result = await db.execute(
        select(User).filter(
            User.id == user_id, User.organization_id == current_user.organization_id
        )
    )
    user = result.scalars().first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    if request.full_name is not None:
        user.full_name = request.full_name
    if request.role is not None:
        user.role = UserRole(request.role)
    if request.is_active is not None:
        user.is_active = request.is_active

    await db.commit()
    await db.refresh(user)

    return {
        "id": str(user.id),
        "email": user.email,
        "full_name": user.full_name,
        "role": user.role.value,
        "is_active": user.is_active,
    }


@router.delete("/users/{user_id}", summary="Delete user (admin)")
async def delete_user(
    user_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Deactivate user (admin only)."""
    if current_user.role != UserRole.admin:
        raise HTTPException(status_code=403, detail="Admin role required")

    from sqlalchemy.future import select

    result = await db.execute(
        select(User).filter(
            User.id == user_id, User.organization_id == current_user.organization_id
        )
    )
    user = result.scalars().first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    if user.id == current_user.id:
        raise HTTPException(status_code=400, detail="Cannot deactivate yourself")

    user.is_active = False
    await db.commit()

    return {"message": "User deactivated successfully"}


@router.post("/users/assign-car", summary="Assign car to driver (admin)")
async def assign_car_to_driver(
    request: AssignCarRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Assign a car to a driver (admin only)."""
    if current_user.role != UserRole.admin:
        raise HTTPException(status_code=403, detail="Admin role required")

    from sqlalchemy.future import select
    from domain.models import Car

    user_result = await db.execute(
        select(User).filter(
            User.id == request.user_id,
            User.organization_id == current_user.organization_id,
        )
    )
    user = user_result.scalars().first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    car_result = await db.execute(
        select(Car).filter(
            Car.id == request.car_id,
            Car.organization_id == current_user.organization_id,
        )
    )
    car = car_result.scalars().first()
    if not car:
        raise HTTPException(status_code=404, detail="Car not found")

    car.assigned_driver_id = user.id
    await db.commit()

    return {"message": f"Car {car.license_plate} assigned to {user.full_name}"}
