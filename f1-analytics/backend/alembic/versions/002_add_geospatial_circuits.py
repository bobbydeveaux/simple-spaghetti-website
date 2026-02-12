"""Add geospatial columns to circuits table

Add latitude and longitude columns to the circuits table to enable
weather data ingestion with geospatial matching functionality.

Revision ID: 002_add_geospatial_circuits
Revises: 001_initial_schema
Create Date: 2026-02-12 12:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '002_add_geospatial_circuits'
down_revision = '001_initial_schema'
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Add geospatial columns to circuits table."""

    # Add latitude column
    op.add_column('circuits', sa.Column(
        'latitude',
        sa.Numeric(precision=10, scale=8),
        nullable=True,
        comment='Circuit latitude coordinate for geospatial matching'
    ))

    # Add longitude column
    op.add_column('circuits', sa.Column(
        'longitude',
        sa.Numeric(precision=11, scale=8),
        nullable=True,
        comment='Circuit longitude coordinate for geospatial matching'
    ))

    # Add check constraints for valid coordinate ranges
    op.create_check_constraint(
        'ck_circuits_latitude_range',
        'circuits',
        'latitude >= -90 AND latitude <= 90'
    )

    op.create_check_constraint(
        'ck_circuits_longitude_range',
        'circuits',
        'longitude >= -180 AND longitude <= 180'
    )

    # Add geospatial index for efficient coordinate-based queries
    op.create_index(
        'idx_circuits_coordinates',
        'circuits',
        ['latitude', 'longitude'],
        unique=False
    )


def downgrade() -> None:
    """Remove geospatial columns from circuits table."""

    # Drop the geospatial index
    op.drop_index('idx_circuits_coordinates', table_name='circuits')

    # Drop the check constraints
    op.drop_constraint('ck_circuits_longitude_range', 'circuits', type_='check')
    op.drop_constraint('ck_circuits_latitude_range', 'circuits', type_='check')

    # Drop the columns
    op.drop_column('circuits', 'longitude')
    op.drop_column('circuits', 'latitude')