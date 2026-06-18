import hashlib
import uuid
from datetime import datetime, timedelta, timezone
from typing import Optional
from jose import jwt, JWTError
from passlib.context import CryptContext
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from ..config.settings import settings
from ..domain.models import User, RefreshToken

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

REFRESH_TOKEN_EXPIRE_DAYS = settings.REFRESH_TOKEN_EXPIRE_DAYS


def _hash_token(token: str) -> str:
    return hashlib.sha256(token.encode()).hexdigest()


async def create_refresh_token_db(
    db: AsyncSession, user_id: uuid.UUID, family_id: uuid.UUID
) -> tuple[str, RefreshToken]:
    payload = {
        "user_id": str(user_id),
        "family_id": str(family_id),
    }
    expire = datetime.now(timezone.utc) + timedelta(days=REFRESH_TOKEN_EXPIRE_DAYS)
    to_encode = payload.copy()
    to_encode.update({"exp": expire, "type": "refresh"})
    token = jwt.encode(to_encode, settings.JWT_SECRET, algorithm=settings.JWT_ALGORITHM)

    token_record = RefreshToken(
        user_id=user_id,
        token_hash=_hash_token(token),
        family_id=family_id,
        expires_at=expire,
    )
    db.add(token_record)
    return token, token_record


async def rotate_refresh_token(
    db: AsyncSession, old_token: str
) -> tuple[str, uuid.UUID, User] | None:
    try:
        payload = jwt.decode(
            old_token, settings.JWT_SECRET, algorithms=[settings.JWT_ALGORITHM]
        )
    except JWTError:
        return None

    if payload.get("type") != "refresh":
        return None

    user_id = uuid.UUID(payload["user_id"])
    family_id = uuid.UUID(payload["family_id"])

    token_hash = _hash_token(old_token)
    result = await db.execute(
        select(RefreshToken).filter(
            RefreshToken.token_hash == token_hash,
            RefreshToken.family_id == family_id,
        )
    )
    old_token_record = result.scalars().first()
    if (
        not old_token_record
        or old_token_record.is_revoked
        or old_token_record.expires_at < datetime.now(timezone.utc)
    ):
        return None

    result_user = await db.execute(select(User).filter(User.id == user_id))
    user = result_user.scalars().first()
    if not user:
        return None

    old_token_record.is_revoked = True

    new_token, new_token_record = await create_refresh_token_db(db, user_id, family_id)

    await db.commit()

    return new_token, new_token_record.id, user


async def revoke_token_family(db: AsyncSession, family_id: uuid.UUID) -> int:
    result = await db.execute(
        select(RefreshToken).filter(
            RefreshToken.family_id == family_id,
            RefreshToken.is_revoked == False,
        )
    )
    tokens = result.scalars().all()
    count = 0
    for token in tokens:
        token.is_revoked = True
        count += 1
    if count > 0:
        await db.commit()
    return count


def verify_password(plain_password: str, hashed_password: str) -> bool:
    return pwd_context.verify(plain_password, hashed_password)


def get_password_hash(password: str) -> str:
    return pwd_context.hash(password)


def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    to_encode = data.copy()
    expire = datetime.now(timezone.utc) + (
        expires_delta or timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    )
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(
        to_encode, settings.JWT_SECRET, algorithm=settings.JWT_ALGORITHM
    )
    return encoded_jwt


def create_refresh_token(data: dict) -> str:
    expire = datetime.now(timezone.utc) + timedelta(
        days=settings.REFRESH_TOKEN_EXPIRE_DAYS
    )
    to_encode = data.copy()
    to_encode.update({"exp": expire, "type": "refresh"})
    encoded_jwt = jwt.encode(
        to_encode, settings.JWT_SECRET, algorithm=settings.JWT_ALGORITHM
    )
    return encoded_jwt


async def authenticate_user(
    db: AsyncSession, email: str, password: str
) -> Optional[User]:
    result = await db.execute(select(User).filter(User.email == email))
    user: Optional[User] = result.scalars().first()
    if user and verify_password(password, user.password_hash):
        return user
    return None


def decode_token(token: str) -> dict:
    try:
        payload = jwt.decode(
            token, settings.JWT_SECRET, algorithms=[settings.JWT_ALGORITHM]
        )
        return payload
    except JWTError as e:
        raise e
