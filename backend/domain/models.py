import enum
import uuid
from datetime import datetime, timezone
from typing import Optional, List, Any

from sqlalchemy import (
    Column,
    String,
    Integer,
    Boolean,
    DateTime,
    Enum,
    ForeignKey,
    Text,
    JSON,
    Float,
    UniqueConstraint,
    Index,
    Numeric,
    CheckConstraint,
)
from sqlalchemy.dialects.postgresql import UUID, JSONB, ARRAY
from sqlalchemy.orm import relationship, declarative_base, Mapped, mapped_column

Base = declarative_base()


# --- Enums ---
class UserRole(str, enum.Enum):
    admin = "admin"
    fleet_manager = "fleet_manager"
    driver = "driver"


class AlertType(str, enum.Enum):
    dtc_error = "dtc_error"
    threshold_exceeded = "threshold_exceeded"
    maintenance_due = "maintenance_due"
    anomaly_detected = "anomaly_detected"
    system = "system"


class AlertSeverity(str, enum.Enum):
    info = "info"
    warning = "warning"
    critical = "critical"


class MessageScope(str, enum.Enum):
    car = "car"
    organization = "organization"


class MessageType(str, enum.Enum):
    chat = "chat"
    alert = "alert"
    command = "command"
    ai_reply = "ai_reply"
    system = "system"


class SenderType(str, enum.Enum):
    user = "user"
    ai = "ai"
    system = "system"


class AISessionType(str, enum.Enum):
    diagnostic = "diagnostic"
    analysis = "analysis"
    chat = "chat"
    proactive_alert = "proactive_alert"


# --- New Enums for Additional Features ---


class GeofenceType(str, enum.Enum):
    warehouse = "warehouse"
    job_site = "job_site"
    restricted = "restricted"
    customer_location = "customer_location"
    home = "home"


class MaintenanceType(str, enum.Enum):
    oil_change = "oil_change"
    tire_rotation = "tire_rotation"
    brake_service = "brake_service"
    transmission = "transmission"
    battery = "battery"
    coolant = "coolant"
    inspection = "inspection"
    general = "general"


class MaintenanceStatus(str, enum.Enum):
    scheduled = "scheduled"
    in_progress = "in_progress"
    completed = "completed"
    overdue = "overdue"
    cancelled = "cancelled"


class DriverScorePeriod(str, enum.Enum):
    daily = "daily"
    weekly = "weekly"
    monthly = "monthly"


class AnomalyType(str, enum.Enum):
    fuel_theft = "fuel_theft"
    unusual_consumption = "unusual_consumption"
    unauthorized_use = "unauthorized_use"
    route_deviation = "route_deviation"
    after_hours_use = "after_hours_use"


# --- Models ---


class Organization(Base):
    __tablename__ = "organizations"
    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    slug: Mapped[str] = mapped_column(
        String(100), unique=True, nullable=False, index=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )
    settings: Mapped[Any] = mapped_column(JSONB, default=dict)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)

    users: Mapped[List["User"]] = relationship(
        "User", back_populates="organization", lazy="selectin"
    )
    cars: Mapped[List["Car"]] = relationship(
        "Car", back_populates="organization", lazy="selectin"
    )


class User(Base):
    __tablename__ = "users"
    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    organization_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("organizations.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    email: Mapped[str] = mapped_column(
        String(255), unique=True, nullable=False, index=True
    )
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    full_name: Mapped[str] = mapped_column(String(255), nullable=False)
    role: Mapped[UserRole] = mapped_column(Enum(UserRole), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )
    last_login_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)

    organization: Mapped["Organization"] = relationship(
        "Organization", back_populates="users", lazy="joined"
    )
    assigned_cars: Mapped[List["Car"]] = relationship(
        "Car",
        back_populates="assigned_driver",
        foreign_keys="[Car.assigned_driver_id]",
        lazy="selectin",
    )


class Car(Base):
    __tablename__ = "cars"
    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    organization_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("organizations.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    vin: Mapped[str] = mapped_column(
        String(17), unique=True, nullable=False, index=True
    )
    license_plate: Mapped[str] = mapped_column(String(20), nullable=False)
    make: Mapped[str] = mapped_column(String(100), nullable=False)
    model: Mapped[str] = mapped_column(String(100), nullable=False)
    year: Mapped[int] = mapped_column(Integer, nullable=False)
    assigned_driver_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )
    car_metadata: Mapped[Any] = mapped_column("metadata", JSONB, default=dict)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)

    organization: Mapped["Organization"] = relationship(
        "Organization", back_populates="cars", lazy="joined"
    )
    assigned_driver: Mapped[Optional["User"]] = relationship(
        "User",
        back_populates="assigned_cars",
        foreign_keys=[assigned_driver_id],
        lazy="joined",
    )
    devices: Mapped[List["Device"]] = relationship(
        "Device", back_populates="car", lazy="selectin"
    )


