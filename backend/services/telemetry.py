"""Telemetry service for OBD data ingestion and retrieval."""
import logging
from datetime import datetime, timezone
from typing import Optional, List, Tuple, Any
import uuid

from sqlalchemy import select, func, and_, or_
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.dialects.postgresql import insert

from backend.domain.models import OBDData, Car
from backend.api.v1.schemas.telemetry import (
    TelemetryIngestRequest,
    TelemetryHistoryResponse,
    TelemetryPoint,
    TelemetryLatestResponse
)

logger = logging.getLogger(__name__)


class TelemetryService:
    """Service for handling telemetry data operations."""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def ingest_telemetry(
        self,
        data: TelemetryIngestRequest,
        organization_id: uuid.UUID
    ) -> OBDData:
        """
        Ingest telemetry data into the database.
        
        Args:
            data: The telemetry data to ingest
            organization_id: The organization ID for multi-tenant isolation
            
        Returns:
            The created OBDData record
        """
        # Verify car belongs to organization
        result = await self.db.execute(
            select(Car).filter(
                Car.id == data.car_id,
                Car.organization_id == organization_id,
                Car.is_active == True
            )
        )
        car = result.scalars().first()
        
        if not car:
            raise ValueError(f"Car {data.car_id} not found or not accessible")

        # Create OBD data record
        obd_data = OBDData(
            time=data.time,
            car_id=data.car_id,
            organization_id=organization_id,
            rpm=data.rpm,
            speed=data.speed,
            throttle_position=data.throttle_position,
            engine_load=data.engine_load,
            coolant_temp=data.coolant_temp,
            intake_temp=data.intake_temp,
            fuel_level=data.fuel_level,
            fuel_rate=data.fuel_rate,
            fuel_pressure=data.fuel_pressure,
            maf_rate=data.maf_rate,
            o2_voltage=data.o2_voltage,
            latitude=data.latitude,
            longitude=data.longitude,
            dtc_codes=data.dtc_codes,
            mil_status=data.mil_status,
            raw_data=data.raw_data or {}
        )

        self.db.add(obd_data)
        await self.db.commit()
        await self.db.refresh(obd_data)

        logger.info(
            f"Ingested telemetry for car {data.car_id} at {data.time}"
        )

        return obd_data

    async def get_history(
        self,
        car_id: uuid.UUID,
        organization_id: uuid.UUID,
        start: datetime,
        end: datetime,
        metrics: Optional[List[str]] = None,
        limit: int = 1000,
        offset: int = 0,
        aggregate: Optional[str] = None
    ) -> TelemetryHistoryResponse:
        """
        Query historical telemetry data.
        
        Args:
            car_id: The car ID to query
            organization_id: The organization ID for isolation
            start: Start time
            end: End time
            metrics: Optional list of specific metrics to retrieve
            limit: Maximum records
            offset: Records to skip
            aggregate: Optional aggregation (hourly, daily)
            
        Returns:
            Telemetry history response
        """
        # Verify access
        await self._verify_car_access(car_id, organization_id)

        # Build query based on aggregation
        if aggregate == "hourly":
            return await self._get_hourly_history(
                car_id, organization_id, start, end, metrics, limit, offset
            )
        elif aggregate == "daily":
            return await self._get_daily_history(
                car_id, organization_id, start, end, metrics, limit, offset
            )
        else:
            return await self._get_raw_history(
                car_id, organization_id, start, end, metrics, limit, offset
            )

    async def _get_raw_history(
        self,
        car_id: uuid.UUID,
        organization_id: uuid.UUID,
        start: datetime,
        end: datetime,
        metrics: Optional[List[str]],
        limit: int,
        offset: int
    ) -> TelemetryHistoryResponse:
        """Get raw (non-aggregated) telemetry history."""
        # Get total count
        count_query = select(func.count()).select_from(OBDData).filter(
            and_(
                OBDData.car_id == car_id,
                OBDData.organization_id == organization_id,
                OBDData.time >= start,
                OBDData.time <= end
            )
        )
        total = await self.db.scalar(count_query) or 0

        # Get data
        query = select(OBDData).filter(
            and_(
                OBDData.car_id == car_id,
                OBDData.organization_id == organization_id,
                OBDData.time >= start,
                OBDData.time <= end
            )
        ).order_by(OBDData.time.desc()).limit(limit).offset(offset)

        result = await self.db.execute(query)
        records = result.scalars().all()

        data = [self._record_to_point(r, metrics) for r in records]

        return TelemetryHistoryResponse(
            car_id=car_id,
            start=start,
            end=end,
            aggregate=None,
            data=data,
            total=total,
            limit=limit,
            offset=offset
        )

    async def _get_hourly_history(
        self,
        car_id: uuid.UUID,
        organization_id: uuid.UUID,
        start: datetime,
        end: datetime,
        metrics: Optional[List[str]],
        limit: int,
        offset: int
    ) -> TelemetryHistoryResponse:
        """Get hourly aggregated telemetry."""
        from backend.domain.models import OBDDataHourly

        # Get total count
        count_query = select(func.count()).select_from(OBDDataHourly).filter(
            and_(
                OBDDataHourly.car_id == car_id,
                OBDDataHourly.organization_id == organization_id,
                OBDDataHourly.time >= start,
                OBDDataHourly.time <= end
            )
        )
        total = await self.db.scalar(count_query) or 0

        # Get hourly data
        query = select(OBDDataHourly).filter(
            and_(
                OBDDataHourly.car_id == car_id,
                OBDDataHourly.organization_id == organization_id,
                OBDDataHourly.time >= start,
                OBDDataHourly.time <= end
            )
        ).order_by(OBDDataHourly.time.desc()).limit(limit).offset(offset)

        result = await self.db.execute(query)
        records = result.scalars().all()

        data = [
            TelemetryPoint(
                time=r.time,
                speed=int(r.avg_speed) if r.avg_speed else None,
                rpm=int(r.avg_rpm) if r.avg_rpm else None,
                throttle_position=r.avg_throttle,
                engine_load=r.avg_engine_load,
                coolant_temp=int(r.avg_coolant_temp) if r.avg_coolant_temp else None,
                fuel_rate=r.avg_fuel_rate
            )
            for r in records
        ]

        return TelemetryHistoryResponse(
            car_id=car_id,
            start=start,
            end=end,
            aggregate="hourly",
            data=data,
            total=total,
            limit=limit,
            offset=offset
        )

    async def _get_daily_history(
        self,
        car_id: uuid.UUID,
        organization_id: uuid.UUID,
        start: datetime,
        end: datetime,
        metrics: Optional[List[str]],
        limit: int,
        offset: int
    ) -> TelemetryHistoryResponse:
        """Get daily aggregated telemetry."""
        # For daily, we aggregate hourly data or query raw with daily bucketing
        # Using time_bucket if TimescaleDB is available
        try:
            # Try using time_bucket for daily aggregation
            query = text("""
                SELECT 
                    time_bucket('1 day', time) as bucket,
                    car_id,
                    organization_id,
                    AVG(avg_rpm) as avg_rpm,
                    AVG(avg_speed) as avg_speed,
                    MAX(max_speed) as max_speed,
                    AVG(avg_throttle) as avg_throttle,
                    AVG(avg_engine_load) as avg_engine_load,
                    AVG(avg_coolant_temp) as avg_coolant_temp,
                    AVG(avg_fuel_rate) as avg_fuel_rate,
                    SUM(total_distance_km) as total_distance_km,
                    SUM(total_fuel_consumed_l) as total_fuel_consumed_l,
                    SUM(dtc_count) as dtc_count
                FROM obd_data_hourly
                WHERE car_id = :car_id 
                    AND organization_id = :org_id
                    AND time >= :start 
                    AND time <= :end
                GROUP BY bucket, car_id, organization_id
                ORDER BY bucket DESC
                LIMIT :limit OFFSET :offset
            """)
            
            from sqlalchemy import text
            result = await self.db.execute(
                query,
                {
                    "car_id": car_id,
                    "org_id": organization_id,
                    "start": start,
                    "end": end,
                    "limit": limit,
                    "offset": offset
                }
            )
            rows = result.fetchall()

            data = [
                TelemetryPoint(
                    time=row.bucket,
                    speed=int(row.avg_speed) if row.avg_speed else None,
                    rpm=int(row.avg_rpm) if row.avg_rpm else None,
                    throttle_position=row.avg_throttle,
                    engine_load=row.avg_engine_load,
                    coolant_temp=int(row.avg_coolant_temp) if row.avg_coolant_temp else None,
                    fuel_rate=row.avg_fuel_rate
                )
                for row in rows
            ]

            # Get count
            count_query = text("""
                SELECT COUNT(DISTINCT time_bucket('1 day', time))
                FROM obd_data_hourly
                WHERE car_id = :car_id 
                    AND organization_id = :org_id
                    AND time >= :start 
                    AND time <= :end
            """)
            total = await self.db.scalar(
                count_query,
                {"car_id": car_id, "org_id": organization_id, "start": start, "end": end}
            ) or 0

            return TelemetryHistoryResponse(
                car_id=car_id,
                start=start,
                end=end,
                aggregate="daily",
                data=data,
                total=total,
                limit=limit,
                offset=offset
            )
        except Exception as e:
            logger.error(f"Daily aggregation error: {e}")
            # Fallback to hourly
            return await self._get_hourly_history(
                car_id, organization_id, start, end, metrics, limit, offset
            )

    async def get_latest(
        self,
        car_id: uuid.UUID,
        organization_id: uuid.UUID
    ) -> Optional[TelemetryLatestResponse]:
        """Get the latest telemetry for a car."""
        await self._verify_car_access(car_id, organization_id)

        query = select(OBDData).filter(
            and_(
                OBDData.car_id == car_id,
                OBDData.organization_id == organization_id
            )
        ).order_by(OBDData.time.desc()).limit(1)

        result = await self.db.execute(query)
        record = result.scalars().first()

        if not record:
            return None

        return TelemetryLatestResponse(
            car_id=record.car_id,
            time=record.time,
            rpm=record.rpm,
            speed=record.speed,
            throttle_position=record.throttle_position,
            engine_load=record.engine_load,
            coolant_temp=record.coolant_temp,
            fuel_level=record.fuel_level,
            latitude=record.latitude,
            longitude=record.longitude,
            dtc_codes=record.dtc_codes,
            mil_status=record.mil_status
        )

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

    def _record_to_point(
        self,
        record: OBDData,
        metrics: Optional[List[str]] = None
    ) -> TelemetryPoint:
        """Convert OBDData record to TelemetryPoint."""
        return TelemetryPoint(
            time=record.time,
            rpm=record.rpm if not metrics or 'rpm' in metrics else None,
            speed=record.speed if not metrics or 'speed' in metrics else None,
            throttle_position=record.throttle_position if not metrics or 'throttle' in metrics else None,
            engine_load=record.engine_load if not metrics or 'engine_load' in metrics else None,
            coolant_temp=record.coolant_temp if not metrics or 'coolant_temp' in metrics else None,
            intake_temp=record.intake_temp if not metrics or 'intake_temp' in metrics else None,
            fuel_level=record.fuel_level if not metrics or 'fuel_level' in metrics else None,
            fuel_rate=record.fuel_rate if not metrics or 'fuel_rate' in metrics else None,
            fuel_pressure=record.fuel_pressure if not metrics or 'fuel_pressure' in metrics else None,
            maf_rate=record.maf_rate if not metrics or 'maf_rate' in metrics else None,
            o2_voltage=record.o2_voltage if not metrics or 'o2_voltage' in metrics else None,
            latitude=record.latitude if not metrics or 'location' in metrics else None,
            longitude=record.longitude if not metrics or 'location' in metrics else None,
            dtc_codes=record.dtc_codes if not metrics or 'dtc_codes' in metrics else None,
            mil_status=record.mil_status if not metrics or 'mil_status' in metrics else None
        )
