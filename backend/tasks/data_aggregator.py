"""Data aggregation Celery task."""
import logging
from datetime import datetime, timedelta, timezone
from typing import List, Dict, Any
import uuid

from celery import shared_task

logger = logging.getLogger(__name__)


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
    import asyncio
    
    async def _aggregate_hourly():
        from backend.db.session import AsyncSessionLocal
        from backend.domain.models import OBDData, OBDDataHourly
        from sqlalchemy import select, func, and_
        from sqlalchemy.dialects.postgresql import insert
        
        async with AsyncSessionLocal() as db:
            # Get the last hour's data to aggregate
            now = datetime.now(timezone.utc)
            hour_start = now.replace(minute=0, second=0, microsecond=0)
            hour_end = hour_start + timedelta(hours=1)
            
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
                # Calculate distance (approximation using average speed)
                avg_speed_kmh = float(agg.avg_speed) if agg.avg_speed else 0
                distance_km = avg_speed_kmh / 60  # 1 hour of driving at avg speed
                
                # Calculate fuel consumed
                avg_fuel_rate = float(agg.avg_fuel_rate) if agg.avg_fuel_rate else 0
                fuel_consumed = avg_fuel_rate  # L/h
                
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
                    total_distance_km=distance_km,
                    total_fuel_consumed_l=fuel_consumed,
                    dtc_count=agg.dtc_count
                )
                db.add(hourly_data)
                inserted_count += 1
            
            await db.commit()
            logger.info(f"Aggregated {inserted_count} hourly records")
            
            return {"aggregated": inserted_count, "hour": hour_start.isoformat()}
    
    try:
        result = asyncio.run(_aggregate_hourly())
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
    import asyncio
    
    async def _generate_summary():
        from backend.db.session import AsyncSessionLocal
        from backend.domain.models import Organization, OBDDataHourly
        from sqlalchemy import select, func
        
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
        result = asyncio.run(_generate_summary())
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
    import asyncio
    from datetime import datetime
    
    async def _backfill():
        from backend.db.session import AsyncSessionLocal
        from backend.domain.models import OBDData, OBDDataHourly
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
                    avg_speed_kmh = float(agg.avg_speed) if agg.avg_speed else 0
                    distance_km = avg_speed_kmh / 60
                    avg_fuel_rate = float(agg.avg_fuel_rate) if agg.avg_fuel_rate else 0
                    fuel_consumed = avg_fuel_rate
                    
                    # Check if record already exists
                    check_query = select(OBDDataHourly).filter(
                        and_(
                            OBDDataHourly.time == agg.hour,
                            OBDDataHourly.car_id == agg.car_id
                        )
                    )
                    existing = await db.execute(check_query)
                    if existing.scalars().first():
                        continue  # Skip existing records
                    
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
                        total_distance_km=distance_km,
                        total_fuel_consumed_l=fuel_consumed,
                        dtc_count=agg.dtc_count
                    )
                    db.add(hourly_data)
                    total_backfilled += 1
                
                await db.commit()
                current += timedelta(hours=1)
            
            logger.info(f"Backfilled {total_backfilled} hourly records")
            return {"backfilled": total_backfilled}
    
    try:
        result = asyncio.run(_backfill())
        return result
    except Exception as e:
        logger.error(f"Backfill failed: {e}")
        raise self.retry(exc=e)