class Device(Base):
    __tablename__ = "devices"
    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    car_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("cars.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    device_type: Mapped[str] = mapped_column(String(50), default="ELM327")
    mac_address: Mapped[str] = mapped_column(
        String(17), unique=True, nullable=False, index=True
    )
    firmware_version: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    last_seen_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)

    car: Mapped["Car"] = relationship("Car", back_populates="devices", lazy="joined")


# TimescaleDB Hypertable: Special migration operations required for hypertable, not here.
class OBDData(Base):
    __tablename__ = "obd_data"
    __table_args__ = (
        UniqueConstraint("time", "car_id", name="uix_obd_data_time_car"),
        UniqueConstraint("car_id", "source_message_id", name="uix_obd_data_source_msg"),
        Index("idx_obd_data_org_time", "organization_id", "time"),
        Index("idx_obd_data_car_time", "car_id", "time"),
        Index("idx_obd_data_dtc", "dtc_codes", postgresql_using="gin"),
        Index("idx_obd_data_source_msg", "car_id", "source_message_id"),
    )
    time: Mapped[datetime] = mapped_column(DateTime(timezone=True), primary_key=True)
    car_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("cars.id", ondelete="CASCADE"), primary_key=True
    )
    organization_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("organizations.id", ondelete="CASCADE"),
        nullable=False,
    )

    @staticmethod
    def make_message_id(car_id: uuid.UUID, time: datetime) -> str:
        return f"{car_id}:{int(time.timestamp() * 1000)}"

    source_message_id: Mapped[Optional[str]] = mapped_column(String(128), nullable=True, index=False)

    # Engine metrics
    rpm: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    speed: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    throttle_position: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    engine_load: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    coolant_temp: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    intake_temp: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    # Fuel metrics
    fuel_level: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    fuel_rate: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    fuel_pressure: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    # Air/Emissions
    maf_rate: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    o2_voltage: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    # Location
    latitude: Mapped[Optional[float]] = mapped_column(Numeric(10, 6), nullable=True)
    longitude: Mapped[Optional[float]] = mapped_column(Numeric(10, 6), nullable=True)
    # Diagnostic
    dtc_codes: Mapped[Optional[List[str]]] = mapped_column(ARRAY(String), nullable=True)
    mil_status: Mapped[Optional[bool]] = mapped_column(Boolean, nullable=True)
    raw_data: Mapped[Any] = mapped_column(JSONB, default=dict)


class OBDDataHourly(Base):
    __tablename__ = "obd_data_hourly"
    __table_args__ = (
        UniqueConstraint("time", "car_id", name="uix_obd_data_hourly_time_car"),
        Index("idx_obd_hourly_org_time", "organization_id", "time"),
    )
    time: Mapped[datetime] = mapped_column(DateTime(timezone=True), primary_key=True)
    car_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("cars.id", ondelete="CASCADE"), primary_key=True
    )
    organization_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("organizations.id", ondelete="CASCADE"),
        nullable=False,
    )

    # Aggregated engine/fuel metrics
    avg_rpm: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    avg_speed: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    max_speed: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    avg_throttle: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    avg_engine_load: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    avg_coolant_temp: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    avg_fuel_rate: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    total_distance_km: Mapped[Optional[float]] = mapped_column(
        Numeric(10, 3), nullable=True
    )
    total_fuel_consumed_l: Mapped[Optional[float]] = mapped_column(
        Numeric(10, 3), nullable=True
    )
    dtc_count: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)


class Alert(Base):
    __tablename__ = "alerts"
    __table_args__ = (
        Index("idx_alerts_org_time", "organization_id", "created_at"),
        Index("idx_alerts_car_time", "car_id", "created_at"),
        Index("idx_alerts_unread", "car_id", "is_read", "is_resolved"),
    )
    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    organization_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("organizations.id", ondelete="CASCADE"),
        nullable=False,
    )
    car_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("cars.id", ondelete="CASCADE"), nullable=False
    )
    alert_type: Mapped[AlertType] = mapped_column(Enum(AlertType), nullable=False)
    severity: Mapped[AlertSeverity] = mapped_column(Enum(AlertSeverity), nullable=False)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    message: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    alert_metadata: Mapped[Any] = mapped_column("metadata", JSONB, default=dict)
    is_read: Mapped[bool] = mapped_column(Boolean, default=False)
    is_resolved: Mapped[bool] = mapped_column(Boolean, default=False)
    resolved_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    resolved_by: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id"), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )


