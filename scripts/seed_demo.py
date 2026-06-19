#!/usr/bin/env python3
"""
Fleet OBD Demo Data Seeder
Creates demo organization, cars, and 30 days of telemetry data.
"""

import asyncio
import random
from datetime import datetime, timedelta, timezone
from uuid import uuid4

DATABASE_URL = "postgresql+asyncpg://fleet_user:password@localhost:5432/fleet_obd"


async def seed():
    try:
        from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
        from sqlalchemy.orm import sessionmaker
        from backend.domain.models import Base, Organization, User, Car, Telemetry
    except ImportError:
        print("Error: Run from backend directory or install dependencies first")
        return

    engine = create_async_engine(DATABASE_URL, echo=False)
    async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    print("Creating demo data...")

    async with async_session() as session:
        # Create organization
        org = Organization(
            id=str(uuid4()),
            name="Demo Fleet Company",
            created_at=datetime.now(timezone.utc),
        )
        session.add(org)

        # Create admin user
        admin = User(
            id=str(uuid4()),
            email="admin@demo.com",
            full_name="Demo Admin",
            organization_id=org.id,
            role="admin",
            hashed_password="$2b$12$dummy_hash",
            created_at=datetime.now(timezone.utc),
        )
        session.add(admin)

        await session.commit()

        # Create 10 demo cars
        makes = ["Toyota", "Honda", "Ford", "Chevrolet", "Tesla"]
        models = ["Camry", "Civic", "F-150", "Silverado", "Model 3"]

        cars = []
        for i in range(10):
            car = Car(
                id=str(uuid4()),
                name=f"Vehicle {i + 1}",
                make=random.choice(makes),
                model=random.choice(models),
                year=random.randint(2018, 2024),
                vin=f"VIN{str(uuid4())[:17]}",
                license_plate=f"ABC{100 + i}",
                status="online",
                organization_id=org.id,
                created_at=datetime.now(timezone.utc),
            )
            session.add(car)
            cars.append(car)

        await session.commit()

        # Generate 30 days of telemetry
        print("Generating 30 days of telemetry data...")
        base_time = datetime.now(timezone.utc) - timedelta(days=30)

        for car in cars:
            for day in range(30):
                for hour in range(24):
                    # Generate realistic telemetry
                    timestamp = base_time + timedelta(days=day, hours=hour)

                    # Simulate driving patterns
                    if 6 <= hour <= 9 or 17 <= hour <= 19:
                        # Rush hour - higher activity
                        speed = random.uniform(30, 100)
                        rpm = random.uniform(1500, 3500)
                    elif 22 <= hour <= 5:
                        # Night - low activity
                        speed = random.uniform(0, 20)
                        rpm = random.uniform(800, 1200)
                    else:
                        speed = random.uniform(0, 80)
                        rpm = random.uniform(1000, 2500)

                    telemetry = Telemetry(
                        id=str(uuid4()),
                        car_id=car.id,
                        speed=speed,
                        rpm=rpm,
                        coolant_temp=random.uniform(80, 100),
                        engine_load=random.uniform(10, 40),
                        throttle=random.uniform(5, 30),
                        fuel_level=random.uniform(30, 90),
                        latitude=40.7128 + random.uniform(-0.1, 0.1),
                        longitude=-74.0060 + random.uniform(-0.1, 0.1),
                        timestamp=timestamp,
                    )
                    session.add(telemetry)

        await session.commit()
        print(
            f"Created demo data: 1 org, {len(cars)} cars, 720 telemetry points per car"
        )

    await engine.dispose()


if __name__ == "__main__":
    asyncio.run(seed())
