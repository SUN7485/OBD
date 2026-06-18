"""Seed data for Fleet OBD Platform:

- Inserts test organization, users, and cars
"""

from alembic import op
import sqlalchemy as sa
import uuid
from datetime import datetime
from passlib.hash import bcrypt

# revision identifiers, used by Alembic.
revision = '002_seed_data'
down_revision = '001_initial_schema'
branch_labels = None
depends_on = None

def upgrade():
    conn = op.get_bind()

    org_id = str(uuid.uuid4())
    admin_id = str(uuid.uuid4())
    manager_id = str(uuid.uuid4())
    car1_id = str(uuid.uuid4())
    car2_id = str(uuid.uuid4())
    car3_id = str(uuid.uuid4())

    # Insert organization
    conn.execute(
        sa.text("""
        INSERT INTO organizations (id, name, slug, created_at, updated_at, settings, is_active)
        VALUES (:id, :name, :slug, :created, :updated, '{}'::jsonb, true)
        """), dict(
            id=org_id,
            name="Test Fleet",
            slug="test-fleet",
            created=datetime.utcnow(),
            updated=datetime.utcnow(),
        )
    )

    # Insert users
    conn.execute(
        sa.text("""
        INSERT INTO users (id, organization_id, email, password_hash, full_name, role, created_at, updated_at, is_active)
        VALUES (:id, :org, :email, :pwd, :name, :role, :created, :updated, true)
        """),
        [
            dict(
                id=admin_id,
                org=org_id,
                email="admin@test.com",
                pwd=bcrypt.hash("admin123"),
                name="System Admin",
                role="admin",
                created=datetime.utcnow(),
                updated=datetime.utcnow(),
            ),
            dict(
                id=manager_id,
                org=org_id,
                email="manager@test.com",
                pwd=bcrypt.hash("manager123"),
                name="Fleet Manager",
                role="fleet_manager",
                created=datetime.utcnow(),
                updated=datetime.utcnow(),
            )
        ]
    )

    # Insert cars
    conn.execute(
        sa.text("""
        INSERT INTO cars (id, organization_id, vin, license_plate, make, model, year, assigned_driver_id, created_at, updated_at, metadata, is_active)
        VALUES (:id, :org, :vin, :plate, :make, :model, :year, :driver, :created, :updated, '{}'::jsonb, true)
        """),
        [
            dict(
                id=car1_id,
                org=org_id,
                vin="1HGBH41JXMN109186",
                plate="TEST-001",
                make="Toyota",
                model="Camry",
                year=2020,
                driver=admin_id,
                created=datetime.utcnow(),
                updated=datetime.utcnow(),
            ),
            dict(
                id=car2_id,
                org=org_id,
                vin="2HGBH41JXMN109187",
                plate="TEST-002",
                make="Honda",
                model="Civic",
                year=2021,
                driver=manager_id,
                created=datetime.utcnow(),
                updated=datetime.utcnow(),
            ),
            dict(
                id=car3_id,
                org=org_id,
                vin="3HGBH41JXMN109188",
                plate="TEST-003",
                make="Ford",
                model="F-150",
                year=2019,
                driver=None,
                created=datetime.utcnow(),
                updated=datetime.utcnow(),
            ),
        ]
    )

def downgrade():
    conn = op.get_bind()
    conn.execute("DELETE FROM cars")
    conn.execute("DELETE FROM users")
    conn.execute("DELETE FROM organizations")