"""Initial F1 Analytics schema

Revision ID: 001
Revises:
Create Date: 2026-02-12 15:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = '001'
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Create all F1 Analytics tables."""

    # Create users table
    op.create_table('users',
        sa.Column('user_id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('email', sa.String(length=255), nullable=False),
        sa.Column('password_hash', sa.String(length=255), nullable=False),
        sa.Column('username', sa.String(length=100), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('last_login', sa.DateTime(timezone=True), nullable=True),
        sa.Column('is_active', sa.Boolean(), nullable=False),
        sa.Column('is_verified', sa.Boolean(), nullable=False),
        sa.Column('role', sa.String(length=20), nullable=False),
        sa.PrimaryKeyConstraint('user_id')
    )
    op.create_index('idx_users_created_at', 'users', ['created_at'], unique=False)
    op.create_index('idx_users_email_active', 'users', ['email', 'is_active'], unique=False)
    op.create_index('idx_users_role_active', 'users', ['role', 'is_active'], unique=False)
    op.create_index(op.f('ix_users_email'), 'users', ['email'], unique=True)
    op.create_index(op.f('ix_users_user_id'), 'users', ['user_id'], unique=False)

    # Create teams table
    op.create_table('teams',
        sa.Column('team_id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('team_name', sa.String(length=100), nullable=False),
        sa.Column('nationality', sa.String(length=50), nullable=True),
        sa.Column('current_elo_rating', sa.Integer(), nullable=False),
        sa.Column('team_color', sa.String(length=7), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint('team_id')
    )
    op.create_index(op.f('ix_teams_current_elo_rating'), 'teams', ['current_elo_rating'], unique=False)
    op.create_index(op.f('ix_teams_team_id'), 'teams', ['team_id'], unique=False)
    op.create_index(op.f('ix_teams_team_name'), 'teams', ['team_name'], unique=True)

    # Create circuits table
    op.create_table('circuits',
        sa.Column('circuit_id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('circuit_name', sa.String(length=100), nullable=False),
        sa.Column('location', sa.String(length=100), nullable=True),
        sa.Column('country', sa.String(length=50), nullable=True),
        sa.Column('track_length_km', sa.Numeric(precision=5, scale=2), nullable=True),
        sa.Column('track_type', sa.Enum('STREET', 'PERMANENT', name='tracktype'), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint('circuit_id')
    )
    op.create_index(op.f('ix_circuits_circuit_id'), 'circuits', ['circuit_id'], unique=False)
    op.create_index(op.f('ix_circuits_circuit_name'), 'circuits', ['circuit_name'], unique=True)
    op.create_index(op.f('ix_circuits_country'), 'circuits', ['country'], unique=False)

    # Create drivers table
    op.create_table('drivers',
        sa.Column('driver_id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('driver_code', sa.String(length=3), nullable=False),
        sa.Column('driver_name', sa.String(length=100), nullable=False),
        sa.Column('nationality', sa.String(length=50), nullable=True),
        sa.Column('date_of_birth', sa.Date(), nullable=True),
        sa.Column('current_team_id', sa.Integer(), nullable=True),
        sa.Column('current_elo_rating', sa.Integer(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(['current_team_id'], ['teams.team_id'], ),
        sa.PrimaryKeyConstraint('driver_id')
    )
    op.create_index('idx_drivers_code', 'drivers', ['driver_code'], unique=False)
    op.create_index('idx_drivers_elo_desc', 'drivers', ['current_elo_rating'], unique=False, postgresql_using='btree', postgresql_ops={'current_elo_rating': 'DESC'})
    op.create_index('idx_drivers_name', 'drivers', ['driver_name'], unique=False)
    op.create_index('idx_drivers_team', 'drivers', ['current_team_id'], unique=False)
    op.create_index(op.f('ix_drivers_current_elo_rating'), 'drivers', ['current_elo_rating'], unique=False)
    op.create_index(op.f('ix_drivers_driver_code'), 'drivers', ['driver_code'], unique=True)
    op.create_index(op.f('ix_drivers_driver_id'), 'drivers', ['driver_id'], unique=False)
    op.create_index(op.f('ix_drivers_driver_name'), 'drivers', ['driver_name'], unique=False)

    # Create races table
    op.create_table('races',
        sa.Column('race_id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('season_year', sa.Integer(), nullable=False),
        sa.Column('round_number', sa.Integer(), nullable=False),
        sa.Column('circuit_id', sa.Integer(), nullable=False),
        sa.Column('race_date', sa.Date(), nullable=False),
        sa.Column('race_name', sa.String(length=100), nullable=False),
        sa.Column('status', sa.Enum('SCHEDULED', 'COMPLETED', 'CANCELLED', name='racestatus'), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(['circuit_id'], ['circuits.circuit_id'], ),
        sa.PrimaryKeyConstraint('race_id'),
        sa.UniqueConstraint('season_year', 'round_number', name='uq_races_season_round')
    )
    op.create_index('idx_races_date', 'races', ['race_date'], unique=False)
    op.create_index('idx_races_season_round', 'races', ['season_year', 'round_number'], unique=False)
    op.create_index('idx_races_status', 'races', ['status'], unique=False)
    op.create_index('idx_races_upcoming', 'races', ['race_date'], unique=False, postgresql_where=sa.text("status = 'SCHEDULED'"))
    op.create_index(op.f('ix_races_race_date'), 'races', ['race_date'], unique=False)
    op.create_index(op.f('ix_races_race_id'), 'races', ['race_id'], unique=False)
    op.create_index(op.f('ix_races_season_year'), 'races', ['season_year'], unique=False)
    op.create_index(op.f('ix_races_status'), 'races', ['status'], unique=False)

    # Create race_results table
    op.create_table('race_results',
        sa.Column('result_id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('race_id', sa.Integer(), nullable=False),
        sa.Column('driver_id', sa.Integer(), nullable=False),
        sa.Column('team_id', sa.Integer(), nullable=False),
        sa.Column('grid_position', sa.Integer(), nullable=True),
        sa.Column('final_position', sa.Integer(), nullable=True),
        sa.Column('points', sa.Numeric(precision=4, scale=1), nullable=True),
        sa.Column('fastest_lap_time', sa.String(length=20), nullable=True),
        sa.Column('status', sa.Enum('FINISHED', 'RETIRED', 'DNF', 'DISQUALIFIED', name='resultstatus'), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint('final_position >= 1 AND final_position <= 30', name='ck_race_results_final_position'),
        sa.CheckConstraint('grid_position >= 1 AND grid_position <= 30', name='ck_race_results_grid_position'),
        sa.CheckConstraint('points >= 0', name='ck_race_results_points'),
        sa.ForeignKeyConstraint(['driver_id'], ['drivers.driver_id'], ),
        sa.ForeignKeyConstraint(['race_id'], ['races.race_id'], ),
        sa.ForeignKeyConstraint(['team_id'], ['teams.team_id'], ),
        sa.PrimaryKeyConstraint('result_id'),
        sa.UniqueConstraint('race_id', 'driver_id', name='uq_race_results_race_driver')
    )
    op.create_index('idx_race_results_driver', 'race_results', ['driver_id'], unique=False)
    op.create_index('idx_race_results_points_desc', 'race_results', ['points'], unique=False, postgresql_using='btree', postgresql_ops={'points': 'DESC'})
    op.create_index('idx_race_results_position', 'race_results', ['final_position'], unique=False)
    op.create_index('idx_race_results_race', 'race_results', ['race_id'], unique=False)
    op.create_index(op.f('ix_race_results_driver_id'), 'race_results', ['driver_id'], unique=False)
    op.create_index(op.f('ix_race_results_final_position'), 'race_results', ['final_position'], unique=False)
    op.create_index(op.f('ix_race_results_race_id'), 'race_results', ['race_id'], unique=False)
    op.create_index(op.f('ix_race_results_result_id'), 'race_results', ['result_id'], unique=False)

    # Create qualifying_results table
    op.create_table('qualifying_results',
        sa.Column('qualifying_id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('race_id', sa.Integer(), nullable=False),
        sa.Column('driver_id', sa.Integer(), nullable=False),
        sa.Column('q1_time', sa.String(length=20), nullable=True),
        sa.Column('q2_time', sa.String(length=20), nullable=True),
        sa.Column('q3_time', sa.String(length=20), nullable=True),
        sa.Column('final_grid_position', sa.Integer(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint('final_grid_position >= 1 AND final_grid_position <= 30', name='ck_qualifying_results_position'),
        sa.ForeignKeyConstraint(['driver_id'], ['drivers.driver_id'], ),
        sa.ForeignKeyConstraint(['race_id'], ['races.race_id'], ),
        sa.PrimaryKeyConstraint('qualifying_id'),
        sa.UniqueConstraint('race_id', 'driver_id', name='uq_qualifying_results_race_driver')
    )
    op.create_index('idx_qualifying_driver', 'qualifying_results', ['driver_id'], unique=False)
    op.create_index('idx_qualifying_position', 'qualifying_results', ['final_grid_position'], unique=False)
    op.create_index('idx_qualifying_race', 'qualifying_results', ['race_id'], unique=False)
    op.create_index(op.f('ix_qualifying_results_driver_id'), 'qualifying_results', ['driver_id'], unique=False)
    op.create_index(op.f('ix_qualifying_results_final_grid_position'), 'qualifying_results', ['final_grid_position'], unique=False)
    op.create_index(op.f('ix_qualifying_results_qualifying_id'), 'qualifying_results', ['qualifying_id'], unique=False)
    op.create_index(op.f('ix_qualifying_results_race_id'), 'qualifying_results', ['race_id'], unique=False)

    # Create weather_data table
    op.create_table('weather_data',
        sa.Column('weather_id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('race_id', sa.Integer(), nullable=False),
        sa.Column('temperature_celsius', sa.Numeric(precision=4, scale=1), nullable=True),
        sa.Column('precipitation_mm', sa.Numeric(precision=5, scale=2), nullable=True),
        sa.Column('wind_speed_kph', sa.Numeric(precision=5, scale=2), nullable=True),
        sa.Column('conditions', sa.Enum('DRY', 'WET', 'MIXED', name='weathercondition'), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(['race_id'], ['races.race_id'], ),
        sa.PrimaryKeyConstraint('weather_id')
    )
    op.create_index(op.f('ix_weather_data_race_id'), 'weather_data', ['race_id'], unique=True)
    op.create_index(op.f('ix_weather_data_weather_id'), 'weather_data', ['weather_id'], unique=False)

    # Create predictions table
    op.create_table('predictions',
        sa.Column('prediction_id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('race_id', sa.Integer(), nullable=False),
        sa.Column('driver_id', sa.Integer(), nullable=False),
        sa.Column('predicted_win_probability', sa.Numeric(precision=5, scale=2), nullable=False),
        sa.Column('model_version', sa.String(length=50), nullable=False),
        sa.Column('prediction_timestamp', sa.DateTime(timezone=True), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint('predicted_win_probability >= 0 AND predicted_win_probability <= 100', name='ck_predictions_probability_range'),
        sa.ForeignKeyConstraint(['driver_id'], ['drivers.driver_id'], ),
        sa.ForeignKeyConstraint(['race_id'], ['races.race_id'], ),
        sa.PrimaryKeyConstraint('prediction_id'),
        sa.UniqueConstraint('race_id', 'driver_id', 'model_version', name='uq_predictions_race_driver_model')
    )
    op.create_index('idx_predictions_probability_desc', 'predictions', ['predicted_win_probability'], unique=False, postgresql_using='btree', postgresql_ops={'predicted_win_probability': 'DESC'})
    op.create_index('idx_predictions_race', 'predictions', ['race_id'], unique=False)
    op.create_index('idx_predictions_timestamp_desc', 'predictions', ['prediction_timestamp'], unique=False, postgresql_using='btree', postgresql_ops={'prediction_timestamp': 'DESC'})
    op.create_index(op.f('ix_predictions_driver_id'), 'predictions', ['driver_id'], unique=False)
    op.create_index(op.f('ix_predictions_predicted_win_probability'), 'predictions', ['predicted_win_probability'], unique=False)
    op.create_index(op.f('ix_predictions_prediction_id'), 'predictions', ['prediction_id'], unique=False)
    op.create_index(op.f('ix_predictions_prediction_timestamp'), 'predictions', ['prediction_timestamp'], unique=False)
    op.create_index(op.f('ix_predictions_race_id'), 'predictions', ['race_id'], unique=False)

    # Create prediction_accuracy table
    op.create_table('prediction_accuracy',
        sa.Column('accuracy_id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('race_id', sa.Integer(), nullable=False),
        sa.Column('brier_score', sa.Numeric(precision=6, scale=4), nullable=True),
        sa.Column('log_loss', sa.Numeric(precision=6, scale=4), nullable=True),
        sa.Column('correct_winner', sa.Boolean(), nullable=True),
        sa.Column('top_3_accuracy', sa.Boolean(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(['race_id'], ['races.race_id'], ),
        sa.PrimaryKeyConstraint('accuracy_id')
    )
    op.create_index('idx_accuracy_brier', 'prediction_accuracy', ['brier_score'], unique=False)
    op.create_index('idx_accuracy_correct_winner', 'prediction_accuracy', ['correct_winner'], unique=False)
    op.create_index('idx_accuracy_race', 'prediction_accuracy', ['race_id'], unique=False)
    op.create_index(op.f('ix_prediction_accuracy_accuracy_id'), 'prediction_accuracy', ['accuracy_id'], unique=False)
    op.create_index(op.f('ix_prediction_accuracy_race_id'), 'prediction_accuracy', ['race_id'], unique=True)


def downgrade() -> None:
    """Drop all F1 Analytics tables."""
    op.drop_table('prediction_accuracy')
    op.drop_table('predictions')
    op.drop_table('weather_data')
    op.drop_table('qualifying_results')
    op.drop_table('race_results')
    op.drop_table('races')
    op.drop_table('drivers')
    op.drop_table('circuits')
    op.drop_table('teams')
    op.drop_table('users')

    # Drop custom enums
    op.execute('DROP TYPE IF EXISTS weathercondition CASCADE')
    op.execute('DROP TYPE IF EXISTS resultstatus CASCADE')
    op.execute('DROP TYPE IF EXISTS racestatus CASCADE')
    op.execute('DROP TYPE IF EXISTS tracktype CASCADE')