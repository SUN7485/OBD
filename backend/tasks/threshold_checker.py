"""Threshold checking Celery task."""
import logging
from datetime import datetime, timezone
from typing import Dict, Any, Optional
import uuid

from celery import shared_task

logger = logging.getLogger(__name__)

# Threshold configurations
THRESHOLDS = {
    "coolant_temp_warning": 100,  # °C
    "coolant_temp_critical": 110,  # °C
    "engine_load_warning": 90,  # %
    "speed_warning": 150,  # km/h
}


@shared_task(
    name="backend.tasks.threshold_checker.check_thresholds",
    bind=True,
    max_retries=3,
    default_retry_delay=60
)
def check_thresholds(
    self,
    car_id: str,
    telemetry_data: Dict[str, Any]
):
    """
    Check telemetry data against predefined thresholds.
    
    Creates alerts when thresholds are exceeded and triggers AI diagnostic
    when DTC codes are detected.
    
    Args:
        car_id: UUID of the car
        telemetry_data: Dictionary containing telemetry values
    """
    import asyncio
    
    async def _check_thresholds():
        from db.session import AsyncSessionLocal
        from services.alerts import AlertService
        from services.alerts import AlertType, AlertSeverity
        from domain.models import Car
        
        car_uuid = uuid.UUID(car_id)
        
        async with AsyncSessionLocal() as db:
            # Get car and organization
            from sqlalchemy import select
            result = await db.execute(
                select(Car).filter(Car.id == car_uuid)
            )
            car = result.scalars().first()
            
            if not car:
                logger.warning(f"Car {car_id} not found for threshold check")
                return
            
            organization_id = car.organization_id
            alerts_service = AlertService(db)
            
            alerts_created = []
            
            # Check coolant temperature
            coolant_temp = telemetry_data.get("coolant_temp")
            if coolant_temp:
                if coolant_temp >= THRESHOLDS["coolant_temp_critical"]:
                    alert = await alerts_service.create_alert(
                        car_id=car_uuid,
                        organization_id=organization_id,
                        alert_type=AlertType.threshold_exceeded,
                        severity=AlertSeverity.critical,
                        title="Critical: High Coolant Temperature",
                        message=f"Coolant temperature is {coolant_temp}°C (critical threshold: {THRESHOLDS['coolant_temp_critical']}°C)",
                        metadata={"coolant_temp": coolant_temp, "threshold": THRESHOLDS["coolant_temp_critical"]}
                    )
                    alerts_created.append(alert)
                elif coolant_temp >= THRESHOLDS["coolant_temp_warning"]:
                    alert = await alerts_service.create_alert(
                        car_id=car_uuid,
                        organization_id=organization_id,
                        alert_type=AlertType.threshold_exceeded,
                        severity=AlertSeverity.warning,
                        title="Warning: High Coolant Temperature",
                        message=f"Coolant temperature is {coolant_temp}°C (warning threshold: {THRESHOLDS['coolant_temp_warning']}°C)",
                        metadata={"coolant_temp": coolant_temp, "threshold": THRESHOLDS["coolant_temp_warning"]}
                    )
                    alerts_created.append(alert)
            
            # Check engine load
            engine_load = telemetry_data.get("engine_load")
            if engine_load and engine_load >= THRESHOLDS["engine_load_warning"]:
                alert = await alerts_service.create_alert(
                    car_id=car_uuid,
                    organization_id=organization_id,
                    alert_type=AlertType.threshold_exceeded,
                    severity=AlertSeverity.warning,
                    title="Warning: High Engine Load",
                    message=f"Engine load is {engine_load}% (threshold: {THRESHOLDS['engine_load_warning']}%)",
                    metadata={"engine_load": engine_load, "threshold": THRESHOLDS["engine_load_warning"]}
                )
                alerts_created.append(alert)
            
            # Check speed
            speed = telemetry_data.get("speed")
            if speed and speed >= THRESHOLDS["speed_warning"]:
                alert = await alerts_service.create_alert(
                    car_id=car_uuid,
                    organization_id=organization_id,
                    alert_type=AlertType.threshold_exceeded,
                    severity=AlertSeverity.warning,
                    title="Warning: Speeding",
                    message=f"Vehicle speed is {speed} km/h (threshold: {THRESHOLDS['speed_warning']} km/h)",
                    metadata={"speed": speed, "threshold": THRESHOLDS["speed_warning"]}
                )
                alerts_created.append(alert)
            
            # Check DTC codes - trigger AI diagnostic
            dtc_codes = telemetry_data.get("dtc_codes")
            if dtc_codes and len(dtc_codes) > 0:
                # Create DTC alert
                alert = await alerts_service.create_alert(
                    car_id=car_uuid,
                    organization_id=organization_id,
                    alert_type=AlertType.dtc_error,
                    severity=AlertSeverity.critical,
                    title="Diagnostic Trouble Codes Detected",
                    message=f"DTC codes detected: {', '.join(dtc_codes)}",
                    metadata={"dtc_codes": dtc_codes}
                )
                alerts_created.append(alert)
                
                # Trigger AI diagnostic
                try:
                    from tasks.ai_tasks import trigger_ai_diagnostic
                    trigger_ai_diagnostic.delay(car_id, dtc_codes)
                except Exception as e:
                    logger.error(f"Failed to trigger AI diagnostic: {e}")
            
            # Broadcast alerts via WebSocket
            if alerts_created:
                try:
                    from services.websocket_manager import manager
                    for alert in alerts_created:
                        await manager.broadcast_to_car(
                            car_uuid,
                            {
                                "type": "alert",
                                "data": {
                                    "id": str(alert.id),
                                    "alert_type": alert.alert_type.value,
                                    "severity": alert.severity.value,
                                    "title": alert.title,
                                    "message": alert.message,
                                    "created_at": alert.created_at.isoformat()
                                }
                            }
                        )
                except Exception as e:
                    logger.error(f"WebSocket broadcast error: {e}")
            
            logger.info(f"Threshold check completed for car {car_id}: {len(alerts_created)} alerts created")
    
    try:
        asyncio.run(_check_thresholds())
    except Exception as e:
        logger.error(f"Threshold check failed for car {car_id}: {e}")
        raise self.retry(exc=e)
