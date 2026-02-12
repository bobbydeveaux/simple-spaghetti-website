"""Initial F1 Analytics Schema

Revision ID: 001
Revises:
Create Date: 2026-02-12 15:55:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision = '001'
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Create all F1 Analytics database tables and indexes."""

    # Create teams table
    op.create_table(
        'teams',
        sa.Column('team_id', sa.Integer(), nullable=False),
        sa.Column('team_name', sa.String(length=100), nullable=False),
        sa.Column('nationality', sa.String(length=50), nullable=True),
        sa.Column('current_elo_rating', sa.Integer(), nullable=True, default=1500),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.text('NOW()')),
        sa.Column('updated_at', sa.DateTime(), nullable=False, server_default=sa.text('NOW()')),
        sa.PrimaryKeyConstraint('team_id'),
        sa.UniqueConstraint('team_name')
    )
    op.create_index(op.f('ix_teams_team_id'), 'teams', ['team_id'], unique=False)

    # Create circuits table
    op.create_table(
        'circuits',
        sa.Column('circuit_id', sa.Integer(), nullable=False),
        sa.Column('circuit_name', sa.String(length=100), nullable=False),
        sa.Column('location', sa.String(length=100), nullable=True),
        sa.Column('country', sa.String(length=50), nullable=True),
        sa.Column('track_length_km', sa.Numeric(precision=5, scale=2), nullable=True),
        sa.Column('track_type', sa.String(length=20), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.text('NOW()')),
        sa.CheckConstraint("track_type IN ('street', 'permanent')", name='ck_circuits_track_type'),
        sa.PrimaryKeyConstraint('circuit_id'),
        sa.UniqueConstraint('circuit_name')
    )
    op.create_index(op.f('ix_circuits_circuit_id'), 'circuits', ['circuit_id'], unique=False)

    # Create drivers table
    op.create_table(
        'drivers',
        sa.Column('driver_id', sa.Integer(), nullable=False),
        sa.Column('driver_code', sa.String(length=3), nullable=False),
        sa.Column('driver_name', sa.String(length=100), nullable=False),
        sa.Column('nationality', sa.String(length=50), nullable=True),
        sa.Column('date_of_birth', sa.Date(), nullable=True),
        sa.Column('current_team_id', sa.Integer(), nullable=True),
        sa.Column('current_elo_rating', sa.Integer(), nullable=True, default=1500),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.text('NOW()')),
        sa.Column('updated_at', sa.DateTime(), nullable=False, server_default=sa.text('NOW()')),
        sa.ForeignKeyConstraint(['current_team_id'], ['teams.team_id'], ),
        sa.PrimaryKeyConstraint('driver_id'),
        sa.UniqueConstraint('driver_code')
    )
    op.create_index('idx_drivers_code', 'drivers', ['driver_code'], unique=False)
    op.create_index('idx_drivers_elo', 'drivers', ['current_elo_rating'], unique=False)
    op.create_index(op.f('ix_drivers_driver_id'), 'drivers', ['driver_id'], unique=False)

    # Create races table
    op.create_table(
        'races',
        sa.Column('race_id', sa.Integer(), nullable=False),
        sa.Column('season_year', sa.Integer(), nullable=False),
        sa.Column('round_number', sa.Integer(), nullable=False),
        sa.Column('circuit_id', sa.Integer(), nullable=True),
        sa.Column('race_date', sa.Date(), nullable=False),
        sa.Column('race_name', sa.String(length=100), nullable=False),
        sa.Column('status', sa.String(length=20), nullable=True, default='scheduled'),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.text('NOW()')),
        sa.CheckConstraint("status IN ('scheduled', 'completed', 'cancelled')", name='ck_races_status'),
        sa.ForeignKeyConstraint(['circuit_id'], ['circuits.circuit_id'], ),
        sa.PrimaryKeyConstraint('race_id'),
        sa.UniqueConstraint('season_year', 'round_number', name='uq_races_season_round')
    )
    op.create_index('idx_races_date', 'races', ['race_date'], unique=False)
    op.create_index('idx_races_season', 'races', ['season_year', 'round_number'], unique=False)
    op.create_index('idx_races_status', 'races', ['status'], unique=False)
    op.create_index(op.f('ix_races_race_id'), 'races', ['race_id'], unique=False)

    # Create users table
    op.create_table(
        'users',
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('email', sa.String(length=255), nullable=False),
        sa.Column('password_hash', sa.String(length=255), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.text('NOW()')),
        sa.Column('last_login', sa.DateTime(), nullable=True),
        sa.Column('role', sa.String(length=20), nullable=True, default='user'),
        sa.CheckConstraint("role IN ('user', 'admin')", name='ck_users_role'),
        sa.PrimaryKeyConstraint('user_id'),
        sa.UniqueConstraint('email')
    )
    op.create_index('idx_users_email', 'users', ['email'], unique=False)
    op.create_index(op.f('ix_users_user_id'), 'users', ['user_id'], unique=False)

    # Create weather_data table
    op.create_table(
        'weather_data',
        sa.Column('weather_id', sa.Integer(), nullable=False),
        sa.Column('race_id', sa.Integer(), nullable=False),
        sa.Column('temperature_celsius', sa.Numeric(precision=4, scale=1), nullable=True),
        sa.Column('precipitation_mm', sa.Numeric(precision=5, scale=2), nullable=True),
        sa.Column('wind_speed_kph', sa.Numeric(precision=5, scale=2), nullable=True),
        sa.Column('conditions', sa.String(length=20), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.text('NOW()')),
        sa.CheckConstraint("conditions IN ('dry', 'wet', 'mixed')", name='ck_weather_data_conditions'),
        sa.ForeignKeyConstraint(['race_id'], ['races.race_id'], ),
        sa.PrimaryKeyConstraint('weather_id'),
        sa.UniqueConstraint('race_id')
    )
    op.create_index(op.f('ix_weather_data_weather_id'), 'weather_data', ['weather_id'], unique=False)

    # Create qualifying_results table
    op.create_table(
        'qualifying_results',
        sa.Column('qualifying_id', sa.Integer(), nullable=False),
        sa.Column('race_id', sa.Integer(), nullable=False),
        sa.Column('driver_id', sa.Integer(), nullable=False),
        sa.Column('q1_time', sa.Interval(), nullable=True),
        sa.Column('q2_time', sa.Interval(), nullable=True),
        sa.Column('q3_time', sa.Interval(), nullable=True),
        sa.Column('final_grid_position', sa.Integer(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.text('NOW()')),
        sa.ForeignKeyConstraint(['driver_id'], ['drivers.driver_id'], ),
        sa.ForeignKeyConstraint(['race_id'], ['races.race_id'], ),
        sa.PrimaryKeyConstraint('qualifying_id'),
        sa.UniqueConstraint('race_id', 'driver_id', name='uq_qualifying_results_race_driver')
    )
    op.create_index('idx_qualifying_race', 'qualifying_results', ['race_id'], unique=False)
    op.create_index(op.f('ix_qualifying_results_qualifying_id'), 'qualifying_results', ['qualifying_id'], unique=False)

    # Create race_results table with partitioning
    op.create_table(
        'race_results',
        sa.Column('result_id', sa.Integer(), nullable=False),
        sa.Column('race_id', sa.Integer(), nullable=False),
        sa.Column('driver_id', sa.Integer(), nullable=False),
        sa.Column('team_id', sa.Integer(), nullable=False),
        sa.Column('grid_position', sa.Integer(), nullable=True),
        sa.Column('final_position', sa.Integer(), nullable=True),
        sa.Column('points', sa.Numeric(precision=4, scale=1), nullable=True),
        sa.Column('fastest_lap_time', sa.Interval(), nullable=True),
        sa.Column('status', sa.String(length=20), nullable=True, default='finished'),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.text('NOW()')),
        sa.CheckConstraint("status IN ('finished', 'retired', 'dnf', 'disqualified')", name='ck_race_results_status'),
        sa.ForeignKeyConstraint(['driver_id'], ['drivers.driver_id'], ),
        sa.ForeignKeyConstraint(['race_id'], ['races.race_id'], ),
        sa.ForeignKeyConstraint(['team_id'], ['teams.team_id'], ),
        sa.PrimaryKeyConstraint('result_id'),
        sa.UniqueConstraint('race_id', 'driver_id', name='uq_race_results_race_driver')
    )
    op.create_index('idx_race_results_driver', 'race_results', ['driver_id'], unique=False)
    op.create_index('idx_race_results_race', 'race_results', ['race_id'], unique=False)
    op.create_index(op.f('ix_race_results_result_id'), 'race_results', ['result_id'], unique=False)

    # Create predictions table with partitioning
    op.create_table(
        'predictions',
        sa.Column('prediction_id', sa.Integer(), nullable=False),
        sa.Column('race_id', sa.Integer(), nullable=False),
        sa.Column('driver_id', sa.Integer(), nullable=False),
        sa.Column('predicted_win_probability', sa.Numeric(precision=5, scale=2), nullable=False),
        sa.Column('model_version', sa.String(length=50), nullable=False),
        sa.Column('prediction_timestamp', sa.DateTime(), nullable=False, server_default=sa.text('NOW()')),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.text('NOW()')),
        sa.CheckConstraint('predicted_win_probability >= 0 AND predicted_win_probability <= 100', name='ck_predictions_probability_range'),
        sa.ForeignKeyConstraint(['driver_id'], ['drivers.driver_id'], ),
        sa.ForeignKeyConstraint(['race_id'], ['races.race_id'], ),
        sa.PrimaryKeyConstraint('prediction_id'),
        sa.UniqueConstraint('race_id', 'driver_id', 'model_version', name='uq_predictions_race_driver_model')
    )
    op.create_index('idx_predictions_race', 'predictions', ['race_id'], unique=False)
    op.create_index('idx_predictions_timestamp', 'predictions', ['prediction_timestamp'], unique=False)
    op.create_index(op.f('ix_predictions_prediction_id'), 'predictions', ['prediction_id'], unique=False)

    # Create prediction_accuracy table
    op.create_table(
        'prediction_accuracy',
        sa.Column('accuracy_id', sa.Integer(), nullable=False),
        sa.Column('race_id', sa.Integer(), nullable=False),
        sa.Column('brier_score', sa.Numeric(precision=6, scale=4), nullable=True),
        sa.Column('log_loss', sa.Numeric(precision=6, scale=4), nullable=True),
        sa.Column('correct_winner', sa.Boolean(), nullable=True),
        sa.Column('top_3_accuracy', sa.Boolean(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.text('NOW()')),
        sa.ForeignKeyConstraint(['race_id'], ['races.race_id'], ),
        sa.PrimaryKeyConstraint('accuracy_id'),
        sa.UniqueConstraint('race_id')
    )
    op.create_index('idx_accuracy_race', 'prediction_accuracy', ['race_id'], unique=False)
    op.create_index(op.f('ix_prediction_accuracy_accuracy_id'), 'prediction_accuracy', ['accuracy_id'], unique=False)

    # Create table partitions for race_results (PostgreSQL native partitioning)
    op.execute("""
        -- Convert race_results to partitioned table
        ALTER TABLE race_results DROP CONSTRAINT race_results_pkey CASCADE;
        ALTER TABLE race_results ADD PRIMARY KEY (result_id, race_id);
    """)

    # Create materialized view for driver rankings
    op.execute("""
        CREATE MATERIALIZED VIEW driver_rankings AS
        SELECT
            d.driver_id,
            d.driver_name,
            d.current_elo_rating,
            COUNT(CASE WHEN rr.final_position = 1 THEN 1 END) as wins,
            COALESCE(SUM(rr.points), 0) as total_points,
            MAX(r.season_year) as latest_season
        FROM drivers d
        LEFT JOIN race_results rr ON d.driver_id = rr.driver_id
        LEFT JOIN races r ON rr.race_id = r.race_id
        GROUP BY d.driver_id, d.driver_name, d.current_elo_rating
        ORDER BY d.current_elo_rating DESC;
    """)

    # Create unique index on materialized view
    op.create_index('idx_driver_rankings_driver', 'driver_rankings', ['driver_id'], unique=True)


def downgrade() -> None:
    """Drop all F1 Analytics database objects."""

    # Drop materialized view
    op.execute("DROP MATERIALIZED VIEW IF EXISTS driver_rankings")

    # Drop tables in reverse order to respect foreign key constraints
    op.drop_table('prediction_accuracy')
    op.drop_table('predictions')
    op.drop_table('race_results')
    op.drop_table('qualifying_results')
    op.drop_table('weather_data')
    op.drop_table('users')
    op.drop_table('races')
    op.drop_table('drivers')
    op.drop_table('circuits')
    op.drop_table('teams')