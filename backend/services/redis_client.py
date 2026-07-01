"""Redis client wrapper with async support for PubSub messaging."""
import json
import asyncio
from typing import Optional, Callable, Any, Dict
import redis.asyncio as redis
from redis.asyncio import Redis
from redis.exceptions import RedisError
import logging

from config.settings import settings
from utils.circuit_breaker import get_redis_breaker, execute_with_circuit_breaker

logger = logging.getLogger(__name__)


class RedisClient:
    """Async Redis client wrapper with PubSub support."""

    def __init__(self):
        self._redis: Optional[Redis] = None
        self._pubsub: Optional[redis.client.PubSub] = None
        self._pubsub_task: Optional[asyncio.Task] = None
        self._handlers: Dict[str, Callable] = {}

    async def connect(self) -> None:
        """Initialize Redis connection."""
        if self._redis is None:
            self._redis = await redis.from_url(
                settings.REDIS_URL,
                encoding="utf-8",
                decode_responses=True
            )
            logger.info("Redis client connected")

    async def disconnect(self) -> None:
        """Close Redis connections."""
        if self._pubsub_task:
            self._pubsub_task.cancel()
            try:
                await self._pubsub_task
            except asyncio.CancelledError:
                pass

        if self._pubsub:
            await self._pubsub.close()

        if self._redis:
            await self._redis.close()
            self._redis = None
            logger.info("Redis client disconnected")

    async def publish(self, channel: str, message: Any) -> int:
        """
        Publish a message to a channel.
        
        Args:
            channel: The channel name to publish to
            message: The message to publish (will be JSON serialized)
            
        Returns:
            Number of subscribers that received the message
        """
        if self._redis is None:
            await self.connect()

        async def _publish():
            serialized = json.dumps(message)
            result = await self._redis.publish(channel, serialized)
            logger.debug(f"Published to {channel}: {message}")
            return result

        try:
            return await execute_with_circuit_breaker(
                get_redis_breaker(),
                _publish,
                fallback=0,
            )
        except RedisError as e:
            logger.error(f"Error publishing to {channel}: {e}")
            raise

    async def subscribe(self, channel: str, handler: Callable[[dict], Any]) -> None:
        """
        Subscribe to a channel with a handler function.
        
        Args:
            channel: The channel name to subscribe to
            handler: Async function to handle received messages
        """
        if self._redis is None:
            await self.connect()

        self._handlers[channel] = handler

        if self._pubsub is None:
            self._pubsub = self._redis.pubsub()
            # Start the listener task
            self._pubsub_task = asyncio.create_task(self._listen())

        await self._pubsub.subscribe(channel)
        logger.info(f"Subscribed to channel: {channel}")

    async def unsubscribe(self, channel: str) -> None:
        """
        Unsubscribe from a channel.
        
        Args:
            channel: The channel name to unsubscribe from
        """
        if self._pubsub:
            await self._pubsub.unsubscribe(channel)
            if channel in self._handlers:
                del self._handlers[channel]
            logger.info(f"Unsubscribed from channel: {channel}")

    async def _listen(self) -> None:
        """Internal: Listen for messages on subscribed channels."""
        try:
            async for message in self._pubsub.listen():
                if message["type"] == "message":
                    channel = message["channel"]
                    try:
                        data = json.loads(message["data"])
                    except json.JSONDecodeError:
                        data = message["data"]

                    if channel in self._handlers:
                        handler = self._handlers[channel]
                        try:
                            if asyncio.iscoroutinefunction(handler):
                                await handler(data)
                            else:
                                handler(data)
                        except Exception as e:
                            logger.error(f"Error in handler for {channel}: {e}")
        except asyncio.CancelledError:
            logger.info("PubSub listener cancelled")
        except Exception as e:
            logger.error(f"Error in pubsub listener: {e}")

    async def get(self, key: str) -> Optional[str]:
        """Get a value by key."""
        if self._redis is None:
            await self.connect()

        async def _get():
            return await self._redis.get(key)

        return await execute_with_circuit_breaker(
            get_redis_breaker(),
            _get,
            fallback=None,
        )

    async def set(self, key: str, value: Any, ex: Optional[int] = None) -> bool:
        """Set a key-value pair with optional expiration."""
        if self._redis is None:
            await self.connect()

        async def _set():
            serialized = json.dumps(value) if not isinstance(value, str) else value
            return await self._redis.set(key, serialized, ex=ex)

        return await execute_with_circuit_breaker(
            get_redis_breaker(),
            _set,
            fallback=False,
        )

    async def delete(self, *keys: str) -> int:
        """Delete one or more keys."""
        if self._redis is None:
            await self.connect()
        return await self._redis.delete(*keys)

    async def incr(self, key: str) -> int:
        """Increment a counter."""
        if self._redis is None:
            await self.connect()
        return await self._redis.incr(key)

    async def expire(self, key: str, seconds: int) -> bool:
        """Set expiration on a key."""
        if self._redis is None:
            await self.connect()
        return await self._redis.expire(key, seconds)

    @property
    def is_connected(self) -> bool:
        """Check if Redis is connected."""
        return self._redis is not None and self._redis.connected


# Global instance
redis_client = RedisClient()
