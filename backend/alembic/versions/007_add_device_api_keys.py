"""Add device_api_keys table

Revision ID: 007_add_device_api_keys
Revises: 006_add_refresh_tokens
Create Date: 2026-04-11 13:25:00.000000

"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "007_add_device_api_keys"
down_revision = "006_add_refresh_tokens"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "device_api_keys",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("organization_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("car_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("key_hash", sa.String(255), nullable=False),
        sa.Column("name", sa.String(100), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default="true"),
        sa.Column("last_used_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("idx_device_api_keys_key_hash", "device_api_keys", ["key_hash"])
    op.create_index("idx_device_api_keys_car", "device_api_keys", ["car_id"])
    op.create_index("idx_device_api_keys_org", "device_api_keys", ["organization_id"])
    op.create_foreign_key(
        "fk_device_api_keys_organizations",
        "device_api_keys",
        "organizations",
        ["organization_id"],
        ["id"],
        ondelete="CASCADE",
    )
    op.create_foreign_key(
        "fk_device_api_keys_cars",
        "device_api_keys",
        "cars",
        ["car_id"],
        ["id"],
        ondelete="CASCADE",
    )


def downgrade() -> None:
    op.drop_constraint("fk_device_api_keys_cars", "device_api_keys", type_="foreignkey")
    op.drop_constraint(
        "fk_device_api_keys_organizations", "device_api_keys", type_="foreignkey"
    )
    op.drop_index("idx_device_api_keys_org", table_name="device_api_keys")
    op.drop_index("idx_device_api_keys_car", table_name="device_api_keys")
    op.drop_index("idx_device_api_keys_key_hash", table_name="device_api_keys")
    op.drop_table("device_api_keys")
