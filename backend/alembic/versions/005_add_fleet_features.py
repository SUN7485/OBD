"""Add new tables for geofencing, driver scoring, maintenance, and fuel anomalies."""
from alembic import op
import sqlalchemy as sa

revision = '005_add_fleet_features'
down_revision = '004_add_compression'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Geofences table
    op.create_table(
        'geofences',
        sa.Column('id', sa.UUID(), primary_key=True),
        sa.Column('organization_id', sa.UUID(), sa.ForeignKey('organizations.id', ondelete='CASCADE'), nullable=False),
        sa.Column('name', sa.String(255), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('geofence_type', sa.String(50), nullable=False),
        sa.Column('geometry', sa.dialects.postgresql.JSONB(), nullable=False),
        sa.Column('is_active', sa.Boolean(), default=True),
        sa.Column('notify_on_entry', sa.Boolean(), default=True),
        sa.Column('notify_on_exit', sa.Boolean(), default=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), onupdate=sa.func.now())
    )
    op.create_index('idx_geofences_org', 'geofences', ['organization_id'])
    
    # Geofence events table
    op.create_table(
        'geofence_events',
        sa.Column('id', sa.UUID(), primary_key=True),
        sa.Column('organization_id', sa.UUID(), sa.ForeignKey('organizations.id', ondelete='CASCADE'), nullable=False),
        sa.Column('geofence_id', sa.UUID(), sa.ForeignKey('geofences.id', ondelete='CASCADE'), nullable=False),
        sa.Column('car_id', sa.UUID(), sa.ForeignKey('cars.id', ondelete='CASCADE'), nullable=False),
        sa.Column('event_type', sa.String(20), nullable=False),
        sa.Column('event_time', sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column('location', sa.dialects.postgresql.JSONB(), nullable=True)
    )
    op.create_index('idx_geofence_events_car_time', 'geofence_events', ['car_id', 'event_time'])
    
    # Maintenance schedules table
    op.create_table(
        'maintenance_schedules',
        sa.Column('id', sa.UUID(), primary_key=True),
        sa.Column('organization_id', sa.UUID(), sa.ForeignKey('organizations.id', ondelete='CASCADE'), nullable=False),
        sa.Column('car_id', sa.UUID(), sa.ForeignKey('cars.id', ondelete='CASCADE'), nullable=False),
        sa.Column('maintenance_type', sa.String(50), nullable=False),
        sa.Column('status', sa.String(50), default='scheduled'),
        sa.Column('scheduled_date', sa.DateTime(timezone=True), nullable=False),
        sa.Column('completed_date', sa.DateTime(timezone=True), nullable=True),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('estimated_cost', sa.Numeric(10, 2), nullable=True),
        sa.Column('actual_cost', sa.Numeric(10, 2), nullable=True),
        sa.Column('notes', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now())
    )
    op.create_index('idx_maintenance_car', 'maintenance_schedules', ['car_id'])
    op.create_index('idx_maintenance_status', 'maintenance_schedules', ['status'])
    
    # Maintenance predictions table
    op.create_table(
        'maintenance_predictions',
        sa.Column('id', sa.UUID(), primary_key=True),
        sa.Column('organization_id', sa.UUID(), sa.ForeignKey('organizations.id', ondelete='CASCADE'), nullable=False),
        sa.Column('car_id', sa.UUID(), sa.ForeignKey('cars.id', ondelete='CASCADE'), nullable=False),
        sa.Column('maintenance_type', sa.String(50), nullable=False),
        sa.Column('predicted_days_until_failure', sa.Integer(), nullable=False),
        sa.Column('confidence_score', sa.Float(), nullable=False),
        sa.Column('reasoning', sa.Text(), nullable=True),
        sa.Column('is_active', sa.Boolean(), default=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now())
    )
    op.create_index('idx_predictions_car', 'maintenance_predictions', ['car_id'])
    
    # Driver scores table
    op.create_table(
        'driver_scores',
        sa.Column('id', sa.UUID(), primary_key=True),
        sa.Column('user_id', sa.UUID(), sa.ForeignKey('users.id', ondelete='CASCADE'), nullable=False),
        sa.Column('organization_id', sa.UUID(), sa.ForeignKey('organizations.id', ondelete='CASCADE'), nullable=False),
        sa.Column('period_start', sa.DateTime(timezone=True), nullable=False),
        sa.Column('period_end', sa.DateTime(timezone=True), nullable=False),
        sa.Column('overall_score', sa.Float(), nullable=False),
        sa.Column('safety_score', sa.Float(), nullable=False),
        sa.Column('efficiency_score', sa.Float(), nullable=False),
        sa.Column('total_trips', sa.Integer(), default=0),
        sa.Column('total_distance_km', sa.Numeric(10, 2), default=0),
        sa.Column('harsh_braking_count', sa.Integer(), default=0),
        sa.Column('harsh_acceleration_count', sa.Integer(), default=0),
        sa.Column('speeding_violations', sa.Integer(), default=0),
        sa.Column('idle_time_minutes', sa.Integer(), default=0),
        sa.Column('fuel_consumed_l', sa.Numeric(10, 2), default=0),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now())
    )
    op.create_index('idx_driver_scores_user', 'driver_scores', ['user_id'])
    op.create_index('uix_driver_score_period', 'driver_scores', ['user_id', 'period_start'], unique=True)
    
    # Fuel anomalies table
    op.create_table(
        'fuel_anomalies',
        sa.Column('id', sa.UUID(), primary_key=True),
        sa.Column('organization_id', sa.UUID(), sa.ForeignKey('organizations.id', ondelete='CASCADE'), nullable=False),
        sa.Column('car_id', sa.UUID(), sa.ForeignKey('cars.id', ondelete='CASCADE'), nullable=False),
        sa.Column('anomaly_type', sa.String(50), nullable=False),
        sa.Column('severity', sa.String(20), nullable=False),
        sa.Column('detected_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column('expected_fuel_l', sa.Numeric(10, 2), nullable=True),
        sa.Column('actual_fuel_l', sa.Numeric(10, 2), nullable=True),
        sa.Column('anomaly_value_l', sa.Numeric(10, 2), nullable=True),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('is_investigated', sa.Boolean(), default=False),
        sa.Column('is_confirmed', sa.Boolean(), default=False),
        sa.Column('notes', sa.Text(), nullable=True)
    )
    op.create_index('idx_fuel_anomalies_car', 'fuel_anomalies', ['car_id'])


def downgrade() -> None:
    op.drop_table('fuel_anomalies')
    op.drop_table('driver_scores')
    op.drop_table('maintenance_predictions')
    op.drop_table('maintenance_schedules')
    op.drop_table('geofence_events')
    op.drop_table('geofences')
