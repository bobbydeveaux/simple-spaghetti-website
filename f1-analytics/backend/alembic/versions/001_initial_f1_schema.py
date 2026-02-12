"""Initial F1 Analytics Database Schema

Creates all tables for the F1 prediction analytics system including:
- Core entities: teams, drivers, circuits, races
- Results: race_results, qualifying_results
- Weather: weather_data
- Predictions: predictions, prediction_accuracy
- Authentication: users

Includes all constraints, indexes, and relationships for optimal performance.

Revision ID: 001_initial_schema
Revises:
Create Date: 2026-02-12 12:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '001_initial_schema'
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Create all F1 analytics tables with proper constraints and indexes."""

    # Create teams table
    op.create_table(
        'teams',
        sa.Column('team_id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('team_name', sa.String(length=100), nullable=False),
        sa.Column('nationality', sa.String(length=50), nullable=False),
        sa.Column('current_elo_rating', sa.Integer(), nullable=False, server_default='1500'),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.text('CURRENT_TIMESTAMP')),
        sa.Column('updated_at', sa.DateTime(), nullable=False, server_default=sa.text('CURRENT_TIMESTAMP')),
        sa.PrimaryKeyConstraint('team_id', name=op.f('pk_teams')),
        sa.UniqueConstraint('team_name', name=op.f('uq_teams_team_name'))
    )
    op.create_index('idx_teams_elo_rating', 'teams', ['current_elo_rating'])
    op.create_index('idx_teams_name', 'teams', ['team_name'])
    op.create_index(op.f('ix_teams_team_name'), 'teams', ['team_name'])

    # Create circuits table
    op.create_table(
        'circuits',
        sa.Column('circuit_id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('circuit_name', sa.String(length=100), nullable=False),
        sa.Column('location', sa.String(length=100), nullable=False),
        sa.Column('country', sa.String(length=50), nullable=False),
        sa.Column('track_length_km', sa.DECIMAL(precision=5, scale=2), nullable=False),
        sa.Column('track_type', sa.String(length=20), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.text('CURRENT_TIMESTAMP')),
        sa.CheckConstraint("track_type IN ('street', 'permanent')", name='ck_circuits_track_type'),
        sa.CheckConstraint("track_length_km > 0", name='ck_circuits_track_length_positive'),
        sa.PrimaryKeyConstraint('circuit_id', name=op.f('pk_circuits')),
        sa.UniqueConstraint('circuit_name', name=op.f('uq_circuits_circuit_name'))
    )
    op.create_index('idx_circuits_country', 'circuits', ['country'])
    op.create_index('idx_circuits_name', 'circuits', ['circuit_name'])
    op.create_index('idx_circuits_type', 'circuits', ['track_type'])
    op.create_index(op.f('ix_circuits_circuit_name'), 'circuits', ['circuit_name'])
    op.create_index(op.f('ix_circuits_country'), 'circuits', ['country'])
    op.create_index(op.f('ix_circuits_track_type'), 'circuits', ['track_type'])

    # Create drivers table
    op.create_table(
        'drivers',
        sa.Column('driver_id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('driver_code', sa.String(length=3), nullable=False),
        sa.Column('driver_name', sa.String(length=100), nullable=False),
        sa.Column('nationality', sa.String(length=50), nullable=False),
        sa.Column('date_of_birth', sa.Date(), nullable=False),
        sa.Column('current_team_id', sa.Integer(), nullable=True),
        sa.Column('current_elo_rating', sa.Integer(), nullable=False, server_default='1500'),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.text('CURRENT_TIMESTAMP')),
        sa.Column('updated_at', sa.DateTime(), nullable=False, server_default=sa.text('CURRENT_TIMESTAMP')),
        sa.ForeignKeyConstraint(['current_team_id'], ['teams.team_id'], name=op.f('fk_drivers_current_team_id_teams'), ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('driver_id', name=op.f('pk_drivers')),
        sa.UniqueConstraint('driver_code', name=op.f('uq_drivers_driver_code'))
    )
    op.create_index('idx_drivers_code', 'drivers', ['driver_code'])
    op.create_index('idx_drivers_elo_rating', 'drivers', ['current_elo_rating'])
    op.create_index('idx_drivers_name', 'drivers', ['driver_name'])
    op.create_index('idx_drivers_team', 'drivers', ['current_team_id'])
    op.create_index(op.f('ix_drivers_current_elo_rating'), 'drivers', ['current_elo_rating'])
    op.create_index(op.f('ix_drivers_current_team_id'), 'drivers', ['current_team_id'])
    op.create_index(op.f('ix_drivers_driver_code'), 'drivers', ['driver_code'])
    op.create_index(op.f('ix_drivers_driver_name'), 'drivers', ['driver_name'])

    # Create races table
    op.create_table(
        'races',
        sa.Column('race_id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('season_year', sa.Integer(), nullable=False),
        sa.Column('round_number', sa.Integer(), nullable=False),
        sa.Column('race_date', sa.Date(), nullable=False),
        sa.Column('race_name', sa.String(length=100), nullable=False),
        sa.Column('circuit_id', sa.Integer(), nullable=False),
        sa.Column('status', sa.String(length=20), nullable=False, server_default='scheduled'),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.text('CURRENT_TIMESTAMP')),
        sa.CheckConstraint("status IN ('scheduled', 'completed', 'cancelled')", name='ck_races_status'),
        sa.CheckConstraint("season_year >= 1950", name='ck_races_season_year_valid'),
        sa.CheckConstraint("round_number >= 1 AND round_number <= 30", name='ck_races_round_number_valid'),
        sa.ForeignKeyConstraint(['circuit_id'], ['circuits.circuit_id'], name=op.f('fk_races_circuit_id_circuits'), ondelete='RESTRICT'),
        sa.PrimaryKeyConstraint('race_id', name=op.f('pk_races')),
        sa.UniqueConstraint('season_year', 'round_number', name='uq_races_season_round')
    )
    op.create_index('idx_races_date', 'races', ['race_date'])
    op.create_index('idx_races_season_round', 'races', ['season_year', 'round_number'])
    op.create_index('idx_races_season_year', 'races', ['season_year'])
    op.create_index('idx_races_status', 'races', ['status'])
    op.create_index(op.f('ix_races_circuit_id'), 'races', ['circuit_id'])
    op.create_index(op.f('ix_races_race_date'), 'races', ['race_date'])
    op.create_index(op.f('ix_races_season_year'), 'races', ['season_year'])
    op.create_index(op.f('ix_races_status'), 'races', ['status'])

    # Create users table
    op.create_table(
        'users',
        sa.Column('user_id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('email', sa.String(length=255), nullable=False),
        sa.Column('password_hash', sa.String(length=255), nullable=False),
        sa.Column('role', sa.String(length=20), nullable=False, server_default='user'),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.text('CURRENT_TIMESTAMP')),
        sa.Column('last_login', sa.DateTime(), nullable=True),
        sa.CheckConstraint("email LIKE '%@%'", name='ck_users_email_format'),
        sa.CheckConstraint("length(email) >= 5", name='ck_users_email_min_length'),
        sa.CheckConstraint("role IN ('user', 'admin')", name='ck_users_role'),
        sa.PrimaryKeyConstraint('user_id', name=op.f('pk_users')),
        sa.UniqueConstraint('email', name=op.f('uq_users_email'))
    )
    op.create_index('idx_users_created_at', 'users', ['created_at'])
    op.create_index('idx_users_email', 'users', ['email'])
    op.create_index('idx_users_last_login', 'users', ['last_login'])
    op.create_index('idx_users_role', 'users', ['role'])
    op.create_index(op.f('ix_users_email'), 'users', ['email'])
    op.create_index(op.f('ix_users_last_login'), 'users', ['last_login'])
    op.create_index(op.f('ix_users_role'), 'users', ['role'])

    # Create weather_data table
    op.create_table(
        'weather_data',
        sa.Column('weather_id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('race_id', sa.Integer(), nullable=False),
        sa.Column('temperature_celsius', sa.DECIMAL(precision=4, scale=1), nullable=False),
        sa.Column('precipitation_mm', sa.DECIMAL(precision=5, scale=2), nullable=False, server_default='0.00'),
        sa.Column('wind_speed_kph', sa.DECIMAL(precision=5, scale=2), nullable=False, server_default='0.00'),
        sa.Column('conditions', sa.String(length=20), nullable=False, server_default='dry'),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.text('CURRENT_TIMESTAMP')),
        sa.CheckConstraint("temperature_celsius >= -20 AND temperature_celsius <= 60", name='ck_weather_data_temperature_range'),
        sa.CheckConstraint("precipitation_mm >= 0", name='ck_weather_data_precipitation_non_negative'),
        sa.CheckConstraint("wind_speed_kph >= 0", name='ck_weather_data_wind_speed_non_negative'),
        sa.CheckConstraint("conditions IN ('dry', 'wet', 'mixed', 'overcast', 'sunny')", name='ck_weather_data_conditions'),
        sa.ForeignKeyConstraint(['race_id'], ['races.race_id'], name=op.f('fk_weather_data_race_id_races'), ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('weather_id', name=op.f('pk_weather_data')),
        sa.UniqueConstraint('race_id', name=op.f('uq_weather_data_race_id'))
    )
    op.create_index('idx_weather_data_conditions', 'weather_data', ['conditions'])
    op.create_index('idx_weather_data_race', 'weather_data', ['race_id'])
    op.create_index('idx_weather_data_temperature', 'weather_data', ['temperature_celsius'])
    op.create_index(op.f('ix_weather_data_conditions'), 'weather_data', ['conditions'])
    op.create_index(op.f('ix_weather_data_race_id'), 'weather_data', ['race_id'])

    # Create qualifying_results table
    op.create_table(
        'qualifying_results',
        sa.Column('qualifying_id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('race_id', sa.Integer(), nullable=False),
        sa.Column('driver_id', sa.Integer(), nullable=False),
        sa.Column('q1_time', sa.Interval(), nullable=True),
        sa.Column('q2_time', sa.Interval(), nullable=True),
        sa.Column('q3_time', sa.Interval(), nullable=True),
        sa.Column('final_grid_position', sa.Integer(), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.text('CURRENT_TIMESTAMP')),
        sa.CheckConstraint("final_grid_position >= 1 AND final_grid_position <= 30", name='ck_qualifying_results_grid_position_valid'),
        sa.ForeignKeyConstraint(['driver_id'], ['drivers.driver_id'], name=op.f('fk_qualifying_results_driver_id_drivers'), ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['race_id'], ['races.race_id'], name=op.f('fk_qualifying_results_race_id_races'), ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('qualifying_id', name=op.f('pk_qualifying_results')),
        sa.UniqueConstraint('race_id', 'driver_id', name='uq_qualifying_results_race_driver')
    )
    op.create_index('idx_qualifying_results_driver', 'qualifying_results', ['driver_id'])
    op.create_index('idx_qualifying_results_grid_position', 'qualifying_results', ['final_grid_position'])
    op.create_index('idx_qualifying_results_race', 'qualifying_results', ['race_id'])
    op.create_index('idx_qualifying_results_race_driver', 'qualifying_results', ['race_id', 'driver_id'])
    op.create_index('idx_qualifying_results_race_position', 'qualifying_results', ['race_id', 'final_grid_position'])
    op.create_index(op.f('ix_qualifying_results_driver_id'), 'qualifying_results', ['driver_id'])
    op.create_index(op.f('ix_qualifying_results_final_grid_position'), 'qualifying_results', ['final_grid_position'])
    op.create_index(op.f('ix_qualifying_results_race_id'), 'qualifying_results', ['race_id'])

    # Create race_results table
    op.create_table(
        'race_results',
        sa.Column('result_id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('race_id', sa.Integer(), nullable=False),
        sa.Column('driver_id', sa.Integer(), nullable=False),
        sa.Column('team_id', sa.Integer(), nullable=False),
        sa.Column('grid_position', sa.Integer(), nullable=False),
        sa.Column('final_position', sa.Integer(), nullable=True),
        sa.Column('points', sa.DECIMAL(precision=4, scale=1), nullable=False, server_default='0.0'),
        sa.Column('fastest_lap_time', sa.Interval(), nullable=True),
        sa.Column('status', sa.String(length=20), nullable=False, server_default='finished'),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.text('CURRENT_TIMESTAMP')),
        sa.CheckConstraint("grid_position >= 1 AND grid_position <= 30", name='ck_race_results_grid_position_valid'),
        sa.CheckConstraint("final_position IS NULL OR (final_position >= 1 AND final_position <= 30)", name='ck_race_results_final_position_valid'),
        sa.CheckConstraint("points >= 0", name='ck_race_results_points_non_negative'),
        sa.CheckConstraint("status IN ('finished', 'retired', 'dnf', 'disqualified', 'dns')", name='ck_race_results_status'),
        sa.ForeignKeyConstraint(['driver_id'], ['drivers.driver_id'], name=op.f('fk_race_results_driver_id_drivers'), ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['race_id'], ['races.race_id'], name=op.f('fk_race_results_race_id_races'), ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['team_id'], ['teams.team_id'], name=op.f('fk_race_results_team_id_teams'), ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('result_id', name=op.f('pk_race_results')),
        sa.UniqueConstraint('race_id', 'driver_id', name='uq_race_results_race_driver')
    )
    op.create_index('idx_race_results_driver', 'race_results', ['driver_id'])
    op.create_index('idx_race_results_final_position', 'race_results', ['final_position'])
    op.create_index('idx_race_results_points', 'race_results', ['points'])
    op.create_index('idx_race_results_race', 'race_results', ['race_id'])
    op.create_index('idx_race_results_race_driver', 'race_results', ['race_id', 'driver_id'])
    op.create_index('idx_race_results_race_position', 'race_results', ['race_id', 'final_position'])
    op.create_index('idx_race_results_status', 'race_results', ['status'])
    op.create_index('idx_race_results_team', 'race_results', ['team_id'])
    op.create_index(op.f('ix_race_results_driver_id'), 'race_results', ['driver_id'])
    op.create_index(op.f('ix_race_results_race_id'), 'race_results', ['race_id'])
    op.create_index(op.f('ix_race_results_status'), 'race_results', ['status'])
    op.create_index(op.f('ix_race_results_team_id'), 'race_results', ['team_id'])

    # Create predictions table
    op.create_table(
        'predictions',
        sa.Column('prediction_id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('race_id', sa.Integer(), nullable=False),
        sa.Column('driver_id', sa.Integer(), nullable=False),
        sa.Column('predicted_win_probability', sa.DECIMAL(precision=5, scale=2), nullable=False),
        sa.Column('model_version', sa.String(length=50), nullable=False),
        sa.Column('prediction_timestamp', sa.DateTime(), nullable=False, server_default=sa.text('CURRENT_TIMESTAMP')),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.text('CURRENT_TIMESTAMP')),
        sa.CheckConstraint("predicted_win_probability >= 0 AND predicted_win_probability <= 100", name='ck_predictions_probability_range'),
        sa.ForeignKeyConstraint(['driver_id'], ['drivers.driver_id'], name=op.f('fk_predictions_driver_id_drivers'), ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['race_id'], ['races.race_id'], name=op.f('fk_predictions_race_id_races'), ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('prediction_id', name=op.f('pk_predictions')),
        sa.UniqueConstraint('race_id', 'driver_id', 'model_version', name='uq_predictions_race_driver_model')
    )
    op.create_index('idx_predictions_driver', 'predictions', ['driver_id'])
    op.create_index('idx_predictions_model', 'predictions', ['model_version'])
    op.create_index('idx_predictions_probability', 'predictions', ['predicted_win_probability'])
    op.create_index('idx_predictions_race', 'predictions', ['race_id'])
    op.create_index('idx_predictions_race_driver', 'predictions', ['race_id', 'driver_id'])
    op.create_index('idx_predictions_race_model', 'predictions', ['race_id', 'model_version'])
    op.create_index('idx_predictions_race_probability', 'predictions', ['race_id', 'predicted_win_probability'])
    op.create_index('idx_predictions_timestamp', 'predictions', ['prediction_timestamp'], postgresql_using='brin')
    op.create_index(op.f('ix_predictions_driver_id'), 'predictions', ['driver_id'])
    op.create_index(op.f('ix_predictions_model_version'), 'predictions', ['model_version'])
    op.create_index(op.f('ix_predictions_predicted_win_probability'), 'predictions', ['predicted_win_probability'])
    op.create_index(op.f('ix_predictions_prediction_timestamp'), 'predictions', ['prediction_timestamp'])
    op.create_index(op.f('ix_predictions_race_id'), 'predictions', ['race_id'])

    # Create prediction_accuracy table
    op.create_table(
        'prediction_accuracy',
        sa.Column('accuracy_id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('race_id', sa.Integer(), nullable=False),
        sa.Column('brier_score', sa.DECIMAL(precision=6, scale=4), nullable=False),
        sa.Column('log_loss', sa.DECIMAL(precision=6, scale=4), nullable=False),
        sa.Column('correct_winner', sa.Boolean(), nullable=False),
        sa.Column('top_3_accuracy', sa.Boolean(), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.text('CURRENT_TIMESTAMP')),
        sa.CheckConstraint("brier_score >= 0 AND brier_score <= 1", name='ck_prediction_accuracy_brier_score_range'),
        sa.CheckConstraint("log_loss >= 0", name='ck_prediction_accuracy_log_loss_non_negative'),
        sa.ForeignKeyConstraint(['race_id'], ['races.race_id'], name=op.f('fk_prediction_accuracy_race_id_races'), ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('accuracy_id', name=op.f('pk_prediction_accuracy')),
        sa.UniqueConstraint('race_id', name=op.f('uq_prediction_accuracy_race_id'))
    )
    op.create_index('idx_prediction_accuracy_brier', 'prediction_accuracy', ['brier_score'])
    op.create_index('idx_prediction_accuracy_log_loss', 'prediction_accuracy', ['log_loss'])
    op.create_index('idx_prediction_accuracy_race', 'prediction_accuracy', ['race_id'])
    op.create_index('idx_prediction_accuracy_top3', 'prediction_accuracy', ['top_3_accuracy'])
    op.create_index('idx_prediction_accuracy_winner', 'prediction_accuracy', ['correct_winner'])
    op.create_index(op.f('ix_prediction_accuracy_brier_score'), 'prediction_accuracy', ['brier_score'])
    op.create_index(op.f('ix_prediction_accuracy_correct_winner'), 'prediction_accuracy', ['correct_winner'])
    op.create_index(op.f('ix_prediction_accuracy_log_loss'), 'prediction_accuracy', ['log_loss'])
    op.create_index(op.f('ix_prediction_accuracy_race_id'), 'prediction_accuracy', ['race_id'])
    op.create_index(op.f('ix_prediction_accuracy_top_3_accuracy'), 'prediction_accuracy', ['top_3_accuracy'])

    # Create materialized view for driver rankings (for performance)
    op.execute("""
        CREATE MATERIALIZED VIEW driver_rankings AS
        SELECT
            d.driver_id,
            d.driver_name,
            d.driver_code,
            d.current_elo_rating,
            COALESCE(wins.win_count, 0) as wins,
            COALESCE(points.total_points, 0) as total_points,
            COALESCE(races.latest_season, EXTRACT(YEAR FROM CURRENT_DATE)) as latest_season
        FROM drivers d
        LEFT JOIN (
            SELECT driver_id, COUNT(*) as win_count
            FROM race_results
            WHERE final_position = 1
            GROUP BY driver_id
        ) wins ON d.driver_id = wins.driver_id
        LEFT JOIN (
            SELECT driver_id, SUM(points) as total_points
            FROM race_results
            GROUP BY driver_id
        ) points ON d.driver_id = points.driver_id
        LEFT JOIN (
            SELECT driver_id, MAX(r.season_year) as latest_season
            FROM race_results rr
            JOIN races r ON rr.race_id = r.race_id
            GROUP BY driver_id
        ) races ON d.driver_id = races.driver_id
        ORDER BY d.current_elo_rating DESC;
    """)

    # Create index on materialized view
    op.create_index('idx_driver_rankings_elo', 'driver_rankings', ['current_elo_rating'])
    op.create_index('idx_driver_rankings_wins', 'driver_rankings', ['wins'])
    op.create_index('idx_driver_rankings_points', 'driver_rankings', ['total_points'])


def downgrade() -> None:
    """Drop all F1 analytics tables and related objects."""

    # Drop materialized view first
    op.execute("DROP MATERIALIZED VIEW IF EXISTS driver_rankings")

    # Drop tables in reverse order of creation (respecting foreign keys)
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