"""Initial schema for Fleet OBD Platform

- Creates all tables (organizations, users, cars, devices, obd_data, obd_data_hourly, alerts, messages, ai_sessions)
- Sets up TimescaleDB hypertables and retention policies
- Adds indexes for performance and multi-tenant separation
"""

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = '001_initial_schema'
down_revision = None
branch_labels = None
depends_on = None

def upgrade():
    # Enable TimescaleDB extension
    op.execute("CREATE EXTENSION IF NOT EXISTS timescaledb")

    # Organizations
    op.create_table(
        "organizations",
        sa.Column("id", sa.dialects.postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("slug", sa.String(100), nullable=False, unique=True, index=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("settings", sa.dialects.postgresql.JSONB, nullable=True),
        sa.Column("is_active", sa.Boolean, nullable=False, server_default="true"),
    )
    op.create_index("idx_organizations_slug", "organizations", ["slug"])

    # Users
    op.create_table(
        "users",
        sa.Column("id", sa.dialects.postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("organization_id", sa.dialects.postgresql.UUID(as_uuid=True), sa.ForeignKey("organizations.id")),
        sa.Column("email", sa.String(255), nullable=False, unique=True, index=True),
        sa.Column("password_hash", sa.String(255), nullable=False),
        sa.Column("full_name", sa.String(255), nullable=False),
        sa.Column("role", sa.Enum("admin", "fleet_manager", "driver", name="userrole"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("last_login_at", sa.DateTime(timezone=True)),
        sa.Column("is_active", sa.Boolean, nullable=False, server_default="true"),
    )
    op.create_index("idx_users_org", "users", ["organization_id"])
    op.create_index("idx_users_email", "users", ["email"])

    # Cars
    op.create_table(
        "cars",
        sa.Column("id", sa.dialects.postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("organization_id", sa.dialects.postgresql.UUID(as_uuid=True), sa.ForeignKey("organizations.id")),
        sa.Column("vin", sa.String(17), nullable=False, unique=True, index=True),
        sa.Column("license_plate", sa.String(20), nullable=False),
        sa.Column("make", sa.String(100), nullable=False),
        sa.Column("model", sa.String(100), nullable=False),
        sa.Column("year", sa.Integer, nullable=False),
        sa.Column("assigned_driver_id", sa.dialects.postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id"), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("metadata", sa.dialects.postgresql.JSONB, nullable=True),
        sa.Column("is_active", sa.Boolean, nullable=False, server_default="true"),
    )
    op.create_index("idx_cars_org", "cars", ["organization_id"])
    op.create_index("idx_cars_driver", "cars", ["assigned_driver_id"])
    op.create_index("idx_cars_vin", "cars", ["vin"])

    # Devices
    op.create_table(
        "devices",
        sa.Column("id", sa.dialects.postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("car_id", sa.dialects.postgresql.UUID(as_uuid=True), sa.ForeignKey("cars.id")),
        sa.Column("device_type", sa.String(50), nullable=False, server_default="ELM327"),
        sa.Column("mac_address", sa.String(17), nullable=False, unique=True, index=True),
        sa.Column("firmware_version", sa.String(50)),
        sa.Column("last_seen_at", sa.DateTime(timezone=True)),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("is_active", sa.Boolean, nullable=False, server_default="true"),
    )
    op.create_index("idx_devices_car", "devices", ["car_id"])
    op.create_index("idx_devices_mac", "devices", ["mac_address"])

    # OBD Data (Timescale hypertable)
    op.create_table(
        "obd_data",
        sa.Column("time", sa.DateTime(timezone=True), primary_key=True),
        sa.Column("car_id", sa.dialects.postgresql.UUID(as_uuid=True), sa.ForeignKey("cars.id"), primary_key=True),
        sa.Column("organization_id", sa.dialects.postgresql.UUID(as_uuid=True), sa.ForeignKey("organizations.id")),
        sa.Column("rpm", sa.Integer),
        sa.Column("speed", sa.Integer),
        sa.Column("throttle_position", sa.Float),
        sa.Column("engine_load", sa.Float),
        sa.Column("coolant_temp", sa.Integer),
        sa.Column("intake_temp", sa.Integer),
        sa.Column("fuel_level", sa.Float),
        sa.Column("fuel_rate", sa.Float),
        sa.Column("fuel_pressure", sa.Float),
        sa.Column("maf_rate", sa.Float),
        sa.Column("o2_voltage", sa.Float),
        sa.Column("latitude", sa.Numeric(10,6)),
        sa.Column("longitude", sa.Numeric(10,6)),
        sa.Column("dtc_codes", sa.ARRAY(sa.String)),
        sa.Column("mil_status", sa.Boolean),
        sa.Column("raw_data", sa.dialects.postgresql.JSONB, nullable=True),
        sa.UniqueConstraint('time', 'car_id', name="uix_obd_data_time_car")
    )
    op.create_index("idx_obd_data_org_time", "obd_data", ["organization_id", "time"])
    op.create_index("idx_obd_data_car_time", "obd_data", ["car_id", "time"])
    op.create_index("idx_obd_data_dtc", "obd_data", ["dtc_codes"], postgresql_using='gin')
    op.execute("SELECT create_hypertable('obd_data', 'time', chunk_time_interval => INTERVAL '1 day', if_not_exists => TRUE)")
    op.execute("SELECT add_retention_policy('obd_data', INTERVAL '90 days')")

    # OBDDataHourly (Timescale hypertable for hourly aggregation)
    op.create_table(
        "obd_data_hourly",
        sa.Column("time", sa.DateTime(timezone=True), primary_key=True),
        sa.Column("car_id", sa.dialects.postgresql.UUID(as_uuid=True), sa.ForeignKey("cars.id"), primary_key=True),
        sa.Column("organization_id", sa.dialects.postgresql.UUID(as_uuid=True), sa.ForeignKey("organizations.id")),
        sa.Column("avg_rpm", sa.Float),
        sa.Column("avg_speed", sa.Float),
        sa.Column("max_speed", sa.Float),
        sa.Column("avg_throttle", sa.Float),
        sa.Column("avg_engine_load", sa.Float),
        sa.Column("avg_coolant_temp", sa.Float),
        sa.Column("avg_fuel_rate", sa.Float),
        sa.Column("total_distance_km", sa.Numeric(10,3)),
        sa.Column("total_fuel_consumed_l", sa.Numeric(10,3)),
        sa.Column("dtc_count", sa.Integer),
        sa.UniqueConstraint('time', 'car_id', name="uix_obd_data_hourly_time_car")
    )
    op.create_index("idx_obd_hourly_org_time", "obd_data_hourly", ["organization_id", "time"])
    op.execute("SELECT create_hypertable('obd_data_hourly', 'time', chunk_time_interval => INTERVAL '7 days', if_not_exists => TRUE)")

    # Alerts
    op.create_table(
        "alerts",
        sa.Column("id", sa.dialects.postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("organization_id", sa.dialects.postgresql.UUID(as_uuid=True), sa.ForeignKey("organizations.id")),
        sa.Column("car_id", sa.dialects.postgresql.UUID(as_uuid=True), sa.ForeignKey("cars.id")),
        sa.Column("alert_type", sa.Enum("dtc_error", "threshold_exceeded", "maintenance_due", "anomaly_detected", "system", name="alerttype"), nullable=False),
        sa.Column("severity", sa.Enum("info", "warning", "critical", name="alertseverity"), nullable=False),
        sa.Column("title", sa.String(255), nullable=False),
        sa.Column("message", sa.Text),
        sa.Column("metadata", sa.dialects.postgresql.JSONB),
        sa.Column("is_read", sa.Boolean, nullable=False, server_default="false"),
        sa.Column("is_resolved", sa.Boolean, nullable=False, server_default="false"),
        sa.Column("resolved_at", sa.DateTime(timezone=True)),
        sa.Column("resolved_by", sa.dialects.postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id"), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("idx_alerts_org_time", "alerts", ["organization_id", "created_at"])
    op.create_index("idx_alerts_car_time", "alerts", ["car_id", "created_at"])
    op.create_index("idx_alerts_unread", "alerts", ["car_id", "is_read", "is_resolved"])

    # Messages
    op.create_table(
        "messages",
        sa.Column("id", sa.dialects.postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("organization_id", sa.dialects.postgresql.UUID(as_uuid=True), sa.ForeignKey("organizations.id")),
        sa.Column("scope", sa.Enum("car", "organization", name="messagescope"), nullable=False),
        sa.Column("car_id", sa.dialects.postgresql.UUID(as_uuid=True), sa.ForeignKey("cars.id"), nullable=True),
        sa.Column("message_type", sa.Enum("chat", "alert", "command", "ai_reply", "system", name="messagetype"), nullable=False),
        sa.Column("sender_type", sa.Enum("user", "ai", "system", name="sendertype"), nullable=False),
        sa.Column("sender_id", sa.dialects.postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id"), nullable=True),
        sa.Column("content", sa.Text, nullable=False),
        sa.Column("metadata", sa.dialects.postgresql.JSONB),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("idx_messages_org_time", "messages", ["organization_id", "created_at"])
    op.create_index("idx_messages_car_time", "messages", ["car_id", "created_at"])
    op.create_index("idx_messages_type", "messages", ["organization_id", "message_type"])
    # Check constraint for car_id when scope='car'
    op.execute("""
        ALTER TABLE messages
        ADD CONSTRAINT check_car_scope_car_id
        CHECK (
            (scope = 'car' AND car_id IS NOT NULL)
            OR (scope = 'organization' AND car_id IS NULL)
        );
    """)

    # AISessions
    op.create_table(
        "ai_sessions",
        sa.Column("id", sa.dialects.postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("organization_id", sa.dialects.postgresql.UUID(as_uuid=True), sa.ForeignKey("organizations.id")),
        sa.Column("car_id", sa.dialects.postgresql.UUID(as_uuid=True), sa.ForeignKey("cars.id"), nullable=True),
        sa.Column("user_id", sa.dialects.postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id")),
        sa.Column("session_type", sa.Enum("diagnostic", "analysis", "chat", "proactive_alert", name="aisessiontype"), nullable=False),
        sa.Column("prompt", sa.Text),
        sa.Column("response", sa.Text),
        sa.Column("model_used", sa.String(100)),
        sa.Column("tokens_used", sa.Integer),
        sa.Column("processing_time_ms", sa.Integer),
        sa.Column("metadata", sa.dialects.postgresql.JSONB),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("idx_ai_sessions_org_time", "ai_sessions", ["organization_id", "created_at"])
    op.create_index("idx_ai_sessions_car_time", "ai_sessions", ["car_id", "created_at"])

def downgrade():
    # Drop in reverse order
    op.drop_index("idx_ai_sessions_car_time", table_name="ai_sessions")
    op.drop_index("idx_ai_sessions_org_time", table_name="ai_sessions")
    op.drop_table("ai_sessions")

    op.execute("ALTER TABLE messages DROP CONSTRAINT IF EXISTS check_car_scope_car_id;")
    op.drop_index("idx_messages_type", table_name="messages")
    op.drop_index("idx_messages_car_time", table_name="messages")
    op.drop_index("idx_messages_org_time", table_name="messages")
    op.drop_table("messages")

    op.drop_index("idx_alerts_unread", table_name="alerts")
    op.drop_index("idx_alerts_car_time", table_name="alerts")
    op.drop_index("idx_alerts_org_time", table_name="alerts")
    op.drop_table("alerts")

    op.execute("SELECT drop_retention_policy('obd_data')")
    op.execute("SELECT drop_chunks(INTERVAL '0 days', 'obd_data')")
    op.drop_index("idx_obd_data_dtc", table_name="obd_data")
    op.drop_index("idx_obd_data_car_time", table_name="obd_data")
    op.drop_index("idx_obd_data_org_time", table_name="obd_data")
    op.drop_table("obd_data")

    op.drop_index("idx_obd_hourly_org_time", table_name="obd_data_hourly")
    op.drop_table("obd_data_hourly")

    op.drop_index("idx_devices_mac", table_name="devices")
    op.drop_index("idx_devices_car", table_name="devices")
    op.drop_table("devices")

    op.drop_index("idx_cars_vin", table_name="cars")
    op.drop_index("idx_cars_driver", table_name="cars")
    op.drop_index("idx_cars_org", table_name="cars")
    op.drop_table("cars")

    op.drop_index("idx_users_email", table_name="users")
    op.drop_index("idx_users_org", table_name="users")
    op.drop_table("users")

    op.drop_index("idx_organizations_slug", table_name="organizations")
    op.drop_table("organizations")

    op.execute("DROP EXTENSION IF EXISTS timescaledb")