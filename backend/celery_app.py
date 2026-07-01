"""Celery application configuration."""
import logging
from celery import Celery
from celery.schedules import crontab

from config.settings import settings

logger = logging.getLogger(__name__)

celery_app = Celery(
    "fleet_obd",
    broker=settings.REDIS_URL,
    backend=settings.REDIS_URL,
    include=[
        "tasks.threshold_checker",
        "tasks.anomaly_detector",
        "tasks.data_aggregator",
        "tasks.ai_tasks",
        "tasks.fleet_tasks",
    ],
)

celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    result_expires=86400,
    task_routes={
        "tasks.threshold_checker.*": {"queue": "default"},
        "tasks.anomaly_detector.*": {"queue": "default"},
        "tasks.data_aggregator.*": {"queue": "aggregation"},
        "tasks.ai_tasks.*": {"queue": "ai"},
    },
    worker_prefetch_multiplier=4,
    worker_max_tasks_per_child=1000,
    task_track_started=True,
    task_soft_time_limit=300,
    task_time_limit=600,
    beat_schedule={
        "aggregate-hourly-data": {
            "task": "tasks.data_aggregator.aggregate_hourly_data",
            "schedule": crontab(minute=5),
        },
        "daily-fleet-summary": {
            "task": "tasks.data_aggregator.generate_daily_fleet_summary",
            "schedule": crontab(hour=1, minute=0),
        },
        "daily-driver-scores": {
            "task": "tasks.fleet_tasks.calculate_daily_driver_scores",
            "schedule": crontab(hour=2, minute=0),
        },
        "daily-fuel-anomaly-detection": {
            "task": "tasks.fleet_tasks.run_fuel_anomaly_detection",
            "schedule": crontab(hour=3, minute=0),
        },
        "weekly-maintenance-predictions": {
            "task": "tasks.fleet_tasks.run_maintenance_predictions",
            "schedule": crontab(hour=4, minute=0, day_of_week=0),
        },
        "hourly-geofence-processing": {
            "task": "tasks.fleet_tasks.process_geofence_locations",
            "schedule": crontab(minute=30),
        },
        "daily-fleet-report": {
            "task": "tasks.fleet_tasks.generate_fleet_report",
            "schedule": crontab(hour=6, minute=0),
        },
    },
)


def register_tasks():
    try:
        import tasks.threshold_checker
        import tasks.anomaly_detector
        import tasks.data_aggregator
        import tasks.ai_tasks
        logger.info("Celery tasks registered")
    except Exception as e:
        logger.error(f"Error registering tasks: {e}")


register_tasks()
