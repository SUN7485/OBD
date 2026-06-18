"""Add TimescaleDB compression policies for obd_data and obd_data_hourly tables.

- Enables native compression on hypertables
- Sets compression segmentby for efficient querying
- Adds 7-day compression policy
- Adds 90-day retention policy (if not exists)
"""

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision = '008_add_compression_policies'
down_revision = '001_initial_schema'
branch_labels = None
depends_on = None


def upgrade():
    # Enable compression and add compression policy for obd_data
    op.execute("""
        ALTER TABLE obd_data SET (
            timescaledb.compress,
            timescaledb.compress_segmentby = 'car_id'
        )
    """)
    op.execute("""
        SELECT add_compression_policy('obd_data', INTERVAL '7 days', if_not_exists => TRUE)
    """)
    
    # Enable compression and add compression policy for obd_data_hourly
    op.execute("""
        ALTER TABLE obd_data_hourly SET (
            timescaledb.compress,
            timescaledb.compress_segmentby = 'car_id'
        )
    """)
    op.execute("""
        SELECT add_compression_policy('obd_data_hourly', INTERVAL '30 days', if_not_exists => TRUE)
    """)
    
    # Ensure retention policy exists
    op.execute("""
        SELECT add_retention_policy('obd_data', INTERVAL '90 days', if_not_exists => TRUE)
    """)


def downgrade():
    op.execute("SELECT remove_compression_policy('obd_data', if_exists => TRUE)")
    op.execute("SELECT remove_compression_policy('obd_data_hourly', if_exists => TRUE)")