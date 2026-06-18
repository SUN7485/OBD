import pytest
import uuid
from sqlalchemy.exc import IntegrityError
from sqlalchemy import select
from ..domain.models import Organization, User, Car
from ..services.auth import get_password_hash, verify_password

@pytest.mark.asyncio
async def test_create_organization(db_session):
    org = Organization(
        id=uuid.uuid4(),
        name="Test Org",
        slug="test-org"
    )
    db_session.add(org)
    await db_session.commit()
    stmt = select(Organization).where(Organization.slug == "test-org")
    res = await db_session.execute(stmt)
    found = res.scalar_one()
    assert found.name == "Test Org"

@pytest.mark.asyncio
async def test_create_user_and_password(db_session):
    pwd_hash = get_password_hash("secretpass")
    org = Organization(id=uuid.uuid4(), name="Hash Org", slug="hash-org")
    user = User(
        id=uuid.uuid4(),
        organization=org,
        email="user@example.com",
        password_hash=pwd_hash,
        full_name="Full Name",
        role="admin"
    )
    db_session.add_all([org, user])
    await db_session.commit()
    stmt = select(User).where(User.email == "user@example.com")
    res = await db_session.execute(stmt)
    found = res.scalar_one()
    assert verify_password("secretpass", found.password_hash)
    assert found.organization.slug == "hash-org"

@pytest.mark.asyncio
async def test_create_car_with_relationships(db_session):
    org = Organization(id=uuid.uuid4(), name="COrg", slug="corg")
    user = User(
        id=uuid.uuid4(), organization=org, email="caru@example.com",
        password_hash=get_password_hash("pw"), full_name="Car Owner", role="driver"
    )
    car = Car(
        id=uuid.uuid4(),
        organization=org,
        vin="X1111111111111111",
        license_plate="PLATE1",
        make="Brand",
        model="Model",
        year=2022,
        assigned_driver=user
    )
    db_session.add_all([org, user, car])
    await db_session.commit()

    stmt = select(Car).where(Car.vin == "X1111111111111111")
    res = await db_session.execute(stmt)
    found = res.scalar_one()
    assert found.assigned_driver.email == "caru@example.com"
    assert found.organization.slug == "corg"

@pytest.mark.asyncio
async def test_unique_constraints(db_session):
    org = Organization(id=uuid.uuid4(), name="UOrg", slug="uorg")
    u1 = User(
        id=uuid.uuid4(), organization=org, email="unique@example.com",
        password_hash=get_password_hash("pw1"), full_name="U1", role="admin"
    )
    u2 = User(
        id=uuid.uuid4(), organization=org, email="unique@example.com",
        password_hash=get_password_hash("pw2"), full_name="U2", role="driver"
    )
    db_session.add_all([org, u1, u2])
    with pytest.raises(IntegrityError):
        await db_session.commit()
        await db_session.rollback()

    c1 = Car(
        id=uuid.uuid4(),
        organization=org,
        vin="X2222222222222222",
        license_plate="PLATE2",
        make="Make",
        model="Model",
        year=2022
    )
    c2 = Car(
        id=uuid.uuid4(),
        organization=org,
        vin="X2222222222222222",
        license_plate="PLATE3",
        make="Brand",
        model="Model",
        year=2021
    )
    db_session.add_all([c1, c2])
    with pytest.raises(IntegrityError):
        await db_session.commit()
        await db_session.rollback()