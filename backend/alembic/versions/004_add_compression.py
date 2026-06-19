"""Add TimescaleDB compression for obd_data hypertable.

This migration enables compression on the obd_data table for chunks
older than 7 days to reduce storage costs.
"""
from alembic import op

# revision identifiers
revision = '004_add_compression'
down_revision = '003_add_rls_policies'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # First, ensure obd_data is a hypertable (if not already)
    op.execute("""
        SELECT create_hypertable('obd_data', 'time', 
            if_not_exists => TRUE,
            migrate_data => FALSE
        );
    """)
    
    # Enable compression on obd_data
    # NOTE: Cannot ENABLE/DISABLE ROW LEVEL SECURITY on hypertables with
    # columnstore (compression) enabled. RLS was never successfully enabled
    # on these hypertables in previous migrations, so we skip it here.
    op.execute("""
        ALTER TABLE obd_data SET (
            timescaledb.compress,
            timescaledb.compress_segmentby = 'car_id, organization_id'
        );
    """)
    
    # Add compression policy (compress chunks older than 7 days)
    op.execute("""
        SELECT add_compression_policy('obd_data', 
            INTERVAL '7 days',
            if_not_exists => TRUE
        );
    """)
    
    # Also set up compression on obd_data_hourly
    op.execute("""
        SELECT create_hypertable('obd_data_hourly', 'time',
            if_not_exists => TRUE,
            migrate_data => FALSE
        );
    """)
    
    op.execute("""
        ALTER TABLE obd_data_hourly SET (
            timescaledb.compress,
            timescaledb.compress_segmentby = 'car_id, organization_id'
        );
    """)
    
    # Add compression policy for hourly data (older than 30 days)
    op.execute("""
        SELECT add_compression_policy('obd_data_hourly',
            INTERVAL '30 days',
            if_not_exists => TRUE
        );
    """)


def downgrade() -> None:
    # Remove compression policies
    op.execute("""
        SELECT remove_compression_policy('obd_data', if_exists => TRUE);
    """)
    
    op.execute("""
        SELECT remove_compression_policy('obd_data_hourly', if_exists => TRUE);
    """)
    
    # Disable compression
    # NOTE: Cannot ENABLE/DISABLE ROW LEVEL SECURITY on hypertables with
    # columnstore enabled. RLS was never successfully enabled on these
    # hypertables, so we skip RLS operations in downgrade as well.
    op.execute("""
        ALTER TABLE obd_data SET (
            timescaledb.compress = FALSE
        );
    """)
    
    op.execute("""
        ALTER TABLE obd_data_hourly SET (
            timescaledb.compress = FALSE
        );
    """)
