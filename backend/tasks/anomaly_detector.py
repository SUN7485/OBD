"""Anomaly detection Celery task."""
import logging
from datetime import datetime, timedelta, timezone
from typing import Dict, Any, List, Optional
import uuid

from celery import shared_task
import numpy as np

logger = logging.getLogger(__name__)

# Z-score threshold for anomaly detection
ANOMALY_ZSCORE_THRESHOLD = 3.0

# Metrics to check for anomalies
ANOMALY_METRICS = ["rpm", "speed", "coolant_temp", "fuel_rate", "engine_load"]


@shared_task(
    name="backend.tasks.anomaly_detector.detect_anomalies",
    bind=True,
    max_retries=3,
    default_retry_delay=300
)
def detect_anomalies(
    self,
    car_id: str,
    telemetry_data: Dict[str, Any]
):
    """
    Detect anomalies in telemetry data using statistical methods.
    
    Compares current values against 7-day baseline and flags anomalies
    when z-score exceeds threshold.
    
    Args:
        car_id: UUID of the car
        telemetry_data: Dictionary containing telemetry values
    """
    import asyncio
    
    async def _detect_anomalies():
        from db.session import AsyncSessionLocal
        from services.alerts import AlertService
        from services.alerts import AlertType, AlertSeverity
        from domain.models import Car, OBDData
        from sqlalchemy import select, func, and_
        
        car_uuid = uuid.UUID(car_id)
        
        async with AsyncSessionLocal() as db:
            # Get car
            result = await db.execute(
                select(Car).filter(Car.id == car_uuid)
            )
            car = result.scalars().first()
            
            if not car:
                logger.warning(f"Car {car_id} not found for anomaly detection")
                return
            
            organization_id = car.organization_id
            
            # Fetch baseline data (last 7 days)
            seven_days_ago = datetime.now(timezone.utc) - timedelta(days=7)
            
            baseline_query = select(
                func.avg(OBDData.rpm).label("avg_rpm"),
                func.stddev(OBDData.rpm).label("std_rpm"),
                func.avg(OBDData.speed).label("avg_speed"),
                func.stddev(OBDData.speed).label("std_speed"),
                func.avg(OBDData.coolant_temp).label("avg_coolant"),
                func.stddev(OBDData.coolant_temp).label("std_coolant"),
                func.avg(OBDData.fuel_rate).label("avg_fuel"),
                func.stddev(OBDData.fuel_rate).label("std_fuel"),
                func.avg(OBDData.engine_load).label("avg_load"),
                func.stddev(OBDData.engine_load).label("std_load"),
            ).filter(
                and_(
                    OBDData.car_id == car_uuid,
                    OBDData.time >= seven_days_ago
                )
            )
            
            result = await db.execute(baseline_query)
            baseline = result.fetchone()
            
            if not baseline or not baseline.avg_rpm:
                logger.info(f"Insufficient baseline data for car {car_id}")
                return
            
            # Calculate z-scores
            anomalies = []
            
            # Check each metric
            for metric in ANOMALY_METRICS:
                current_value = telemetry_data.get(metric)
                if current_value is None:
                    continue
                
                baseline_avg, baseline_std = _get_baseline_values(baseline, metric)
                
                if baseline_std is None or baseline_std == 0:
                    continue
                
                z_score = abs(current_value - baseline_avg) / baseline_std
                
                if z_score > ANOMALY_ZSCORE_THRESHOLD:
                    anomalies.append({
                        "metric": metric,
                        "current_value": current_value,
                        "baseline_avg": baseline_avg,
                        "z_score": z_score
                    })
            
            # Create alerts for significant anomalies
            if anomalies:
                alerts_service = AlertService(db)
                
                for anomaly in anomalies:
                    alert = await alerts_service.create_alert(
                        car_id=car_uuid,
                        organization_id=organization_id,
                        alert_type=AlertType.anomaly_detected,
                        severity=AlertSeverity.warning,
                        title=f"Anomaly Detected: {anomaly['metric']}",
                        message=f"Unusual {anomaly['metric']} value: {anomaly['current_value']} (baseline: {anomaly['baseline_avg']:.1f}, z-score: {anomaly['z_score']:.1f})",
                        metadata={
                            "metric": anomaly["metric"],
                            "current_value": anomaly["current_value"],
                            "baseline_avg": anomaly["baseline_avg"],
                            "z_score": anomaly["z_score"]
                        }
                    )
                    
                    # Broadcast to WebSocket
                    try:
                        from services.websocket_manager import manager
                        await manager.broadcast_to_car(
                            car_uuid,
                            {
                                "type": "alert",
                                "data": {
                                    "alert_type": "anomaly_detected",
                                    "severity": "warning",
                                    "title": alert.title,
                                    "message": alert.message
                                }
                            }
                        )
                    except Exception as e:
                        logger.error(f"WebSocket broadcast error: {e}")
                
                # Trigger AI analysis for significant anomalies
                if len(anomalies) >= 2:
                    try:
                        from tasks.ai_tasks import trigger_ai_analysis
                        trigger_ai_analysis.delay(car_id, telemetry_data, {
                            "anomalies": anomalies,
                            "baseline": {
                                "avg_rpm": baseline.avg_rpm,
                                "avg_speed": baseline.avg_speed,
                                "avg_coolant": baseline.avg_coolant,
                                "avg_fuel": baseline.avg_fuel,
                                "avg_load": baseline.avg_load
                            }
                        })
                    except Exception as e:
                        logger.error(f"Failed to trigger AI analysis: {e}")
                
                logger.info(f"Anomaly detection completed for car {car_id}: {len(anomalies)} anomalies found")
    
    try:
        asyncio.run(_detect_anomalies())
    except Exception as e:
        logger.error(f"Anomaly detection failed for car {car_id}: {e}")
        raise self.retry(exc=e)


def _get_baseline_values(baseline, metric: str):
    """Extract baseline average and std for a metric."""
    mapping = {
        "rpm": (baseline.avg_rpm, baseline.std_rpm),
        "speed": (baseline.avg_speed, baseline.std_speed),
        "coolant_temp": (baseline.avg_coolant, baseline.std_coolant),
        "fuel_rate": (baseline.avg_fuel, baseline.std_fuel),
        "engine_load": (baseline.avg_load, baseline.std_load),
    }
    return mapping.get(metric, (None, None))


@shared_task(
    name="backend.tasks.anomaly_detector.batch_anomaly_check",
    bind=True
)
def batch_anomaly_check(self, car_ids: List[str]):
    """
    Run anomaly detection on multiple cars.
    
    This is a convenience task to run anomaly detection
    on a batch of cars.
    """
    results = []
    
    for car_id in car_ids:
        try:
            # This would fetch the latest telemetry for each car
            # and run anomaly detection
            # For now, we'll just log
            logger.info(f"Would run anomaly check for car {car_id}")
            results.append({"car_id": car_id, "status": "pending"})
        except Exception as e:
            logger.error(f"Error queueing anomaly check for car {car_id}: {e}")
            results.append({"car_id": car_id, "status": "error", "error": str(e)})
    
    return results
