from fastapi import APIRouter, status, HTTPException, Depends
from fastapi.responses import JSONResponse, PlainTextResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text
import asyncio
import httpx
import redis.asyncio as aioredis
import time

from config.settings import settings
from db.session import AsyncSessionLocal
from api.v1.schemas.health import HealthResponse
from services.llm_client import get_llm_client
from middleware.auth import get_current_user, require_role

router = APIRouter(tags=["health"])

start_time = time.time()


async def get_prometheus_metrics() -> str:
    try:
        import prometheus_client
        return prometheus_client.generate_latest(prometheus_client.REGISTRY).decode()
    except ImportError:
        return ""


@router.get("/metrics")
async def metrics_check(current_user = Depends(require_role(["admin"]))):
    """Return Prometheus metrics - admin only."""
    metrics = await get_prometheus_metrics()
    if not metrics:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Prometheus not installed"
        )
    return PlainTextResponse(content=metrics, media_type="text/plain")


@router.get("/live")
async def liveness_check():
    """Liveness probe - returns 200 if process is alive."""
    return {"status": "alive"}


@router.get("/ready")
async def readiness_check():
    """Readiness probe - checks DB, Redis, and LLM connectivity."""
    db_status = "unknown"
    redis_status = "unknown"
    lm_status = "unknown"
    details = {}

    # DB check
    try:
        async with AsyncSessionLocal() as session:
            result = await session.execute(text("SELECT 1"))
            if result.scalar() == 1:
                db_status = "connected"
            else:
                db_status = "error"
    except Exception as e:
        db_status = "error"
        details["db_error"] = str(e)

    # Redis check
    try:
        redis = await aioredis.from_url(
            settings.REDIS_URL, encoding="utf-8", decode_responses=True
        )
        pong = await redis.ping()
        redis_status = "connected" if pong in (True, "PONG") else "error"
        await redis.close()
    except Exception as e:
        redis_status = "error"
        details["redis_error"] = str(e)

    # LLM check
    try:
        llm = get_llm_client()
        lm_status = llm.get_circuit_state()
        if lm_status == "closed":
            lm_status = "connected"
    except Exception as e:
        lm_status = "error"
        details["llm_error"] = str(e)

    # Determine overall status
    if db_status == "connected" and redis_status == "connected":
        overall = "healthy"
        code = status.HTTP_200_OK
    else:
        overall = "unhealthy"
        code = status.HTTP_503_SERVICE_UNAVAILABLE

    return JSONResponse(
        content={
            "status": overall,
            "database": db_status,
            "redis": redis_status,
            "llm": lm_status,
            "details": details,
        },
        status_code=code,
    )


@router.get("/", response_model=HealthResponse)
async def health_check():
    """Main health endpoint - checks DB, Redis, and LLM."""
    db_status = "unknown"
    redis_status = "unknown"
    lm_status = "unknown"

    # DB
    try:
        async with AsyncSessionLocal() as session:
            result = await session.execute(text("SELECT 1"))
            db_status = "connected" if result.scalar() == 1 else "error"
    except Exception:
        db_status = "error"

    # Redis
    try:
        redis = await aioredis.from_url(
            settings.REDIS_URL, encoding="utf-8", decode_responses=True
        )
        pong = await redis.ping()
        redis_status = "connected" if pong in (True, "PONG") else "error"
        await redis.close()
    except Exception:
        redis_status = "error"

    # LM Studio
    if settings.LM_STUDIO_URL:
        try:
            llm = get_llm_client()
            state = llm.get_circuit_state()
            lm_status = state if state != "closed" else "connected"
        except Exception:
            lm_status = "unreachable"
    else:
        lm_status = "not configured"

    if db_status == "connected" and redis_status == "connected":
        overall = "healthy"
        code = status.HTTP_200_OK
    elif db_status == "error":
        overall = "unhealthy"
        code = status.HTTP_503_SERVICE_UNAVAILABLE
    else:
        overall = "degraded"
        code = status.HTTP_503_SERVICE_UNAVAILABLE

    return JSONResponse(
        content=HealthResponse(
            status=overall, database=db_status, redis=redis_status, lm_studio=lm_status
        ).dict(),
        status_code=code,
    )