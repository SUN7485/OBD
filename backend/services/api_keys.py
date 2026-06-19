import secrets
import uuid
from datetime import datetime, timezone
from typing import Optional

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy import func

from domain.models import DeviceAPIKey


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


async def rotate_api_key(db: AsyncSession, key_id: uuid.UUID) -> Optional[str]:
    result = await db.execute(select(DeviceAPIKey).filter(DeviceAPIKey.id == key_id))
    api_key = result.scalars().first()
    if not api_key or not api_key.is_active:
        return None
    new_key = generate_api_key()
    api_key.key_hash = hash_api_key(new_key)
    api_key.updated_at = datetime.now(timezone.utc)
    await db.flush()
    return new_key


async def get_api_key_usage(db: AsyncSession, key_id: uuid.UUID) -> Optional[dict]:
    from domain.models import OBDData
    
    result = await db.execute(select(DeviceAPIKey).filter(DeviceAPIKey.id == key_id))
    api_key = result.scalars().first()
    if not api_key:
        return None
    
    usage_result = await db.execute(
        select(func.count(OBDData.car_id))
        .filter(OBDData.organization_id == api_key.organization_id)
    )
    total_ingested = usage_result.scalar_one()
    return {
        "key_id": str(api_key.id),
        "total_requests": total_ingested,
        "last_used": api_key.last_used_at.isoformat() if api_key.last_used_at else None,
        "is_active": api_key.is_active,
        "created_at": api_key.created_at.isoformat() if api_key.created_at else None,
    }