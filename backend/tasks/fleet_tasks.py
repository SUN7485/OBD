"""Fleet automation Celery tasks."""
import logging
from datetime import datetime, timezone
from typing import List
import uuid

from celery import shared_task

logger = logging.getLogger(__name__)


@shared_task(
    name="backend.tasks.fleet_tasks.calculate_daily_driver_scores",
    bind=True
)
def calculate_daily_driver_scores(self):
    """Calculate daily driver scores for all organizations."""
    import asyncio
    
    async def _calculate():
        from backend.db.session import AsyncSessionLocal
        from backend.services.driver import DriverScoreService
        from backend.domain.models import Organization
        from sqlalchemy import select
        
        async with AsyncSessionLocal() as db:
            # Get all active organizations
            result = await db.execute(
                select(Organization).filter(Organization.is_active == True)
            )
            organizations = result.scalars().all()
            
            service = DriverScoreService(db)
            total_scores = 0
            
            for org in organizations:
                try:
                    scores = await service.calculate_daily_scores(
                        organization_id=org.id
                    )
                    total_scores += len(scores)
                    logger.info(f"Calculated {len(scores)} driver scores for org {org.id}")
                except Exception as e:
                    logger.error(f"Error calculating scores for org {org.id}: {e}")
            
            return {"total_scores": total_scores}
    
    try:
        return asyncio.run(_calculate())
    except Exception as e:
        logger.error(f"Daily driver scoring failed: {e}")
        raise self.retry(exc=e)


@shared_task(
    name="backend.tasks.fleet_tasks.run_fuel_anomaly_detection",
    bind=True
)
def run_fuel_anomaly_detection(self):
    """Run fuel anomaly detection for all active vehicles."""
    import asyncio
    
    async def _detect():
        from backend.db.session import AsyncSessionLocal
        from backend.services.fuel_anomaly import FuelAnomalyService
        from backend.domain.models import Car
        from sqlalchemy import select
        
        async with AsyncSessionLocal() as db:
            # Get all active cars
            result = await db.execute(
                select(Car).filter(Car.is_active == True)
            )
            cars = result.scalars().all()
            
            service = FuelAnomalyService(db)
            total_anomalies = 0
            
            for car in cars:
                try:
                    result = await service.analyze_fuel_consumption(
                        car_id=car.id,
                        organization_id=car.organization_id,
                        days=7
                    )
                    total_anomalies += result.get("anomalies_detected", 0)
                    
                    # Also check idle fuel theft
                    await service.check_idle_fuel_theft(
                        car_id=car.id,
                        organization_id=car.organization_id,
                        hours=24
                    )
                    
                except Exception as e:
                    logger.error(f"Error analyzing fuel for car {car.id}: {e}")
            
            return {"total_anomalies": total_anomalies}
    
    try:
        return asyncio.run(_detect())
    except Exception as e:
        logger.error(f"Fuel anomaly detection failed: {e}")
        raise self.retry(exc=e)


@shared_task(
    name="backend.tasks.fleet_tasks.run_maintenance_predictions",
    bind=True
)
def run_maintenance_predictions(self):
    """Run maintenance predictions for all active vehicles."""
    import asyncio
    
    async def _predict():
        from backend.db.session import AsyncSessionLocal
        from backend.services.driver import MaintenanceService
        from backend.domain.models import Car
        from sqlalchemy import select
        
        async with AsyncSessionLocal() as db:
            result = await db.execute(
                select(Car).filter(Car.is_active == True)
            )
            cars = result.scalars().all()
            
            service = MaintenanceService(db)
            total_predictions = 0
            
            for car in cars:
                try:
                    predictions = await service.predict_maintenance_needs(
                        car_id=car.id,
                        organization_id=car.organization_id
                    )
                    total_predictions += len(predictions)
                except Exception as e:
                    logger.error(f"Error predicting maintenance for car {car.id}: {e}")
            
            return {"total_predictions": total_predictions}
    
    try:
        return asyncio.run(_predict())
    except Exception as e:
        logger.error(f"Maintenance prediction failed: {e}")
        raise self.retry(exc=e)