class Message(Base):
    __tablename__ = "messages"
    __table_args__ = (
        Index("idx_messages_org_time", "organization_id", "created_at"),
        Index("idx_messages_car_time", "car_id", "created_at"),
        Index("idx_messages_type", "organization_id", "message_type"),
        CheckConstraint(
            "(scope = 'car' AND car_id IS NOT NULL) OR (scope = 'organization' AND car_id IS NULL)",
            name="check_car_scope_car_id",
        ),
    )
    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    organization_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("organizations.id", ondelete="CASCADE"),
        nullable=False,
    )
    scope: Mapped[MessageScope] = mapped_column(Enum(MessageScope), nullable=False)
    car_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True), ForeignKey("cars.id", ondelete="SET NULL"), nullable=True
    )
    message_type: Mapped[MessageType] = mapped_column(Enum(MessageType), nullable=False)
    sender_type: Mapped[SenderType] = mapped_column(Enum(SenderType), nullable=False)
    sender_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id"), nullable=True
    )
    content: Mapped[str] = mapped_column(Text, nullable=False)
    message_metadata: Mapped[Any] = mapped_column("metadata", JSONB, default=dict)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )


class AISession(Base):
    __tablename__ = "ai_sessions"
    __table_args__ = (
        Index("idx_ai_sessions_org_time", "organization_id", "created_at"),
        Index("idx_ai_sessions_car_time", "car_id", "created_at"),
    )
    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    organization_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("organizations.id", ondelete="CASCADE"),
        nullable=False,
    )
    car_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True), ForeignKey("cars.id", ondelete="CASCADE"), nullable=True
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    session_type: Mapped[AISessionType] = mapped_column(
        Enum(AISessionType), nullable=False
    )
    prompt: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    response: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    model_used: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    tokens_used: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    processing_time_ms: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    ai_metadata: Mapped[Any] = mapped_column("metadata", JSONB, default=dict)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )


# ============================================
# NEW MODELS FOR ADDITIONAL FEATURES
# ============================================


class Geofence(Base):
    """Virtual geographic zones for fleet monitoring."""

    __tablename__ = "geofences"
    __table_args__ = (Index("idx_geofences_org", "organization_id"),)
    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    organization_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("organizations.id", ondelete="CASCADE"),
        nullable=False,
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    geofence_type: Mapped[GeofenceType] = mapped_column(
        Enum(GeofenceType), nullable=False
    )

    # GeoJSON polygon or point + radius
    geometry: Mapped[Any] = mapped_column(
        JSONB, nullable=False
    )  # {"type": "Point", "coordinates": [lng, lat], "radius": 500}

    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    notify_on_entry: Mapped[bool] = mapped_column(Boolean, default=True)
    notify_on_exit: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )


class GeofenceEvent(Base):
    """Events when vehicles enter/exit geofences."""

    __tablename__ = "geofence_events"
    __table_args__ = (Index("idx_geofence_events_car_time", "car_id", "event_time"),)
    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    organization_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("organizations.id", ondelete="CASCADE"),
        nullable=False,
    )
    geofence_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("geofences.id", ondelete="CASCADE"),
        nullable=False,
    )
    car_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("cars.id", ondelete="CASCADE"), nullable=False
    )
    event_type: Mapped[str] = mapped_column(
        String(20), nullable=False
    )  # "enter" or "exit"
    event_time: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )
    location: Mapped[Optional[dict]] = mapped_column(JSONB, nullable=True)

    geofence: Mapped["Geofence"] = relationship("Geofence", lazy="joined")
    car: Mapped["Car"] = relationship("Car", lazy="joined")


class MaintenanceSchedule(Base):
    """Scheduled maintenance records."""

    __tablename__ = "maintenance_schedules"
    __table_args__ = (
        Index("idx_maintenance_car", "car_id"),
        Index("idx_maintenance_status", "status"),
    )
    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    organization_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("organizations.id", ondelete="CASCADE"),
        nullable=False,
    )
    car_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("cars.id", ondelete="CASCADE"), nullable=False
    )
    maintenance_type: Mapped[MaintenanceType] = mapped_column(
        Enum(MaintenanceType), nullable=False
    )
    status: Mapped[MaintenanceStatus] = mapped_column(
        Enum(MaintenanceStatus), default=MaintenanceStatus.scheduled
    )

    scheduled_date: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )
    completed_date: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    estimated_cost: Mapped[Optional[float]] = mapped_column(
        Numeric(10, 2), nullable=True
    )
    actual_cost: Mapped[Optional[float]] = mapped_column(Numeric(10, 2), nullable=True)

    notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )

    car: Mapped["Car"] = relationship("Car", lazy="joined")


