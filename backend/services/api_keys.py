import secrets
import uuid
from datetime import datetime, timezone
from typing import Optional

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from ..domain.models import DeviceAPIKey


def generate_api_key() -> str:
    return secrets.token_urlsafe(32)


def hash_api_key(key: str) -> str:
    import hashlib

    return hashlib.sha256(key.encode()).hexdigest()


async def validate_api_key(db: AsyncSession, key: str) -> Optional[DeviceAPIKey]:
    key_hash = hash_api_key(key)
    result = await db.execute(
        select(DeviceAPIKey).filter(
            DeviceAPIKey.key_hash == key_hash, DeviceAPIKey.is_active == True
        )
    )
    return result.scalars().first()


async def update_last_used(db: AsyncSession, key_id: uuid.UUID) -> None:
    result = await db.execute(select(DeviceAPIKey).filter(DeviceAPIKey.id == key_id))
    api_key = result.scalars().first()
    if api_key:
        api_key.last_used_at = datetime.now(timezone.utc)
        await db.flush()
