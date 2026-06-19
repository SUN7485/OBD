import logging
from fastapi import FastAPI, Request, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from contextlib import asynccontextmanager

from config.settings import settings
from api.v1.routes import auth as auth_routes
from api.v1.routes import health as health_routes
from api.v1.routes import websocket as websocket_routes
from api.v1.routes import telemetry as telemetry_routes
from api.v1.routes import analytics as analytics_routes
from api.v1.routes import alerts as alerts_routes
from api.v1.routes import messages as messages_routes
from api.v1.routes import ai as ai_routes
from api.v1.routes import fleet as fleet_routes
from api.v1.routes import batch as batch_routes

# Configure logging
from config.logging_config import setup_logging

setup_logging()

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    logging.info("Fleet OBD Platform starting up...")

    # Startup: check DB connection
    try:
        from db.session import AsyncSessionLocal
        from sqlalchemy import text

        async with AsyncSessionLocal() as session:
            await session.execute(text("SELECT 1"))
        logging.info("Database connection verified")
    except Exception as e:
        logging.error(f"Database connection failed: {e}")

    # Start Redis client
    try:
        from services.redis_client import redis_client

        await redis_client.connect()
        logging.info("Redis client connected")
    except Exception as e:
        logging.error(f"Redis connection failed: {e}")

    # Start WebSocket manager
    try:
        from services.websocket_manager import manager

        await manager.start()
        logging.info("WebSocket manager started")
    except Exception as e:
        logging.error(f"WebSocket manager start failed: {e}")

    # Start MQTT client
    try:
        from services.mqtt_client import mqtt_client

        await mqtt_client.connect()
        logging.info("MQTT client connected")
    except Exception as e:
        logging.error(f"MQTT client connection failed: {e}")

    yield

    # Shutdown
    logging.info("Fleet OBD Platform shutting down...")

    # Stop MQTT client
    try:
        from services.mqtt_client import mqtt_client

        await mqtt_client.disconnect()
    except Exception as e:
        logger.error(f"MQTT client disconnect error: {e}")

    # Stop WebSocket manager
    try:
        from services.websocket_manager import manager

        await manager.stop()
    except Exception as e:
        logger.error(f"WebSocket manager stop error: {e}")

    # Disconnect Redis
    try:
        from services.redis_client import redis_client

        await redis_client.disconnect()
    except Exception as e:
        logger.error(f"Redis disconnect error: {e}")


app = FastAPI(
    title="Fleet OBD Platform",
    version="1.0.0",
    description="Vehicle fleet management and telemetry platform with OBD data ingestion, real-time WebSocket communication, and AI-powered diagnostics.",
    lifespan=lifespan,
)

# Rate limiting
from slowapi.errors import RateLimitExceeded
from middleware.rate_limiter import limiter, rate_limit_exceeded_handler
app.state.limiter = limiter

# Add slowapi middleware
try:
    from slowapi.middleware import SlowAPIMiddleware

    app.add_middleware(SlowAPIMiddleware)
except ImportError:
    pass

app.add_exception_handler(RateLimitExceeded, rate_limit_exceeded_handler)

# Prometheus metrics (exposed via protected endpoint in health_routes)
try:
    from prometheus_fastapi_instrumentator import Instrumentator

    instrumentator = Instrumentator(
        should_group_status_codes=False,
        should_ignore_untemplated=True,
        excluded_handlers=["/health", "/health/live", "/health/ready"],
    )
    instrumentator.instrument(app)
except ImportError:
    logger.warning(
        "prometheus-fastapi-instrumentator not installed, metrics endpoint disabled"
    )

# CORS
if not settings.CORS_ORIGINS:
    if settings.ENVIRONMENT == "prod":
        raise RuntimeError("CORS_ORIGINS must be set in production")
    origins = ["http://localhost:3000", "http://localhost:5173"]
else:
    origins = settings.CORS_ORIGINS
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Routers
app.include_router(auth_routes.router, prefix="/api/v1")
app.include_router(health_routes.router, prefix="/api/v1/health")
app.include_router(websocket_routes.router, prefix="/api/v1")
app.include_router(telemetry_routes.router, prefix="/api/v1")
app.include_router(analytics_routes.router, prefix="/api/v1")
app.include_router(alerts_routes.router, prefix="/api/v1")
app.include_router(messages_routes.router, prefix="/api/v1")
app.include_router(ai_routes.router, prefix="/api/v1")
app.include_router(fleet_routes.router, prefix="/api/v1")
app.include_router(batch_routes.router, prefix="/api/v1")


# Global exception handlers
@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    logging.warning(f"HTTPException {exc.status_code}: {exc.detail}")
    return JSONResponse(status_code=exc.status_code, content={"detail": exc.detail})


@app.exception_handler(Exception)
async def generic_exception_handler(request: Request, exc: Exception):
    logging.error(f"Unhandled Exception: {exc}")
    return JSONResponse(status_code=500, content={"detail": "Internal Server Error"})
