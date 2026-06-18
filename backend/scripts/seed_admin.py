import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from passlib.hash import bcrypt
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.db.session import AsyncSessionLocal, engine
from backend.db.models import User, Organization


async def seed_admin():
    await engine.dispose()
    async with AsyncSessionLocal() as session:
        result = await session.execute(
            select(User).where(User.email == "admin@fleet.com")
        )
        existing = result.scalar_one_or_none()

        if existing:
            print("Admin user already exists")
            return

        result = await session.execute(
            select(Organization).where(Organization.name == "My Fleet")
        )
        org = result.scalar_one_or_none()

        if not org:
            org = Organization(name="My Fleet")
            session.add(org)
            await session.flush()

        admin = User(
            email="admin@fleet.com",
            hashed_password=bcrypt.hash("AdminPass1"),
            full_name="Admin User",
            role="fleet_manager",
            organization_id=org.id,
        )
        session.add(admin)
        await session.commit()
        print("Created admin@fleet.com / AdminPass1")


if __name__ == "__main__":
    asyncio.run(seed_admin())
