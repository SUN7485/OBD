"""AI-triggered Celery tasks."""
import logging
from typing import Dict, Any, List
import uuid

from celery import shared_task
from celery.exceptions import MaxRetriesExceededError

logger = logging.getLogger(__name__)

# Rate limiting key prefix
RATE_LIMIT_PREFIX = "ai_rate_limit:"
RATE_LIMIT_WINDOW = 60  # seconds
RATE_LIMIT_MAX = 10  # max requests per window


@shared_task(
    name="backend.tasks.ai_tasks.trigger_ai_diagnostic",
    bind=True,
    max_retries=3,
    default_retry_delay=60
)
def trigger_ai_diagnostic(
    self,
    car_id: str,
    dtc_codes: List[str]
):
    """
    Trigger AI diagnostic analysis for DTC codes.
    
    This task is rate-limited to prevent excessive AI usage.
    
    Args:
        car_id: UUID of the car
        dtc_codes: List of DTC codes to analyze
    """
    import asyncio
    
    async def _trigger_ai():
        from backend.db.session import AsyncSessionLocal
        from backend.services.ai_service import AIService
        from backend.services.websocket_manager import manager
        
        # Check rate limit
        from backend.services.redis_client import redis_client
        await redis_client.connect()
        
        rate_key = f"{RATE_LIMIT_PREFIX}{car_id}"
        current_count = await redis_client.get(rate_key)
        
        if current_count and int(current_count) >= RATE_LIMIT_MAX:
            logger.warning(f"Rate limit exceeded for car {car_id}")
            return {
                "status": "rate_limited",
                "message": "Too many AI requests. Please try again later."
            }
        
        # Increment rate limit counter
        await redis_client.incr(rate_key)
        await redis_client.expire(rate_key, RATE_LIMIT_WINDOW)
        
        car_uuid = uuid.UUID(car_id)
        
        async with AsyncSessionLocal() as db:
            # Get user_id from car assignment or use system
            from sqlalchemy import select
            from backend.domain.models import Car
            
            result = await db.execute(
                select(Car).filter(Car.id == car_uuid)
            )
            car = result.scalars().first()
            
            if not car:
                logger.warning(f"Car {car_id} not found")
                return {"status": "error", "message": "Car not found"}
            
            # Use organization owner as user if no driver assigned
            user_id = car.assigned_driver_id if car.assigned_driver_id else None
            
            if not user_id:
                # Get any admin user
                from backend.domain.models import User
                result = await db.execute(
                    select(User.id).filter(
                        User.organization_id == car.organization_id,
                        User.role == "admin"
                    ).limit(1)
                )
                user_row = result.fetchone()
                if user_row:
                    user_id = user_row[0]
            
            if not user_id:
                logger.warning(f"No user found for AI diagnostic")
                return {"status": "error", "message": "No user found"}
            
            ai_service = AIService(db)
            
            try:
                result = await ai_service.explain_dtc_codes(
                    car_id=car_uuid,
                    dtc_codes=dtc_codes,
                    user_id=user_id
                )
                
                # Broadcast AI response to WebSocket
                try:
                    await manager.broadcast_to_car(
                        car_uuid,
                        {
                            "type": "ai_reply",
                            "data": {
                                "session_type": "diagnostic",
                                "content": result["explanation"],
                                "dtc_codes": dtc_codes
                            }
                        }
                    )
                except Exception as e:
                    logger.error(f"WebSocket broadcast error: {e}")
                
                logger.info(f"AI diagnostic completed for car {car_id}")
                
                return {
                    "status": "success",
                    "session_id": result["session_id"]
                }
                
            except RuntimeError as e:
                logger.error(f"AI service error: {e}")
                raise self.retry(exc=e)
    
    try:
        result = asyncio.run(_trigger_ai())
        return result
    except Exception as e:
        logger.error(f"AI diagnostic task failed for car {car_id}: {e}")
        raise self.retry(exc=e)


@shared_task(
    name="backend.tasks.ai_tasks.trigger_ai_analysis",
    bind=True,
    max_retries=2,
    default_retry_delay=120
)
def trigger_ai_analysis(
    self,
    car_id: str,
    telemetry_data: Dict[str, Any],
    baseline_data: Dict[str, Any]
):
    """
    Trigger AI analysis for detected anomalies.
    
    Args:
        car_id: UUID of the car
        telemetry_data: Current telemetry values
        baseline_data: Historical baseline values
    """
    import asyncio
    
    async def _trigger_ai():
        from backend.db.session import AsyncSessionLocal
        from backend.services.ai_service import AIService
        from backend.services.websocket_manager import manager
        from backend.services.prompts import ANOMALY_ANALYSIS_USER_PROMPT
        
        car_uuid = uuid.UUID(car_id)
        
        async with AsyncSessionLocal() as db:
            from sqlalchemy import select
            from backend.domain.models import Car
            
            result = await db.execute(
                select(Car).filter(Car.id == car_uuid)
            )
            car = result.scalars().first()
            
            if not car:
                return {"status": "error", "message": "Car not found"}
            
            # Build prompt
            anomalies = baseline_data.get("anomalies", [])
            baseline = baseline_data.get("baseline", {})
            
            anomaly_details = "\n".join([
                f"- {a['metric']}: {a['current_value']} (baseline: {a['baseline_avg']:.1f}, z-score: {a['z_score']:.1f})"
                for a in anomalies
            ])
            
            baseline_details = "\n".join([
                f"- {k}: {v}" if v else f"- {k}: N/A"
                for k, v in baseline.items()
            ])
            
            current_values = "\n".join([
                f"- {k}: {v}" if v else f"- {k}: N/A"
                for k, v in telemetry_data.items()
            ])
            
            user_prompt = ANOMALY_ANALYSIS_USER_PROMPT.format(
                year=car.year,
                make=car.make,
                model=car.model,
                anomaly_details=anomaly_details or "Multiple anomalies detected",
                baseline_details=baseline_details or "No baseline available",
                current_values=current_values or "No current values"
            )
            
            # Get LLM client
            from backend.services.llm_client import get_llm_client
            from backend.services.ai_safety import sanitize_response
            
            llm_client = get_llm_client()
            
            try:
                response = await llm_client.chat([
                    {"role": "system", "content": "You are an automotive diagnostics expert."},
                    {"role": "user", "content": user_prompt}
                ])
                
                content = sanitize_response(response["content"])
                
                # Broadcast result
                try:
                    await manager.broadcast_to_car(
                        car_uuid,
                        {
                            "type": "ai_reply",
                            "data": {
                                "session_type": "anomaly_analysis",
                                "content": content,
                                "anomalies": anomalies
                            }
                        }
                    )
                except Exception as e:
                    logger.error(f"WebSocket broadcast error: {e}")
                
                return {
                    "status": "success",
                    "analysis": content
                }
                
            except Exception as e:
                logger.error(f"AI analysis failed: {e}")
                return {"status": "error", "message": str(e)}
    
    try:
        result = asyncio.run(_trigger_ai())
        return result
    except Exception as e:
        logger.error(f"AI analysis task failed for car {car_id}: {e}")
        raise self.retry(exc=e)
