"""Add TimescaleDB performance tuning for telemetry scale: chunk interval, compression, refresh policies."""

from alembic import op

revision = "009_tune_timescale_for_scale"
down_revision = "008_add_compression_policies"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("""
        DO $$
        BEGIN
            IF NOT EXISTS (
                SELECT 1 FROM timescaledb_information.hypertables
                WHERE hypertable_name = 'obd_data'
            ) THEN
                RETURN;
            END IF;
        END;
        $$;
    """)

    op.execute("""
        SELECT add_compression_policy(
            'obd_data',
            INTERVAL '7 days',
            if_not_exists => TRUE
        )
    """)

    op.execute("""
        SELECT add_retention_policy(
            'obd_data',
            INTERVAL '90 days',
            if_not_exists => TRUE
        )
    """)


def downgrade() -> None:
    op.execute(
        "SELECT remove_retention_policy('obd_data', if_exists => TRUE)"
    )
    op.execute(
        "SELECT remove_compression_policy('obd_data', if_exists => TRUE)"
    )