class MaintenancePrediction(Base):
    """ML-based maintenance predictions."""

    __tablename__ = "maintenance_predictions"
    __table_args__ = (Index("idx_predictions_car", "car_id"),)
    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    organization_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("organizations.id", ondelete="CASCADE"),
        nullable=False,
    )
    car_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("cars.id", ondelete="CASCADE"), nullable=False
    )

    maintenance_type: Mapped[MaintenanceType] = mapped_column(
        Enum(MaintenanceType), nullable=False
    )
    predicted_days_until_failure: Mapped[int] = mapped_column(Integer, nullable=False)
    confidence_score: Mapped[float] = mapped_column(Float, nullable=False)  # 0-1

    reasoning: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )

    car: Mapped["Car"] = relationship("Car", lazy="joined")


class DriverScore(Base):
    """Driver behavior scores."""

    __tablename__ = "driver_scores"
    __table_args__ = (
        UniqueConstraint("user_id", "period_start", name="uix_driver_score_period"),
        Index("idx_driver_scores_user", "user_id"),
    )
    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    organization_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("organizations.id", ondelete="CASCADE"),
        nullable=False,
    )

    period_start: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )
    period_end: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )

    # Scores (0-100)
    overall_score: Mapped[float] = mapped_column(Float, nullable=False)
    safety_score: Mapped[float] = mapped_column(Float, nullable=False)
    efficiency_score: Mapped[float] = mapped_column(Float, nullable=False)

    # Metrics
    total_trips: Mapped[int] = mapped_column(Integer, default=0)
    total_distance_km: Mapped[float] = mapped_column(Numeric(10, 2), default=0)
    harsh_braking_count: Mapped[int] = mapped_column(Integer, default=0)
    harsh_acceleration_count: Mapped[int] = mapped_column(Integer, default=0)
    speeding_violations: Mapped[int] = mapped_column(Integer, default=0)
    idle_time_minutes: Mapped[int] = mapped_column(Integer, default=0)
    fuel_consumed_l: Mapped[float] = mapped_column(Numeric(10, 2), default=0)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )

    user: Mapped["User"] = relationship("User", lazy="joined")


class FuelAnomaly(Base):
    """Fuel theft/unusual consumption anomalies."""

    __tablename__ = "fuel_anomalies"
    __table_args__ = (Index("idx_fuel_anomalies_car", "car_id"),)
    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    organization_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("organizations.id", ondelete="CASCADE"),
        nullable=False,
    )
    car_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("cars.id", ondelete="CASCADE"), nullable=False
    )

    anomaly_type: Mapped[AnomalyType] = mapped_column(Enum(AnomalyType), nullable=False)
    severity: Mapped[AlertSeverity] = mapped_column(Enum(AlertSeverity), nullable=False)

    detected_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )

    # Details
    expected_fuel_l: Mapped[Optional[float]] = mapped_column(
        Numeric(10, 2), nullable=True
    )
    actual_fuel_l: Mapped[Optional[float]] = mapped_column(
        Numeric(10, 2), nullable=True
    )
    anomaly_value_l: Mapped[Optional[float]] = mapped_column(
        Numeric(10, 2), nullable=True
    )

    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    is_investigated: Mapped[bool] = mapped_column(Boolean, default=False)
    is_confirmed: Mapped[bool] = mapped_column(Boolean, default=False)
    notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    car: Mapped["Car"] = relationship("Car", lazy="joined")


class RefreshToken(Base):
    __tablename__ = "refresh_tokens"
    __table_args__ = (
        Index("idx_refresh_tokens_family", "family_id"),
        Index("idx_refresh_tokens_user", "user_id"),
    )
    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    token_hash: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    family_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    is_revoked: Mapped[bool] = mapped_column(Boolean, default=False)
    expires_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )

    user: Mapped["User"] = relationship("User", lazy="joined")


class DeviceAPIKey(Base):
    __tablename__ = "device_api_keys"
    __table_args__ = (
        Index("idx_device_api_keys_car", "car_id"),
        Index("idx_device_api_keys_org", "organization_id"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    organization_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("organizations.id", ondelete="CASCADE"),
        nullable=False,
    )
    car_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("cars.id", ondelete="CASCADE"), nullable=False
    )
    key_hash: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    last_used_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )

    car: Mapped["Car"] = relationship("Car", lazy="joined")
    organization: Mapped["Organization"] = relationship("Organization", lazy="joined")


class WebhookConfiguration(Base):
    __tablename__ = "webhook_configurations"
    __table_args__ = (Index("idx_webhook_org", "organization_id"),)

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    organization_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("organizations.id", ondelete="CASCADE"),
        nullable=False,
    )
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    url: Mapped[str] = mapped_column(String(500), nullable=False)
    secret: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    event_types: Mapped[str] = mapped_column(JSON, nullable=False, default=list)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    failure_count: Mapped[int] = mapped_column(Integer, default=0)
    last_failure_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )

    organization: Mapped["Organization"] = relationship("Organization", lazy="joined")
