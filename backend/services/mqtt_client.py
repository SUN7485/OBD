"""Async MQTT client wrapper for EMQX broker integration."""
import asyncio
import json
import logging
import uuid
from datetime import datetime, timezone
from typing import Optional, Any
from urllib.parse import urlparse

from gmqtt import Client as MQTTClient

from config.settings import settings
from services.telemetry import TelemetryService
from db.session import AsyncSessionLocal
from services.redis_client import redis_client
from domain.models import OBDData

logger = logging.getLogger(__name__)


class MQTTClientWrapper:
    """Async MQTT client with reconnection and message handling."""

    def __init__(self):
        self._client: Optional[MQTTClient] = None
        self._connected_event: asyncio.Event = asyncio.Event()
        self._reconnect_task: Optional[asyncio.Task] = None
        self._reconnect_delay: float = 1.0
        self._max_reconnect_delay: float = 60.0
        self._car_org_cache: dict = {}

    def _on_connect(self, client: MQTTClient, flags: int, rc: int, properties: Any) -> None:
        logger.info(f"MQTT connected with result code: {rc}")
        self._connected_event.set()
        self._reconnect_delay = 1.0

    def _on_disconnect(self, client: MQTTClient, packet: Any, exc: Optional[Exception] = None) -> None:
        logger.warning(f"MQTT disconnected: {exc}")
        self._connected_event.clear()
        if self._reconnect_task is not None and not self._reconnect_task.done():
            self._reconnect_task.cancel()
            try:
                # await cancelled task to let it cleanup; ignore CancelledError
                loop = asyncio.get_event_loop()
                if loop.is_running():
                    # Already in running loop (gmqtt callback may run in event loop thread)
                    self._reconnect_task = asyncio.ensure_future(self._reconnect_loop())
                else:
                    self._reconnect_task = asyncio.create_task(self._reconnect_loop())
            except Exception:
                self._reconnect_task = asyncio.create_task(self._reconnect_loop())
        else:
            self._reconnect_task = asyncio.create_task(self._reconnect_loop())

    async def _on_message(
        self, client: MQTTClient, topic: str, payload: bytes, qos: int, properties: Any
    ) -> int:
        await self._handle_message(topic, payload)
        return 0

    def _on_subscribe(self, client: MQTTClient, mid: int, qos: int, properties: Any) -> None:
        logger.info(f"MQTT subscription confirmed mid={mid} qos={qos}")

    def _on_unsubscribe(self, client: MQTTClient, mid: int, properties: Any) -> None:
        logger.info(f"MQTT unsubscription confirmed mid={mid}")

    async def _handle_message(self, topic: str, payload: bytes) -> None:
        try:
            data = json.loads(payload.decode("utf-8"))
        except (json.JSONDecodeError, UnicodeDecodeError) as e:
            logger.error(f"Failed to parse MQTT message on {topic}: {e}")
            return

        await self._route_message(topic, data)

    async def _route_message(self, topic: str, data: dict) -> None:
        car_id = self._extract_car_id(topic)
        if not car_id:
            logger.warning(f"Could not extract car_id from topic: {topic}")
            return

        org_id = await self._load_car_organization(car_id)
        if not org_id:
            logger.warning(f"Car {car_id} not found or has no organization")
            return

        if not data.get("source_message_id"):
            data["source_message_id"] = OBDData.make_message_id(
                car_id=car_id,
                time=datetime.fromisoformat(data["time"]) if data.get("time") else datetime.now(timezone.utc),
            )

        seen_key = data["source_message_id"]
        cache_key = f"mqtt:msg:{car_id}:{seen_key}"
        if settings.ENVIRONMENT != "testing":
            try:
                already_known = await redis_client.set(cache_key, "1", ex=3600, nx=True) != True
            except Exception as e:
                logger.debug("Dedup check failed, continuing without dedup: %s", e)
                already_known = False
            if already_known:
                logger.debug("Duplicate MQTT message dropped: %s", cache_key)
                return

        async with AsyncSessionLocal() as session:
            service = TelemetryService(session)
            try:
                await service.ingest_mqtt_reading(car_id, org_id, data)
                await self._broadcast_to_websocket(car_id, data)
            except Exception as e:
                logger.error(f"Error processing MQTT message for car {car_id}: {e}")
                raise

    async def _broadcast_to_websocket(self, car_id: uuid.UUID, data: dict) -> None:
        from services.websocket_manager import manager

        message = {
            "type": "telemetry",
            "car_id": str(car_id),
            "data": data,
        }
        await manager.broadcast_to_car(car_id, message)

    def _extract_car_id(self, topic: str) -> Optional[uuid.UUID]:
        parts = topic.split("/")
        if len(parts) >= 2:
            try:
                return uuid.UUID(parts[1])
            except (ValueError, TypeError):
                pass
        return None

    async def _load_car_organization(self, car_id: uuid.UUID) -> Optional[uuid.UUID]:
        if car_id in self._car_org_cache:
            return self._car_org_cache[car_id]

        from sqlalchemy import select
        from domain.models import Car

        async with AsyncSessionLocal() as session:
            result = await session.execute(
                select(Car.organization_id).where(Car.id == car_id)
            )
            org_id = result.scalar_one_or_none()
            if org_id:
                self._car_org_cache[car_id] = org_id
            return org_id

    def _parse_mqtt_url(self) -> tuple:
        """Parse MQTT_URL for host and port.
        
        Supports:
        - mqtt://host:port (native MQTT)
        - mqtts://host:port (MQTT over TLS)  
        - ws://host:port/mqtt or wss://host:port/mqtt (WebSocket MQTT)
        """
        url = settings.MQTT_URL
        
        # Handle WebSocket URLs
        if url.startswith("ws://") or url.startswith("wss://"):
            parsed = urlparse(url)
            host = parsed.hostname or "localhost"
            # EMQX WS MQTT uses path /mqtt, default port 8083
            port = parsed.port or 8083
            return host, port
        
        # Native MQTT URLs
        parsed = urlparse(url)
        host = parsed.hostname or "localhost"
        port = parsed.port or 1883
        if url.startswith("mqtts://"):
            port = parsed.port or 8883
        return host, port

    async def connect(self) -> None:
        if self._connected_event.is_set():
            return

        client_id = f"fleet-obd-{uuid.uuid4().hex[:8]}"
        self._client = MQTTClient(client_id)

        host, port = self._parse_mqtt_url()

        if settings.MQTT_USERNAME:
            self._client.set_auth_credentials(
                settings.MQTT_USERNAME, settings.MQTT_PASSWORD or ""
            )

        self._client.on_connect = self._on_connect
        self._client.on_disconnect = self._on_disconnect
        self._client.on_message = self._on_message
        self._client.on_subscribe = self._on_subscribe
        self._client.on_unsubscribe = self._on_unsubscribe

        try:
            # gmqtt uses synchronous connect with callbacks
            await self._client.connect(host, port, keepalive=60)
            await asyncio.wait_for(self._connected_event.wait(), timeout=10.0)
            self._subscribe_topics()
        except asyncio.TimeoutError:
            logger.error("MQTT connection timeout")
            raise
        except Exception as e:
            logger.error(f"MQTT connection failed: {e}")
            self._client = None
            raise

    def _subscribe_topics(self) -> None:
        if self._client is None or not self._connected_event.is_set():
            return

        topics = ["telemetry/#", "obd/#"]
        for topic in topics:
            self._client.subscribe(topic, qos=1)
        logger.info(f"MQTT subscribed to topics: {topics}")

    async def _reconnect_loop(self) -> None:
        while not self._connected_event.is_set():
            try:
                await asyncio.sleep(self._reconnect_delay)
                logger.info(f"Attempting MQTT reconnection in {self._reconnect_delay}s")
                await self.connect()
                self._reconnect_delay = min(
                    self._reconnect_delay * 2, self._max_reconnect_delay
                )
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"MQTT reconnection attempt failed: {e}")
                self._reconnect_delay = min(
                    self._reconnect_delay * 2, self._max_reconnect_delay
                )

    async def disconnect(self) -> None:
        if self._reconnect_task and not self._reconnect_task.done():
            self._reconnect_task.cancel()
            try:
                await self._reconnect_task
            except asyncio.CancelledError:
                pass

        if self._client:
            try:
                disconnect = self._client.disconnect
                if disconnect and callable(disconnect):
                    result = disconnect()
                    if result and hasattr(result, '__await__'):
                        await result
            except Exception:
                pass
            self._client = None

        self._connected_event.clear()
        logger.info("MQTT client disconnected")

    @property
    def is_connected(self) -> bool:
        return self._connected_event.is_set()


mqtt_client = MQTTClientWrapper()