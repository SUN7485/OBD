import re
import uuid as uuid_lib
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from jose import JWTError, ExpiredSignatureError
from datetime import timedelta, datetime, timezone

from db.session import get_db
from services import auth as auth_service
from api.v1.schemas.auth import (
    LoginRequest,
    TokenResponse,
    RefreshRequest,
    UserResponse,
    RegisterRequest,
)
from middleware.auth import get_current_user
from domain.models import User, Organization, UserRole

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/login", response_model=TokenResponse)
async def login(req: LoginRequest, db: AsyncSession = Depends(get_db)):
    user: User = await auth_service.authenticate_user(db, req.email, req.password)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials"
        )
    # Update last_login_at
    user.last_login_at = datetime.now(timezone.utc)
    db.add(user)
    await db.commit()
    # Token payload
    payload = {
        "user_id": str(user.id),
        "organization_id": str(user.organization_id),
        "role": user.role.value if hasattr(user.role, "value") else user.role,
    }
    access_token = auth_service.create_access_token(payload)
    family_id = uuid_lib.uuid4()
    refresh_token, _ = await auth_service.create_refresh_token_db(
        db, user.id, family_id
    )
    await db.commit()
    return TokenResponse(
        access_token=access_token,
        refresh_token=refresh_token,
        user=UserResponse(
            id=user.id,
            email=user.email,
            full_name=user.full_name,
            role=user.role.value if hasattr(user.role, "value") else user.role,
            organization_id=user.organization_id,
        ),
    )


@router.post("/register", response_model=TokenResponse)
async def register(req: RegisterRequest, db: AsyncSession = Depends(get_db)):
    from sqlalchemy.future import select

    result = await db.execute(select(User).filter(User.email == req.email))
    existing_user = result.scalars().first()
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email already registered",
        )

    slug = re.sub(r"[^a-z0-9-]", "", req.organization_name.lower().replace(" ", "-"))
    if not slug:
        slug = "org-" + str(uuid_lib.uuid4())[:8]

    org = Organization(name=req.organization_name, slug=slug)
    db.add(org)
    await db.flush()

    password_hash = auth_service.get_password_hash(req.password)
    user = User(
        email=req.email,
        password_hash=password_hash,
        full_name=req.full_name,
        organization_id=org.id,
        role=UserRole.admin,
    )
    db.add(user)
    await db.flush()

    payload = {
        "user_id": str(user.id),
        "organization_id": str(user.organization_id),
        "role": user.role.value if hasattr(user.role, "value") else user.role,
    }
    access_token = auth_service.create_access_token(payload)
    family_id = uuid_lib.uuid4()
    refresh_token, _ = await auth_service.create_refresh_token_db(
        db, user.id, family_id
    )
    await db.commit()

    return TokenResponse(
        access_token=access_token,
        refresh_token=refresh_token,
        user=UserResponse(
            id=user.id,
            email=user.email,
            full_name=user.full_name,
            role=user.role.value if hasattr(user.role, "value") else user.role,
            organization_id=user.organization_id,
        ),
    )


@router.post("/refresh", response_model=TokenResponse)
async def refresh(req: RefreshRequest, db: AsyncSession = Depends(get_db)):
    result = await auth_service.rotate_refresh_token(db, req.refresh_token)
    if not result:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or revoked refresh token",
        )
    new_token, _, user = result

    payload = {
        "user_id": str(user.id),
        "organization_id": str(user.organization_id),
        "role": user.role.value if hasattr(user.role, "value") else user.role,
    }
    access_token = auth_service.create_access_token(payload)

    return TokenResponse(
        access_token=access_token,
        refresh_token=new_token,
        user=UserResponse(
            id=user.id,
            email=user.email,
            full_name=user.full_name,
            role=user.role.value if hasattr(user.role, "value") else user.role,
            organization_id=user.organization_id,
        ),
    )


@router.post("/logout")
async def logout(current_user: User = Depends(get_current_user)):
    # If token blacklist is required, implement with Redis here
    # This implementation is a placeholder for stateless JWT logout
    return {"detail": "Logged out successfully"}
