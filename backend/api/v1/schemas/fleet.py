"""Fleet operation schemas."""

from typing import Optional, List
from pydantic import BaseModel, Field
import uuid


class GeofenceCreate(BaseModel):
    """Schema for creating a geofence."""

    name: str = Field(..., min_length=1, max_length=255)
    geofence_type: str = Field(
        ..., description="warehouse, job_site, restricted, customer_location, home"
    )
    geometry: dict = Field(..., description="GeoJSON geometry")
    description: Optional[str] = None
    notify_on_entry: bool = True
    notify_on_exit: bool = True


class GeofenceResponse(BaseModel):
    """Geofence response schema."""

    id: str
    name: str
    geofence_type: str
    geometry: dict
    description: Optional[str]
    notify_on_entry: bool
    notify_on_exit: bool
    created_at: str

    class Config:
        from_attributes = True


class LocationCheck(BaseModel):
    """Check if car is within geofence."""

    car_id: uuid.UUID
    latitude: float = Field(..., ge=-90, le=90)
    longitude: float = Field(..., ge=-180, le=180)


class LocationCheckResponse(BaseModel):
    """Location check response."""

    inside: bool
    geofence_id: Optional[str]
    geofence_name: Optional[str]
    distance_meters: Optional[float]


class MaintenanceCreate(BaseModel):
    """Create maintenance record."""

    car_id: uuid.UUID
    maintenance_type: str = Field(
        ..., description="oil_change, tire_rotation, brake_service, etc."
    )
    description: Optional[str] = None
    scheduled_date: Optional[str] = None
    cost: Optional[float] = Field(None, ge=0)
    mileage: Optional[int] = Field(None, ge=0)


class MaintenanceResponse(BaseModel):
    """Maintenance record response."""

    id: str
    car_id: str
    maintenance_type: str
    description: Optional[str]
    scheduled_date: Optional[str]
    completed_date: Optional[str]
    cost: Optional[float]
    mileage: Optional[int]
    created_by: str
    created_at: str

    class Config:
        from_attributes = True


class FuelAnalysisRequest(BaseModel):
    """Request fuel anomaly analysis."""

    car_id: uuid.UUID
    start_date: str
    end_date: str


class FuelAnomalyResponse(BaseModel):
    """Fuel anomaly analysis response."""

    car_id: str
    analysis_date: str
    anomalies: List[dict]
    summary: dict


class DriverScoreRequest(BaseModel):
    """Request driver score calculation."""

    car_id: uuid.UUID
    start_date: str
    end_date: str


class DriverScoreResponse(BaseModel):
    """Driver score response."""

    car_id: str
    driver_name: str
    safety_score: float
    efficiency_score: float
    total_score: float
    trip_count: int
    total_distance_km: float
    total_fuel_liters: float
