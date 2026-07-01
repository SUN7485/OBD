"""Add idempotency_key and source_message_id to obd_data for deduplication.

Revision ID: 009
Revises: 009_tune_timescale_for_scale
"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "009"
down_revision: Union[str, None] = "009_tune_timescale_for_scale"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "obd_data",
        sa.Column("idempotency_key", sa.String(length=64), nullable=True),
    )
    op.add_column(
        "obd_data",
        sa.Column("source_message_id", sa.String(length=128), nullable=True),
    )
    op.create_index(
        "idx_obd_data_idempotency_key",
        "obd_data",
        ["idempotency_key"],
        unique=False,
    )
    op.create_index(
        "idx_obd_data_source_msg",
        "obd_data",
        ["car_id", "source_message_id"],
        unique=False,
    )
    # Note: TimescaleDB hypertables require the partitioning column in unique constraints.
    # Deduplication is handled at the application layer via idempotency key checks
    # instead of a DB-level unique constraint on car_id + source_message_id.


def downgrade() -> None:
    op.drop_index("idx_obd_data_source_msg", table_name="obd_data")
    op.drop_index("idx_obd_data_idempotency_key", table_name="obd_data")
    op.drop_column("obd_data", "source_message_id")
    op.drop_column("obd_data", "idempotency_key")