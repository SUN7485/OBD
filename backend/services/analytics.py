"""Analytics service for fleet and car-level metrics."""
import logging
from datetime import datetime, timedelta, timezone
from typing import Optional, Dict, Any
import uuid

from sqlalchemy import select, func, and_
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.sql import text

from backend.domain.models import Car, OBDData, OBDDataHourly, Alert

logger = logging.getLogger(__name__)


class AnalyticsService:
    """Service for fleet and car analytics."""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_fleet_summary(
        self,
        organization_id: uuid.UUID
    ) -> Dict[str, Any]:
        """
        Get organization-wide fleet summary.
        
        Returns:
            Dictionary with fleet metrics:
            - total_cars: Total number of cars
            - active_cars: Cars with telemetry in last 1 hour
            - total_distance_km: Total distance today
            - total_fuel_consumed_l: Total fuel consumed today
            - alerts_by_severity: Count of alerts by severity
            - active_alerts: Count of unresolved alerts
        """
        now = datetime.now(timezone.utc)
        one_hour_ago = now - timedelta(hours=1)
        today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)

        # Total cars
        total_cars_result = await self.db.execute(
            select(func.count(Car.id)).filter(
                Car.organization_id == organization_id,
                Car.is_active == True
            )
        )
        total_cars = total_cars_result.scalar() or 0

        # Active cars (last seen < 1 hour)
        active_cars_result = await self.db.execute(
            select(func.count(func.distinct(OBDData.car_id))).filter(
                OBDData.organization_id == organization_id,
                OBDData.time >= one_hour_ago
            )
        )
        active_cars = active_cars_result.scalar() or 0

        # Today's distance and fuel from hourly aggregates
        fleet_summary_result = await self.db.execute(
            select(
                func.coalesce(func.sum(OBDDataHourly.total_distance_km), 0),
                func.coalesce(func.sum(OBDDataHourly.total_fuel_consumed_l), 0)
            ).filter(
                OBDDataHourly.organization_id == organization_id,
                OBDDataHourly.time >= today_start
            )
        )
        distance_row = fleet_summary_result.fetchone()
        total_distance_km = float(distance_row[0]) if distance_row else 0
        total_fuel_consumed_l = float(distance_row[1]) if distance_row else 0

        # Alerts by severity
        alerts_by_severity = {}
        for severity in ["info", "warning", "critical"]:
            count_result = await self.db.execute(
                select(func.count(Alert.id)).filter(
                    Alert.organization_id == organization_id,
                    Alert.severity == severity,
                    Alert.is_resolved == False
                )
            )
            alerts_by_severity[severity] = count_result.scalar() or 0

        active_alerts = sum(alerts_by_severity.values())

        return {
            "total_cars": total_cars,
            "active_cars": active_cars,
            "inactive_cars": total_cars - active_cars,
            "total_distance_km": round(total_distance_km, 2),
            "total_fuel_consumed_l": round(total_fuel_consumed_l, 2),
            "alerts_by_severity": alerts_by_severity,
            "active_alerts": active_alerts,
            "timestamp": now.isoformat()
        }

    async def get_car_summary(
        self,
        car_id: uuid.UUID,
        organization_id: uuid.UUID,
        hours: int = 24
    ) -> Dict[str, Any]:
        """
        Get individual car analytics.
        
        Args:
            car_id: The car ID
            organization_id: The organization ID
            hours: Number of hours to look back (default 24)
            
        Returns:
            Dictionary with car metrics:
            - car_info: Basic car information
            - recent_metrics: Latest telemetry values
            - averages: Average values over period
            - max_values: Maximum values over period
            - dtc_history: Recent DTC codes
        """
        # Verify access
        await self._verify_car_access(car_id, organization_id)

        now = datetime.now(timezone.utc)
        start_time = now - timedelta(hours=hours)

        # Get car info
        car_result = await self.db.execute(
            select(Car).filter(Car.id == car_id)
        )
        car = car_result.scalars().first()

        # Get latest telemetry
        latest_result = await self.db.execute(
            select(OBDData).filter(
                OBDData.car_id == car_id,
                OBDData.organization_id == organization_id
            ).order_by(OBDData.time.desc()).limit(1)
        )
        latest = latest_result.scalars().first()

        # Get averages from hourly data
        hourly_result = await self.db.execute(
            select(
                func.avg(OBDDataHourly.avg_rpm),
                func.avg(OBDDataHourly.avg_speed),
                func.avg(OBDDataHourly.avg_throttle),
                func.avg(OBDDataHourly.avg_engine_load),
                func.avg(OBDDataHourly.avg_coolant_temp),
                func.avg(OBDDataHourly.avg_fuel_rate),
                func.sum(OBDDataHourly.total_distance_km),
                func.sum(OBDDataHourly.total_fuel_consumed_l)
            ).filter(
                OBDDataHourly.car_id == car_id,
                OBDDataHourly.organization_id == organization_id,
                OBDDataHourly.time >= start_time
            )
        )
        avg_row = hourly_result.fetchone()

        # Get max values
        max_result = await self.db.execute(
            select(
                func.max(OBDDataHourly.max_speed),
                func.max(OBDDataHourly.avg_rpm),
                func.max(OBDDataHourly.avg_coolant_temp),
                func.max(OBDDataHourly.avg_engine_load)
            ).filter(
                OBDDataHourly.car_id == car_id,
                OBDDataHourly.organization_id == organization_id,
                OBDDataHourly.time >= start_time
            )
        )
        max_row = max_result.fetchone()

        # Get DTC history
        dtc_result = await self.db.execute(
            select(OBDData.dtc_codes).filter(
                OBDData.car_id == car_id,
                OBDData.organization_id == organization_id,
                OBDData.dtc_codes.isnot(None),
                OBDData.time >= start_time
            ).order_by(OBDData.time.desc()).limit(50)
        )
        dtc_records = dtc_result.scalars().all()
        
        # Flatten DTC codes
        all_dtcs = []
        for dtc_list in dtc_records:
            if dtc_list:
                all_dtcs.extend(dtc_list)
        unique_dtcs = list(set(all_dtcs))[:10]  # Top 10 unique

        return {
            "car_info": {
                "id": str(car.id),
                "vin": car.vin,
                "license_plate": car.license_plate,
                "make": car.make,
                "model": car.model,
                "year": car.year
            },
            "recent_metrics": {
                "time": latest.time.isoformat() if latest else None,
                "rpm": latest.rpm if latest else None,
                "speed": latest.speed if latest else None,
                "coolant_temp": latest.coolant_temp if latest else None,
                "engine_load": latest.engine_load if latest else None,
                "fuel_level": latest.fuel_level if latest else None,
                "latitude": float(latest.latitude) if latest and latest.latitude else None,
                "longitude": float(latest.longitude) if latest and latest.longitude else None
            },
            "averages": {
                "rpm": round(float(avg_row[0]), 1) if avg_row and avg_row[0] else None,
                "speed": round(float(avg_row[1]), 1) if avg_row and avg_row[1] else None,
                "throttle": round(float(avg_row[2]), 1) if avg_row and avg_row[2] else None,
                "engine_load": round(float(avg_row[3]), 1) if avg_row and avg_row[3] else None,
                "coolant_temp": round(float(avg_row[4]), 1) if avg_row and avg_row[4] else None,
                "fuel_rate": round(float(avg_row[5]), 2) if avg_row and avg_row[5] else None,
                "distance_km": round(float(avg_row[6]), 2) if avg_row and avg_row[6] else 0,
                "fuel_consumed_l": round(float(avg_row[7]), 2) if avg_row and avg_row[7] else 0
            },
            "max_values": {
                "speed": int(max_row[0]) if max_row and max_row[0] else None,
                "rpm": int(max_row[1]) if max_row and max_row[1] else None,
                "coolant_temp": int(max_row[2]) if max_row and max_row[2] else None,
                "engine_load": round(float(max_row[3]), 1) if max_row and max_row[3] else None
            },
            "dtc_history": unique_dtcs,
            "period_hours": hours,
            "timestamp": now.isoformat()
        }

    async def get_driving_statistics(
        self,
        car_id: uuid.UUID,
        organization_id: uuid.UUID,
        days: int = 7
    ) -> Dict[str, Any]:
        """Get driving statistics over multiple days."""
        await self._verify_car_access(car_id, organization_id)

        now = datetime.now(timezone.utc)
        start_time = now - timedelta(days=days)

        # Daily aggregation
        query = text("""
            SELECT 
                DATE(time) as day,
                SUM(total_distance_km) as distance,
                SUM(total_fuel_consumed_l) as fuel,
                AVG(avg_speed) as avg_speed,
                MAX(max_speed) as max_speed,
                COUNT(*) as hours_active
            FROM obd_data_hourly
            WHERE car_id = :car_id 
                AND organization_id = :org_id
                AND time >= :start_time
            GROUP BY DATE(time)
            ORDER BY day DESC
        """)

        result = await self.db.execute(
            query,
            {
                "car_id": car_id,
                "org_id": organization_id,
                "start_time": start_time
            }
        )
        rows = result.fetchall()

        daily_stats = [
            {
                "date": str(row.day),
                "distance_km": round(float(row.distance), 2) if row.distance else 0,
                "fuel_consumed_l": round(float(row.fuel), 2) if row.fuel else 0,
                "avg_speed_kmh": round(float(row.avg_speed), 1) if row.avg_speed else 0,
                "max_speed_kmh": int(row.max_speed) if row.max_speed else 0,
                "hours_active": row.hours_active
            }
            for row in rows
        ]

        # Summary
        total_distance = sum(s["distance_km"] for s in daily_stats)
        total_fuel = sum(s["fuel_consumed_l"] for s in daily_stats)

        return {
            "car_id": str(car_id),
            "period_days": days,
            "daily_stats": daily_stats,
            "summary": {
                "total_distance_km": round(total_distance, 2),
                "total_fuel_consumed_l": round(total_fuel, 2),
                "avg_fuel_efficiency_l_per_100km": round(
                    (total_fuel / total_distance * 100) if total_distance > 0 else 0,
                    2
                ),
                "avg_daily_distance_km": round(total_distance / days, 2) if days > 0 else 0
            },
            "timestamp": now.isoformat()
        }

    async def _verify_car_access(
        self,
        car_id: uuid.UUID,
        organization_id: uuid.UUID
    ) -> None:
        """Verify user has access to the car."""
        result = await self.db.execute(
            select(Car).filter(
                Car.id == car_id,
                Car.organization_id == organization_id,
                Car.is_active == True
            )
        )
        car = result.scalars().first()

        if not car:
            raise ValueError(f"Car {car_id} not found or not accessible")
