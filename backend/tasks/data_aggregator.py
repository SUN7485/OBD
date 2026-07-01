"""Data aggregation Celery task."""
import logging
from datetime import datetime, timedelta, timezone
from typing import List, Dict, Any, Optional, Tuple
import uuid
import math

from celery import shared_task

logger = logging.getLogger(__name__)


def _haversine_distance(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Calculate distance between two GPS points in kilometers using Haversine formula."""
    R = 6371.0  # Earth radius in km
    lat1_rad = math.radians(lat1)
    lon1_rad = math.radians(lon1)
    lat2_rad = math.radians(lat2)
    lon2_rad = math.radians(lon2)
    dlat = lat2_rad - lat1_rad
    dlon = lon2_rad - lon1_rad
    a = math.sin(dlat / 2)**2 + math.cos(lat1_rad) * math.cos(lat2_rad) * math.sin(dlon / 2)**2
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
    return R * c


def _compute_distance_from_obd_records(records: List[Tuple[datetime, Optional[float], Optional[float]]]) -> float:
    """
    Compute total distance from a list of OBD data points with timestamps and GPS coordinates.
    Falls back to speed-based estimation when GPS is missing.
    """
    total_km = 0.0
    for i in range(1, len(records)):
        t0, lat0, lon0 = records[i - 1]
        t1, lat1, lon1 = records[i]
        dt_hours = (t1 - t0).total_seconds() / 3600.0
        if dt_hours <= 0:
            continue
        if lat0 is not None and lon0 is not None and lat1 is not None and lon1 is not None:
            total_km += _haversine_distance(lat0, lon0, lat1, lon1)
        else:
            # Fallback: we don't have speed here directly; leave 0 if not provided
            # Caller should supply speed if they want fallback estimation
            pass
    return total_km


def _run_async(coro):
    """Run an async coroutine safely inside a synchronous Celery worker."""
    try:
        loop = asyncio_get_or_create_loop()
        return loop.run_until_complete(coro)
    except RuntimeError:
        import asyncio
        return asyncio.run(coro)


def asyncio_get_or_create_loop():
    """Get the current running event loop, or create a new one if none exists."""
    import asyncio
    try:
        return asyncio.get_running_loop()
    except RuntimeError:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        return loop


@shared_task(
    name="backend.tasks.data_aggregator.aggregate_hourly_data",
    bind=True,
    max_retries=3,
    default_retry_delay=300
)
def aggregate_hourly_data(self):
    """
    Aggregate telemetry data into hourly statistics.
    
    This task runs hourly and aggregates raw OBD data into
    hourly summaries stored in the obd_data_hourly table.
    """
    async def _aggregate_hourly():
        from db.session import AsyncSessionLocal
        from domain.models import OBDData, OBDDataHourly, Car
        from sqlalchemy import select, func, and_
        from sqlalchemy.dialects.postgresql import insert
        
        async with AsyncSessionLocal() as db:
            # Get the last completed hour's data to aggregate
            now = datetime.now(timezone.utc)
            hour_end = now.replace(minute=0, second=0, microsecond=0)
            hour_start = hour_end - timedelta(hours=1)
            
            # Aggregate query
            aggregate_query = select(
                func.date_trunc('hour', OBDData.time).label('hour'),
                OBDData.car_id,
                OBDData.organization_id,
                func.avg(OBDData.rpm).label('avg_rpm'),
                func.avg(OBDData.speed).label('avg_speed'),
                func.max(OBDData.speed).label('max_speed'),
                func.avg(OBDData.throttle_position).label('avg_throttle'),
                func.avg(OBDData.engine_load).label('avg_engine_load'),
                func.avg(OBDData.coolant_temp).label('avg_coolant_temp'),
                func.avg(OBDData.fuel_rate).label('avg_fuel_rate'),
                func.coalesce(func.sum(func.array_length(OBDData.dtc_codes, 1)), 0).label('dtc_count')
            ).filter(
                and_(
                    OBDData.time >= hour_start,
                    OBDData.time < hour_end
                )
            ).group_by(
                'hour',
                OBDData.car_id,
                OBDData.organization_id
            )
            
            result = await db.execute(aggregate_query)
            aggregates = result.fetchall()
            
            if not aggregates:
                logger.info("No data to aggregate for the last hour")
                return
            
            # Insert aggregated data
            inserted_count = 0
            for agg in aggregates:
                # Compute distance from raw GPS records during this hour for this car
                points_query = select(
                    OBDData.time,
                    OBDData.latitude,
                    OBDData.longitude,
                    OBDData.fuel_rate,
                ).filter(
                    and_(
                        OBDData.car_id == agg.car_id,
                        OBDData.time >= hour_start,
                        OBDData.time < hour_end,
                    )
                ).order_by(OBDData.time.asc())
                
                points_result = await db.execute(points_query)
                points = points_result.fetchall()
                
                distance_km = 0.0
                if len(points) >= 2:
                    lat_lon_pairs = [
                        (row.time, float(row.latitude) if row.latitude is not None else None, float(row.longitude) if row.longitude is not None else None)
                        for row in points
                    ]
                    distance_km = _compute_distance_from_obd_records(lat_lon_pairs)
                
                # Sum fuel consumed (fuel_rate is L/h, average it for the hour)
                avg_fuel_rate = float(agg.avg_fuel_rate) if agg.avg_fuel_rate else 0.0
                fuel_consumed = avg_fuel_rate  # L/h for 1 hour
                
                hourly_data = OBDDataHourly(
                    time=agg.hour,
                    car_id=agg.car_id,
                    organization_id=agg.organization_id,
                    avg_rpm=agg.avg_rpm,
                    avg_speed=agg.avg_speed,
                    max_speed=agg.max_speed,
                    avg_throttle=agg.avg_throttle,
                    avg_engine_load=agg.avg_engine_load,
                    avg_coolant_temp=agg.avg_coolant_temp,
                    avg_fuel_rate=agg.avg_fuel_rate,
                    total_distance_km=distance_km if distance_km > 0 else None,
                    total_fuel_consumed_l=fuel_consumed if fuel_consumed > 0 else None,
                    dtc_count=agg.dtc_count
                )
                db.add(hourly_data)
                inserted_count += 1
            
            await db.commit()
            logger.info(f"Aggregated {inserted_count} hourly records")
            
            return {"aggregated": inserted_count, "hour": hour_start.isoformat()}
    
    try:
        result = _run_async(_aggregate_hourly())
        return result
    except Exception as e:
        logger.error(f"Hourly data aggregation failed: {e}")
        raise self.retry(exc=e)


@shared_task(
    name="backend.tasks.data_aggregator.generate_daily_fleet_summary",
    bind=True
)
def generate_daily_fleet_summary(self):
    """
    Generate daily fleet summary for all organizations.
    
    This task runs daily and creates summary statistics
    for each organization's fleet.
    """
    async def _generate_summary():
        from db.session import AsyncSessionLocal
        from domain.models import Organization, OBDDataHourly, OBDData
        from sqlalchemy import select, func, and_
        
        async with AsyncSessionLocal() as db:
            # Get yesterday's date range
            today = datetime.now(timezone.utc).date()
            yesterday_start = datetime.combine(today - timedelta(days=1), datetime.min.time()).replace(tzinfo=timezone.utc)
            yesterday_end = datetime.combine(today, datetime.min.time()).replace(tzinfo=timezone.utc)
            
            # Get all active organizations
            orgs_result = await db.execute(
                select(Organization).filter(Organization.is_active == True)
            )
            organizations = orgs_result.scalars().all()
            
            summaries = []
            
            for org in organizations:
                # Get fleet summary for yesterday
                summary_query = select(
                    func.count(func.distinct(OBDDataHourly.car_id)).label('active_cars'),
                    func.sum(OBDDataHourly.total_distance_km).label('total_distance'),
                    func.sum(OBDDataHourly.total_fuel_consumed_l).label('total_fuel'),
                    func.avg(OBDDataHourly.avg_speed).label('avg_speed'),
                    func.sum(OBDDataHourly.dtc_count).label('dtc_count')
                ).filter(
                    and_(
                        OBDDataHourly.organization_id == org.id,
                        OBDDataHourly.time >= yesterday_start,
                        OBDDataHourly.time < yesterday_end
                    )
                )
                
                result = await db.execute(summary_query)
                summary = result.fetchone()
                
                if summary and summary.active_cars:
                    summaries.append({
                        "organization_id": str(org.id),
                        "organization_name": org.name,
                        "date": yesterday_start.date().isoformat(),
                        "active_cars": summary.active_cars,
                        "total_distance_km": float(summary.total_distance or 0),
                        "total_fuel_consumed_l": float(summary.total_fuel or 0),
                        "avg_speed_kmh": float(summary.avg_speed or 0),
                        "dtc_count": summary.dtc_count or 0
                    })
            
            logger.info(f"Generated daily summaries for {len(summaries)} organizations")
            return summaries
    
    try:
        result = _run_async(_generate_summary())
        return result
    except Exception as e:
        logger.error(f"Daily fleet summary generation failed: {e}")
        raise self.retry(exc=e)


@shared_task(
    name="backend.tasks.data_aggregator.backfill_hourly_data",
    bind=True
)
def backfill_hourly_data(self, start_date: str, end_date: str):
    """
    Backfill hourly data for a date range.
    
    Use this to fill in missing hourly aggregates.
    
    Args:
        start_date: Start date in ISO format
        end_date: End date in ISO format
    """
    async def _backfill():
        from db.session import AsyncSessionLocal
        from domain.models import OBDData, OBDDataHourly
        from sqlalchemy import select, func, and_
        
        start = datetime.fromisoformat(start_date).replace(tzinfo=timezone.utc)
        end = datetime.fromisoformat(end_date).replace(tzinfo=timezone.utc)
        
        async with AsyncSessionLocal() as db:
            current = start
            total_backfilled = 0
            
            while current < end:
                hour_start = current
                hour_end = current + timedelta(hours=1)
                
                # Aggregate query for this hour
                aggregate_query = select(
                    func.date_trunc('hour', OBDData.time).label('hour'),
                    OBDData.car_id,
                    OBDData.organization_id,
                    func.avg(OBDData.rpm).label('avg_rpm'),
                    func.avg(OBDData.speed).label('avg_speed'),
                    func.max(OBDData.speed).label('max_speed'),
                    func.avg(OBDData.throttle_position).label('avg_throttle'),
                    func.avg(OBDData.engine_load).label('avg_engine_load'),
                    func.avg(OBDData.coolant_temp).label('avg_coolant_temp'),
                    func.avg(OBDData.fuel_rate).label('avg_fuel_rate'),
                    func.coalesce(func.sum(func.array_length(OBDData.dtc_codes, 1)), 0).label('dtc_count')
                ).filter(
                    and_(
                        OBDData.time >= hour_start,
                        OBDData.time < hour_end
                    )
                ).group_by(
                    'hour', OBDData.car_id, OBDData.organization_id
                )
                
                result = await db.execute(aggregate_query)
                aggregates = result.fetchall()
                
                for agg in aggregates:
                    points_query = select(
                        OBDData.time,
                        OBDData.latitude,
                        OBDData.longitude,
                        OBDData.fuel_rate,
                    ).filter(
                        and_(
                            OBDData.car_id == agg.car_id,
                            OBDData.time >= hour_start,
                            OBDData.time < hour_end,
                        )
                    ).order_by(OBDData.time.asc())
                    points_result = await db.execute(points_query)
                    points = points_result.fetchall()
                    
                    distance_km = 0.0
                    if len(points) >= 2:
                        lat_lon_pairs = [
                            (row.time, float(row.latitude) if row.latitude is not None else None, float(row.longitude) if row.longitude is not None else None)
                            for row in points
                        ]
                        distance_km = _compute_distance_from_obd_records(lat_lon_pairs)
                    
                    avg_fuel_rate = float(agg.avg_fuel_rate) if agg.avg_fuel_rate else 0.0
                    fuel_consumed = avg_fuel_rate  # L/h
                    
                    # Check if record already exists
                    check_query = select(OBDDataHourly).filter(
                        and_(
                            OBDDataHourly.time == agg.hour,
                            OBDDataHourly.car_id == agg.car_id
                        )
                    )
                    existing = await db.execute(check_query)
                    if existing.scalars().first():
                        continue
                    
                    hourly_data = OBDDataHourly(
                        time=agg.hour,
                        car_id=agg.car_id,
                        organization_id=agg.organization_id,
                        avg_rpm=agg.avg_rpm,
                        avg_speed=agg.avg_speed,
                        max_speed=agg.max_speed,
                        avg_throttle=agg.avg_throttle,
                        avg_engine_load=agg.avg_engine_load,
                        avg_coolant_temp=agg.avg_coolant_temp,
                        avg_fuel_rate=agg.avg_fuel_rate,
                        total_distance_km=distance_km if distance_km > 0 else None,
                        total_fuel_consumed_l=fuel_consumed if fuel_consumed > 0 else None,
                        dtc_count=agg.dtc_count
                    )
                    db.add(hourly_data)
                    total_backfilled += 1
                
                await db.commit()
                current += timedelta(hours=1)
            
            logger.info(f"Backfilled {total_backfilled} hourly records")
            return {"backfilled": total_backfilled}
    
    try:
        result = _run_async(_backfill())
        return result
    except Exception as e:
        logger.error(f"Backfill failed: {e}")
        raise self.retry(exc=e)