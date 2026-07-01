"""Telemetry service for OBD data ingestion and retrieval."""
import hashlib
import json
import logging
from datetime import datetime, timezone
from typing import Optional, List, Tuple, Any
import uuid

from sqlalchemy import select, func, and_, or_, text, insert
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession

from domain.models import OBDData, Car, OBDDataHourly
from api.v1.schemas.telemetry import (
    TelemetryIngestRequest,
    TelemetryIngestResponse,
    TelemetryHistoryResponse,
    TelemetryPoint,
    TelemetryLatestResponse,
)

logger = logging.getLogger(__name__)


def _compute_idempotency_key(
    car_id: uuid.UUID,
    time: datetime,
    rpm: Optional[int],
    speed: Optional[int],
    throttle: Optional[float],
    fuel_level: Optional[float],
    latitude: Optional[float],
    longitude: Optional[float],
    raw_data: Optional[dict] = None,
) -> str:
    """Compute a stable idempotency key for deduplication."""
    payload = {
        "car_id": str(car_id),
        "time": time.isoformat(),
        "rpm": rpm,
        "speed": speed,
        "throttle": throttle,
        "fuel_level": fuel_level,
        "lat": latitude,
        "lon": longitude,
    }
    raw_str = json.dumps(payload, sort_keys=True, default=str)
    return hashlib.sha256(raw_str.encode()).hexdigest()


