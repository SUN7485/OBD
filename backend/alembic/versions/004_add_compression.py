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
    
    # Disable RLS temporarily to allow compression
    op.execute("""
        ALTER TABLE obd_data DISABLE ROW LEVEL SECURITY;
    """)
    
    # Enable compression on obd_data
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
    
    # Re-enable RLS
    op.execute("""
        ALTER TABLE obd_data ENABLE ROW LEVEL SECURITY;
    """)
    
    # Also set up compression on obd_data_hourly
    op.execute("""
        SELECT create_hypertable('obd_data_hourly', 'time',
            if_not_exists => TRUE,
            migrate_data => FALSE
        );
    """)
    
    # Disable RLS temporarily for hourly table
    op.execute("""
        ALTER TABLE obd_data_hourly DISABLE ROW LEVEL SECURITY;
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
    
    # Re-enable RLS for hourly table
    op.execute("""
        ALTER TABLE obd_data_hourly ENABLE ROW LEVEL SECURITY;
    """)


def downgrade() -> None:
    # Disable RLS before removing compression
    op.execute("""
        ALTER TABLE obd_data DISABLE ROW LEVEL SECURITY;
    """)
    
    # Remove compression policies
    op.execute("""
        SELECT remove_compression_policy('obd_data', if_exists => TRUE);
    """)
    
    op.execute("""
        SELECT remove_compression_policy('obd_data_hourly', if_exists => TRUE);
    """)
    
    # Disable compression
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
    
    # Re-enable RLS
    op.execute("""
        ALTER TABLE obd_data ENABLE ROW LEVEL SECURITY;
    """)
    
    op.execute("""
        ALTER TABLE obd_data_hourly ENABLE ROW LEVEL SECURITY;
    """)
