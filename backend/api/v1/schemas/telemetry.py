"""Pydantic schemas for telemetry data."""

from datetime import datetime, timezone
from typing import Optional, List, Any
from pydantic import BaseModel, Field, field_validator
import uuid


class TelemetryIngestRequest(BaseModel):
    """Schema for ingesting telemetry data."""

    car_id: uuid.UUID = Field(..., description="UUID of the car")
    time: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        description="Timestamp of the reading",
    )

    # Engine metrics
    rpm: Optional[int] = Field(None, ge=0, le=10000, description="Engine RPM")
    speed: Optional[int] = Field(
        None, ge=0, le=300, description="Vehicle speed in km/h"
    )
    throttle_position: Optional[float] = Field(
        None, ge=0, le=100, description="Throttle position in %"
    )
    engine_load: Optional[float] = Field(
        None, ge=0, le=100, description="Engine load in %"
    )
    coolant_temp: Optional[int] = Field(
        None, ge=-40, le=150, description="Coolant temperature in °C"
    )
    intake_temp: Optional[int] = Field(
        None, ge=-40, le=100, description="Intake air temperature in °C"
    )

    # Fuel metrics
    fuel_level: Optional[float] = Field(
        None, ge=0, le=100, description="Fuel level in %"
    )
    fuel_rate: Optional[float] = Field(
        None, ge=0, description="Fuel consumption rate L/h"
    )
    fuel_pressure: Optional[float] = Field(None, ge=0, description="Fuel pressure kPa")

    # Air/Emissions
    maf_rate: Optional[float] = Field(None, ge=0, description="MAF air flow rate g/s")
    o2_voltage: Optional[float] = Field(
        None, ge=0, le=2, description="O2 sensor voltage"
    )

    # Location
    latitude: Optional[float] = Field(None, ge=-90, le=90, description="Latitude")
    longitude: Optional[float] = Field(None, ge=-180, le=180, description="Longitude")

    # Diagnostic
    dtc_codes: Optional[List[str]] = Field(None, description="Diagnostic Trouble Codes")
    mil_status: Optional[bool] = Field(
        None, description="Malfunction Indicator Lamp status"
    )
    raw_data: Optional[dict] = Field(None, description="Raw OBD data")

    @field_validator("dtc_codes")
    @classmethod
    def validate_dtc_codes(cls, v):
        if v is not None:
            # Basic DTC format validation (e.g., "P0128", "C0035")
            for code in v:
                if not isinstance(code, str) or len(code) < 4:
                    raise ValueError(f"Invalid DTC code format: {code}")
        return v

    class Config:
        json_schema_extra = {
            "example": {
                "car_id": "123e4567-e89b-12d3-a456-426614174000",
                "rpm": 2500,
                "speed": 80,
                "throttle_position": 45.5,
                "engine_load": 35.2,
                "coolant_temp": 90,
                "fuel_level": 75.0,
                "latitude": 40.7128,
                "longitude": -74.0060,
                "dtc_codes": [],
                "mil_status": False,
            }
        }


class TelemetryIngestResponse(BaseModel):
    success: bool = True
    message: str = "Telemetry data ingested successfully"
    time: datetime
    car_id: uuid.UUID


class TelemetryBatchIngestRequest(BaseModel):
    items: List[TelemetryIngestRequest] = Field(..., max_length=50)


class TelemetryHistoryRequest(BaseModel):
    """Query parameters for telemetry history."""

    car_id: uuid.UUID = Field(..., description="UUID of the car")
    start: datetime = Field(..., description="Start time for query")
    end: datetime = Field(..., description="End time for query")
    metrics: Optional[List[str]] = Field(
        None, description="List of metrics to retrieve (comma-separated in query)"
    )
    limit: int = Field(1000, ge=1, le=10000, description="Maximum records to return")
    offset: int = Field(0, ge=0, description="Records to skip")
    aggregate: Optional[str] = Field(
        None, description="Aggregation: hourly, daily, or None for raw data"
    )


class TelemetryPoint(BaseModel):
    """Single telemetry data point."""

    time: datetime
    rpm: Optional[int] = None
    speed: Optional[int] = None
    throttle_position: Optional[float] = None
    engine_load: Optional[float] = None
    coolant_temp: Optional[int] = None
    intake_temp: Optional[int] = None
    fuel_level: Optional[float] = None
    fuel_rate: Optional[float] = None
    fuel_pressure: Optional[float] = None
    maf_rate: Optional[float] = None
    o2_voltage: Optional[float] = None
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    dtc_codes: Optional[List[str]] = None
    mil_status: Optional[bool] = None


class TelemetryHistoryResponse(BaseModel):
    """Response with telemetry history data."""

    car_id: uuid.UUID
    start: datetime
    end: datetime
    aggregate: Optional[str] = None
    data: List[TelemetryPoint]
    total: int
    limit: int
    offset: int


class TelemetryLatestResponse(BaseModel):
    """Latest telemetry data for a car."""

    car_id: uuid.UUID
    time: datetime
    rpm: Optional[int] = None
    speed: Optional[int] = None
    throttle_position: Optional[float] = None
    engine_load: Optional[float] = None
    coolant_temp: Optional[int] = None
    fuel_level: Optional[float] = None
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    dtc_codes: Optional[List[str]] = None
    mil_status: Optional[bool] = None