class TelemetryService:
    """Service for handling telemetry data operations."""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def ingest_telemetry(
        self,
        data: TelemetryIngestRequest,
        organization_id: uuid.UUID,
    ) -> OBDData:
        result = await self.db.execute(
            select(Car).filter(
                Car.id == data.car_id,
                Car.organization_id == organization_id,
                Car.is_active == True,
            )
        )
        car = result.scalars().first()
        if not car:
            raise ValueError(f"Car {data.car_id} not found or not accessible")

        idempotency_key = _compute_idempotency_key(
            car_id=data.car_id,
            time=data.time,
            rpm=data.rpm,
            speed=data.speed,
            throttle=data.throttle_position,
            fuel_level=data.fuel_level,
            latitude=data.latitude,
            longitude=data.longitude,
            raw_data=data.raw_data,
        )

        # Try insert with ON CONFLICT DO NOTHING for idempotency_key
        stmt = insert(OBDData).values(
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
            raw_data=data.raw_data or {},
            idempotency_key=idempotency_key,
        )
        stmt = stmt.on_conflict_do_nothing(index_elements=["idempotency_key"])
        await self.db.execute(stmt)
        await self.db.commit()

        # Fetch the record we just inserted (or the existing one if conflict)
        record = (
            await self.db.execute(
                select(OBDData).filter(OBDData.idempotency_key == idempotency_key)
            )
        ).scalars().first()
        if record is None:
            raise RuntimeError("Failed to retrieve inserted telemetry record")

        logger.info(f"Ingested telemetry for car {data.car_id} at {record.time}")
        return record

    async def ingest_telemetry_batch(
        self,
        items: List[TelemetryIngestRequest],
        organization_id: uuid.UUID,
    ) -> Tuple[int, int]:
        if not items:
            return 0, 0

        values = []
        for item in items:
            idempotency_key = _compute_idempotency_key(
                car_id=item.car_id,
                time=item.time,
                rpm=item.rpm,
                speed=item.speed,
                throttle=item.throttle_position,
                fuel_level=item.fuel_level,
                latitude=item.latitude,
                longitude=item.longitude,
                raw_data=item.raw_data,
            )
            values.append(
                {
                    "time": item.time,
                    "car_id": item.car_id,
                    "organization_id": organization_id,
                    "rpm": item.rpm,
                    "speed": item.speed,
                    "throttle_position": item.throttle_position,
                    "engine_load": item.engine_load,
                    "coolant_temp": item.coolant_temp,
                    "intake_temp": item.intake_temp,
                    "fuel_level": item.fuel_level,
                    "fuel_rate": item.fuel_rate,
                    "fuel_pressure": item.fuel_pressure,
                    "maf_rate": item.maf_rate,
                    "o2_voltage": item.o2_voltage,
                    "latitude": item.latitude,
                    "longitude": item.longitude,
                    "dtc_codes": item.dtc_codes,
                    "mil_status": item.mil_status,
                    "raw_data": item.raw_data or {},
                    "idempotency_key": idempotency_key,
                }
            )

        stmt = pg_insert(OBDData).values(values)
        stmt = stmt.on_conflict_do_nothing(index_elements=["idempotency_key"])
        await self.db.execute(stmt)
        await self.db.commit()
        return len(values), 0

    async def ingest_mqtt_reading(self, car_id: uuid.UUID, organization_id: uuid.UUID, reading: dict) -> bool:
        source_message_id = reading.get("source_message_id")
        if not source_message_id:
            logger.debug("MQTT reading missing source_message_id, cannot deduplicate for car %s", car_id)
            return False

        stmt = pg_insert(OBDData).values(
            car_id=car_id,
            organization_id=organization_id,
            source_message_id=source_message_id,
            time=datetime.fromisoformat(reading["time"]) if reading.get("time") else datetime.now(timezone.utc),
            rpm=reading.get("rpm"),
            speed=reading.get("speed"),
            throttle_position=reading.get("throttle_position"),
            engine_load=reading.get("engine_load"),
            coolant_temp=reading.get("coolant_temp"),
            intake_temp=reading.get("intake_temp"),
            fuel_level=reading.get("fuel_level"),
            fuel_rate=reading.get("fuel_rate"),
            fuel_pressure=reading.get("fuel_pressure"),
            maf_rate=reading.get("maf_rate"),
            o2_voltage=reading.get("o2_voltage"),
            latitude=reading.get("latitude"),
            longitude=reading.get("longitude"),
            dtc_codes=reading.get("dtc_codes"),
            mil_status=reading.get("mil_status"),
            raw_data=reading.get("raw_data", {}),
        )
        stmt = stmt.on_conflict_do_nothing(constraint="uix_obd_data_source_msg")
        await self.db.execute(stmt)
        await self.db.commit()
        return True

    async def get_history(
        self,
        car_id: uuid.UUID,
        organization_id: uuid.UUID,
        start: datetime,
        end: datetime,
        metrics: Optional[List[str]] = None,
        limit: int = 1000,
        offset: int = 0,
        aggregate: Optional[str] = None,
    ) -> TelemetryHistoryResponse:
        await self._verify_car_access(car_id, organization_id)

        if aggregate == "hourly":
            return await self._get_hourly_history(car_id, organization_id, start, end, metrics, limit, offset)
        if aggregate == "daily":
            return await self._get_daily_history(car_id, organization_id, start, end, metrics, limit, offset)
        return await self._get_raw_history(car_id, organization_id, start, end, metrics, limit, offset)

    async def _get_raw_history(self, car_id, organization_id, start, end, metrics, limit, offset):
        count_query = (
            select(func.count())
            .select_from(OBDData)
            .filter(
                and_(
                    OBDData.car_id == car_id,
                    OBDData.organization_id == organization_id,
                    OBDData.time >= start,
                    OBDData.time <= end,
                )
            )
        )
        total = await self.db.scalar(count_query) or 0
        query = (
            select(OBDData)
            .filter(
                and_(
                    OBDData.car_id == car_id,
                    OBDData.organization_id == organization_id,
                    OBDData.time >= start,
                    OBDData.time <= end,
                )
            )
            .order_by(OBDData.time.desc())
            .limit(limit)
            .offset(offset)
        )
        records = (await self.db.execute(query)).scalars().all()
        data = [self._record_to_point(r, metrics) for r in records]
        return TelemetryHistoryResponse(
            car_id=car_id,
            start=start,
            end=end,
            aggregate=None,
            data=data,
            total=total,
            limit=limit,
            offset=offset,
        )

    async def _get_hourly_history(self, car_id, organization_id, start, end, metrics, limit, offset):
        from domain.models import OBDDataHourly
        count_query = (
            select(func.count())
            .select_from(OBDDataHourly)
            .filter(
                and_(
                    OBDDataHourly.car_id == car_id,
                    OBDDataHourly.organization_id == organization_id,
                    OBDDataHourly.time >= start,
                    OBDDataHourly.time <= end,
                )
            )
        )
        total = await self.db.scalar(count_query) or 0
        query = (
            select(OBDDataHourly)
            .filter(
                and_(
                    OBDDataHourly.car_id == car_id,
                    OBDDataHourly.organization_id == organization_id,
                    OBDDataHourly.time >= start,
                    OBDDataHourly.time <= end,
                )
            )
            .order_by(OBDDataHourly.time.desc())
            .limit(limit)
            .offset(offset)
        )
        records = (await self.db.execute(query)).scalars().all()
        data = [
            TelemetryPoint(
                time=r.time,
                speed=int(r.avg_speed) if r.avg_speed else None,
                rpm=int(r.avg_rpm) if r.avg_rpm else None,
                throttle_position=r.avg_throttle,
                engine_load=r.avg_engine_load,
                coolant_temp=int(r.avg_coolant_temp) if r.avg_coolant_temp else None,
                fuel_rate=r.avg_fuel_rate,
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
            offset=offset,
        )

    async def _get_daily_history(self, car_id, organization_id, start, end, metrics, limit, offset):
        try:
            from sqlalchemy import text

            query = text("""
                SELECT time_bucket('1 day', time) as bucket,
                       car_id, organization_id,
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
                    AND time >= :start AND time <= :end
                GROUP BY bucket, car_id, organization_id
                ORDER BY bucket DESC
                LIMIT :limit OFFSET :offset
            """)
            result = await self.db.execute(
                query,
                {"car_id": car_id, "org_id": organization_id, "start": start, "end": end, "limit": limit, "offset": offset},
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
                    fuel_rate=row.avg_fuel_rate,
                )
                for row in rows
            ]
            count_query = text("""
                SELECT COUNT(DISTINCT time_bucket('1 day', time))
                FROM obd_data_hourly
                WHERE car_id = :car_id
                    AND organization_id = :org_id
                    AND time >= :start AND time <= :end
            """)
            total = (
                await self.db.scalar(
                    count_query, {"car_id": car_id, "org_id": organization_id, "start": start, "end": end}
                )
                or 0
            )
            return TelemetryHistoryResponse(
                car_id=car_id,
                start=start,
                end=end,
                aggregate="daily",
                data=data,
                total=total,
                limit=limit,
                offset=offset,
            )
        except Exception as e:
            logger.error(f"Daily aggregation error: {e}")
            return await self._get_hourly_history(car_id, organization_id, start, end, metrics, limit, offset)

    async def get_latest(self, car_id: uuid.UUID, organization_id: uuid.UUID) -> Optional[TelemetryLatestResponse]:
        await self._verify_car_access(car_id, organization_id)
        record = (
            await self.db.execute(
                select(OBDData)
                .filter(
                    OBDData.car_id == car_id,
                    OBDData.organization_id == organization_id,
                )
                .order_by(OBDData.time.desc())
                .limit(1)
            )
        ).scalars().first()
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
            mil_status=record.mil_status,
        )

    async def _verify_car_access(self, car_id: uuid.UUID, organization_id: uuid.UUID) -> None:
        result = await self.db.execute(
            select(Car).filter(
                Car.id == car_id,
                Car.organization_id == organization_id,
                Car.is_active == True,
            )
        )
        if not result.scalars().first():
            raise ValueError(f"Car {car_id} not found or not accessible")

    def _record_to_point(self, record: OBDData, metrics: Optional[List[str]] = None) -> TelemetryPoint:
        return TelemetryPoint(
            time=record.time,
            rpm=record.rpm if not metrics or "rpm" in metrics else None,
            speed=record.speed if not metrics or "speed" in metrics else None,
            throttle_position=record.throttle_position if not metrics or "throttle" in metrics else None,
            engine_load=record.engine_load if not metrics or "engine_load" in metrics else None,
            coolant_temp=record.coolant_temp if not metrics or "coolant_temp" in metrics else None,
            intake_temp=record.intake_temp if not metrics or "intake_temp" in metrics else None,
            fuel_level=record.fuel_level if not metrics or "fuel_level" in metrics else None,
            fuel_rate=record.fuel_rate if not metrics or "fuel_rate" in metrics else None,
            fuel_pressure=record.fuel_pressure if not metrics or "fuel_pressure" in metrics else None,
            maf_rate=record.maf_rate if not metrics or "maf_rate" in metrics else None,
            o2_voltage=record.o2_voltage if not metrics or "o2" in metrics else None,
            latitude=record.latitude if not metrics or "location" in metrics else None,
            longitude=record.longitude if not metrics or "location" in metrics else None,
            dtc_codes=record.dtc_codes if not metrics or "dtc_codes" in metrics else None,
            mil_status=record.mil_status if not metrics or "mil_status" in metrics else None,
        )