@shared_task(
    name="backend.tasks.fleet_tasks.process_geofence_locations",
    bind=True
)
def process_geofence_locations(self):
    """Process recent vehicle locations against geofences."""
    import asyncio
    
    async def _process():
        from backend.db.session import AsyncSessionLocal
        from backend.services.geofence import GeofenceService
        from backend.domain.models import Car, OBDData
        from sqlalchemy import select, func
        from datetime import timedelta
        
        async with AsyncSessionLocal() as db:
            # Get latest location for each active car
            subquery = (
                select(
                    OBDData.car_id,
                    func.max(OBDData.time).label('last_time')
                )
                .filter(
                    OBDData.latitude.isnot(None),
                    OBDData.longitude.isnot(None)
                )
                .group_by(OBDData.car_id)
                .subquery()
            )
            
            query = (
                select(OBDData, Car)
                .join(subquery, OBDData.car_id == subquery.c.car_id)
                .join(Car, OBDData.car_id == Car.id)
                .filter(OBDData.time == subquery.c.last_time)
                .limit(100)  # Process in batches
            )
            
            result = await db.execute(query)
            records = result.fetchall()
            
            service = GeofenceService(db)
            total_events = 0
            
            for obd_data, car in records:
                try:
                    events = await service.check_location(
                        car_id=car.id,
                        latitude=float(obd_data.latitude),
                        longitude=float(obd_data.longitude),
                        organization_id=car.organization_id
                    )
                    total_events += len(events)
                except Exception as e:
                    logger.error(f"Error processing location for car {car.id}: {e}")
            
            return {"total_events": total_events}
    
    try:
        return asyncio.run(_process())
    except Exception as e:
        logger.error(f"Geofence processing failed: {e}")
        raise self.retry(exc=e)


@shared_task(
    name="backend.tasks.fleet_tasks.generate_fleet_report",
    bind=True
)
def generate_fleet_report(self):
    """Generate daily fleet performance report."""
    import asyncio
    
    async def _generate():
        from backend.db.session import AsyncSessionLocal
        from backend.domain.models import Organization, Car, Alert, OBDDataHourly
        from sqlalchemy import select, func, and_
        from datetime import timedelta
        
        reports = []
        
        async with AsyncSessionLocal() as db:
            # Get all organizations
            result = await db.execute(
                select(Organization).filter(Organization.is_active == True)
            )
            organizations = result.scalars().all()
            
            for org in organizations:
                try:
                    # Get fleet stats
                    yesterday = datetime.now(timezone.utc) - timedelta(days=1)
                    
                    # Total cars
                    cars_result = await db.execute(
                        select(func.count(Car.id)).filter(
                            Car.organization_id == org.id,
                            Car.is_active == True
                        )
                    )
                    total_cars = cars_result.scalar() or 0
                    
                    # Active cars
                    active_result = await db.execute(
                        select(func.count(func.distinct(OBDDataHourly.car_id))).filter(
                            OBDDataHourly.organization_id == org.id,
                            OBDDataHourly.time >= yesterday
                        )
                    )
                    active_cars = active_result.scalar() or 0
                    
                    # Alerts
                    alerts_result = await db.execute(
                        select(func.count(Alert.id)).filter(
                            Alert.organization_id == org.id,
                            Alert.created_at >= yesterday,
                            Alert.is_resolved == False
                        )
                    )
                    active_alerts = alerts_result.scalar() or 0
                    
                    # Distance
                    distance_result = await db.execute(
                        select(func.sum(OBDDataHourly.total_distance_km)).filter(
                            OBDDataHourly.organization_id == org.id,
                            OBDDataHourly.time >= yesterday
                        )
                    )
                    total_distance = float(distance_result.scalar() or 0)
                    
                    report = {
                        "organization_id": str(org.id),
                        "organization_name": org.name,
                        "date": yesterday.date().isoformat(),
                        "total_cars": total_cars,
                        "active_cars": active_cars,
                        "active_alerts": active_alerts,
                        "total_distance_km": round(total_distance, 2)
                    }
                    
                    reports.append(report)
                    
                    # Broadcast to admin via WebSocket
                    try:
                        from backend.services.websocket_manager import manager
                        await manager.broadcast_to_org(
                            org.id,
                            {
                                "type": "daily_report",
                                "data": report
                            }
                        )
                    except Exception:
                        pass
                        
                except Exception as e:
                    logger.error(f"Error generating report for org {org.id}: {e}")
            
            return {"reports_generated": len(reports)}
    
    try:
        return asyncio.run(_generate())
    except Exception as e:
        logger.error(f"Fleet report generation failed: {e}")
        raise self.retry(exc=e)
