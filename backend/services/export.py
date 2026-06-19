"""Fleet report export service for CSV and PDF generation."""

import io
import csv
import logging
from datetime import datetime, timedelta, timezone
from typing import Optional, List, Dict, Any
import uuid

from sqlalchemy import select, func, and_
from sqlalchemy.ext.asyncio import AsyncSession

from domain.models import (
    Car,
    OBDData,
    OBDDataHourly,
    DriverScore,
    User,
    Alert,
    MaintenanceSchedule,
    FuelAnomaly,
    GeofenceEvent,
)

logger = logging.getLogger(__name__)


class ExportService:
    """Service for generating fleet reports in various formats."""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def export_fleet_summary_csv(
        self, organization_id: uuid.UUID, start_date: datetime, end_date: datetime
    ) -> bytes:
        """Export fleet summary as CSV."""
        query = select(
            Car.id, Car.license_plate, Car.make, Car.model, Car.year, Car.is_active
        ).filter(and_(Car.organization_id == organization_id, Car.is_active == True))

        result = await self.db.execute(query)
        cars = result.fetchall()

        output = io.StringIO()
        writer = csv.writer(output)

        writer.writerow(
            [
                "License Plate",
                "Make",
                "Model",
                "Year",
                "Total Distance (km)",
                "Total Fuel (L)",
                "Avg Speed (km/h)",
                "Max Speed (km/h)",
                "Active Days",
                "Alerts",
            ]
        )

        for car in cars:
            car_id = car[0]

            stats_query = select(
                func.sum(OBDDataHourly.total_distance_km).label("distance"),
                func.sum(OBDDataHourly.total_fuel_consumed_l).label("fuel"),
                func.avg(OBDDataHourly.avg_speed).label("avg_speed"),
                func.max(OBDDataHourly.max_speed).label("max_speed"),
                func.count(func.distinct(func.date(OBDDataHourly.time))).label(
                    "active_days"
                ),
            ).filter(
                and_(
                    OBDDataHourly.car_id == car_id,
                    OBDDataHourly.time >= start_date,
                    OBDDataHourly.time <= end_date,
                )
            )

            stats_result = await self.db.execute(stats_query)
            stats = stats_result.fetchone()

            alerts_query = select(func.count(Alert.id)).filter(
                and_(
                    Alert.car_id == car_id,
                    Alert.organization_id == organization_id,
                    Alert.created_at >= start_date,
                    Alert.created_at <= end_date,
                )
            )
            alerts_result = await self.db.execute(alerts_query)
            alert_count = alerts_result.scalar() or 0

            writer.writerow(
                [
                    car.license_plate,
                    car.make,
                    car.model,
                    car.year,
                    round(float(stats.distance or 0), 1),
                    round(float(stats.fuel or 0), 1),
                    int(stats.avg_speed or 0),
                    int(stats.max_speed or 0),
                    stats.active_days or 0,
                    alert_count,
                ]
            )

        output.seek(0)
        return output.getvalue().encode("utf-8")

    async def export_telemetry_csv(
        self,
        car_id: uuid.UUID,
        start_date: datetime,
        end_date: datetime,
        limit: int = 10000,
    ) -> bytes:
        """Export telemetry data for a car as CSV."""
        query = (
            select(OBDData)
            .filter(
                and_(
                    OBDData.car_id == car_id,
                    OBDData.time >= start_date,
                    OBDData.time <= end_date,
                )
            )
            .order_by(OBDData.time)
            .limit(limit)
        )

        result = await self.db.execute(query)
        records = result.scalars().all()

        output = io.StringIO()
        writer = csv.writer(output)

        writer.writerow(
            [
                "Timestamp",
                "Speed (km/h)",
                "RPM",
                "Engine Load (%)",
                "Coolant Temp (°C)",
                "Throttle (%)",
                "Fuel Level (%)",
                "Latitude",
                "Longitude",
                "DTC Codes",
            ]
        )

        for record in records:
            writer.writerow(
                [
                    record.time.isoformat(),
                    record.speed,
                    record.rpm,
                    record.engine_load,
                    record.coolant_temp,
                    record.throttle_position,
                    record.fuel_level,
                    record.latitude,
                    record.longitude,
                    ",".join(record.dtc_codes or []),
                ]
            )

        output.seek(0)
        return output.getvalue().encode("utf-8")

    async def export_driver_scores_csv(
        self, organization_id: uuid.UUID, start_date: datetime, end_date: datetime
    ) -> bytes:
        """Export driver scores as CSV."""
        query = (
            select(DriverScore, User)
            .join(User, DriverScore.user_id == User.id)
            .filter(
                and_(
                    DriverScore.organization_id == organization_id,
                    DriverScore.period_start >= start_date,
                    DriverScore.period_end <= end_date,
                )
            )
            .order_by(DriverScore.overall_score.desc())
        )

        result = await self.db.execute(query)
        records = result.fetchall()

        output = io.StringIO()
        writer = csv.writer(output)

        writer.writerow(
            [
                "Driver Name",
                "Email",
                "Overall Score",
                "Safety Score",
                "Efficiency Score",
                "Total Distance (km)",
                "Harsh Braking",
                "Harsh Acceleration",
                "Speeding Violations",
                "Fuel Consumed (L)",
                "Period",
            ]
        )

        for score, user in records:
            writer.writerow(
                [
                    user.full_name,
                    user.email,
                    round(score.overall_score, 1),
                    round(score.safety_score, 1),
                    round(score.efficiency_score, 1),
                    round(float(score.total_distance_km or 0), 1),
                    score.harsh_braking_count,
                    score.harsh_acceleration_count,
                    score.speeding_violations,
                    round(float(score.fuel_consumed_l or 0), 1),
                    f"{score.period_start.date()} to {score.period_end.date()}",
                ]
            )

        output.seek(0)
        return output.getvalue().encode("utf-8")

    async def export_alerts_csv(
        self,
        organization_id: uuid.UUID,
        start_date: datetime,
        end_date: datetime,
        is_resolved: Optional[bool] = None,
    ) -> bytes:
        """Export alerts as CSV."""
        filters = [
            Alert.organization_id == organization_id,
            Alert.created_at >= start_date,
            Alert.created_at <= end_date,
        ]

        if is_resolved is not None:
            filters.append(Alert.is_resolved == is_resolved)

        query = (
            select(Alert, Car)
            .join(Car, Alert.car_id == Car.id)
            .filter(and_(*filters))
            .order_by(Alert.created_at.desc())
        )

        result = await self.db.execute(query)
        records = result.fetchall()

        output = io.StringIO()
        writer = csv.writer(output)

        writer.writerow(
            [
                "Timestamp",
                "License Plate",
                "Alert Type",
                "Severity",
                "Title",
                "Message",
                "Resolved",
                "Resolved At",
            ]
        )

        for alert, car in records:
            writer.writerow(
                [
                    alert.created_at.isoformat(),
                    car.license_plate,
                    alert.alert_type.value,
                    alert.severity.value,
                    alert.title,
                    alert.message,
                    alert.is_resolved,
                    alert.resolved_at.isoformat() if alert.resolved_at else "",
                ]
            )

        output.seek(0)
        return output.getvalue().encode("utf-8")

    async def export_maintenance_csv(
        self, organization_id: uuid.UUID, start_date: datetime, end_date: datetime
    ) -> bytes:
        """Export maintenance schedules as CSV."""
        query = (
            select(MaintenanceSchedule, Car)
            .join(Car, MaintenanceSchedule.car_id == Car.id)
            .filter(
                and_(
                    MaintenanceSchedule.organization_id == organization_id,
                    MaintenanceSchedule.scheduled_date >= start_date,
                    MaintenanceSchedule.scheduled_date <= end_date,
                )
            )
            .order_by(MaintenanceSchedule.scheduled_date)
        )

        result = await self.db.execute(query)
        records = result.fetchall()

        output = io.StringIO()
        writer = csv.writer(output)

        writer.writerow(
            [
                "Scheduled Date",
                "License Plate",
                "Type",
                "Status",
                "Description",
                "Estimated Cost",
                "Actual Cost",
                "Completed Date",
            ]
        )

        for schedule, car in records:
            writer.writerow(
                [
                    schedule.scheduled_date.isoformat(),
                    car.license_plate,
                    schedule.maintenance_type.value,
                    schedule.status.value,
                    schedule.description,
                    schedule.estimated_cost,
                    schedule.actual_cost,
                    schedule.completed_at.isoformat() if schedule.completed_at else "",
                ]
            )

        output.seek(0)
        return output.getvalue().encode("utf-8")
