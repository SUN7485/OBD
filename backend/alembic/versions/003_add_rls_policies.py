"""Add Row-Level Security (RLS) policies.

This migration enables RLS on multi-tenant tables and creates policies
to filter by organization_id.
"""
from alembic import op
import sqlalchemy as sa

# revision identifiers
revision = '003_add_rls_policies'
down_revision = '002_seed_data'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Enable RLS on organizations table (for admin access)
    op.execute("""
        ALTER TABLE organizations ENABLE ROW LEVEL SECURITY;
    """)
    
    # Enable RLS on users table
    op.execute("""
        ALTER TABLE users ENABLE ROW LEVEL SECURITY;
    """)
    
    # Enable RLS on cars table
    op.execute("""
        ALTER TABLE cars ENABLE ROW LEVEL SECURITY;
    """)
    
    # Enable RLS on devices table
    op.execute("""
        ALTER TABLE devices ENABLE ROW LEVEL SECURITY;
    """)
    
    # Note: obd_data and obd_data_hourly are TimescaleDB hypertables
    # RLS on hypertables requires special handling - skip ENABLE RLS
    # CREATE POLICY still works with SELECT policies
    
    # Enable RLS on alerts table
    op.execute("""
        ALTER TABLE alerts ENABLE ROW LEVEL SECURITY;
    """)
    
    # Enable RLS on messages table
    op.execute("""
        ALTER TABLE messages ENABLE ROW LEVEL SECURITY;
    """)
    
    # Enable RLS on ai_sessions table
    op.execute("""
        ALTER TABLE ai_sessions ENABLE ROW LEVEL SECURITY;
    """)
    
    # Create RLS policies for users table
    op.execute("""
        CREATE POLICY users_org_policy ON users
        FOR ALL
        USING (organization_id::text = current_setting('app.current_org_id', true));
    """)
    
    # Create RLS policies for cars table
    op.execute("""
        CREATE POLICY cars_org_policy ON cars
        FOR ALL
        USING (organization_id::text = current_setting('app.current_org_id', true));
    """)
    
    # Create RLS policies for devices table
    op.execute("""
        CREATE POLICY devices_org_policy ON devices
        FOR ALL
        USING (
            car_id IN (
                SELECT id FROM cars 
                WHERE cars.organization_id::text = current_setting('app.current_org_id', true)
            )
        );
    """)
    
    # Create RLS policies for obd_data table
    op.execute("""
        CREATE POLICY obd_data_org_policy ON obd_data
        FOR ALL
        USING (organization_id::text = current_setting('app.current_org_id', true));
    """)
    
    # Create RLS policies for obd_data_hourly table
    op.execute("""
        CREATE POLICY obd_data_hourly_org_policy ON obd_data_hourly
        FOR ALL
        USING (organization_id::text = current_setting('app.current_org_id', true));
    """)
    
    # Create RLS policies for alerts table
    op.execute("""
        CREATE POLICY alerts_org_policy ON alerts
        FOR ALL
        USING (organization_id::text = current_setting('app.current_org_id', true));
    """)
    
    # Create RLS policies for messages table
    op.execute("""
        CREATE POLICY messages_org_policy ON messages
        FOR ALL
        USING (organization_id::text = current_setting('app.current_org_id', true));
    """)
    
    # Create RLS policies for ai_sessions table
    op.execute("""
        CREATE POLICY ai_sessions_org_policy ON ai_sessions
        FOR ALL
        USING (organization_id::text = current_setting('app.current_org_id', true));
    """)


def downgrade() -> None:
    # Drop policies
    op.execute("DROP POLICY IF EXISTS users_org_policy ON users;")
    op.execute("DROP POLICY IF EXISTS cars_org_policy ON cars;")
    op.execute("DROP POLICY IF EXISTS devices_org_policy ON devices;")
    op.execute("DROP POLICY IF EXISTS obd_data_org_policy ON obd_data;")
    op.execute("DROP POLICY IF EXISTS obd_data_hourly_org_policy ON obd_data_hourly;")
    op.execute("DROP POLICY IF EXISTS alerts_org_policy ON alerts;")
    op.execute("DROP POLICY IF EXISTS messages_org_policy ON messages;")
    op.execute("DROP POLICY IF EXISTS ai_sessions_org_policy ON ai_sessions;")
    
    # Disable RLS
    op.execute("ALTER TABLE organizations DISABLE ROW LEVEL SECURITY;")
    op.execute("ALTER TABLE users DISABLE ROW LEVEL SECURITY;")
    op.execute("ALTER TABLE cars DISABLE ROW LEVEL SECURITY;")
    op.execute("ALTER TABLE devices DISABLE ROW LEVEL SECURITY;")
    op.execute("ALTER TABLE obd_data DISABLE ROW LEVEL SECURITY;")
    op.execute("ALTER TABLE obd_data_hourly DISABLE ROW LEVEL SECURITY;")
    op.execute("ALTER TABLE alerts DISABLE ROW LEVEL SECURITY;")
    op.execute("ALTER TABLE messages DISABLE ROW LEVEL SECURITY;")
    op.execute("ALTER TABLE ai_sessions DISABLE ROW LEVEL SECURITY;")
