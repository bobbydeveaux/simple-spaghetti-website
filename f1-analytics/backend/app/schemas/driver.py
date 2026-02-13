"""
Pydantic schemas for driver-related API operations.

This module provides schemas for driver data validation,
serialization, and transformation.
"""

from datetime import date
from typing import Optional, List
from pydantic import BaseModel, Field, validator

from .base import BaseSchema, TimestampMixin, PaginatedResponse


class DriverBase(BaseSchema):
    """Base driver schema with common fields."""

    driver_code: str = Field(
        ...,
        min_length=3,
        max_length=3,
        regex=r'^[A-Z]{3}$',
        description="Three-letter driver code (e.g., VER, HAM)"
    )
    driver_name: str = Field(
        ...,
        min_length=2,
        max_length=100,
        description="Full driver name"
    )
    nationality: Optional[str] = Field(
        None,
        max_length=50,
        description="Driver nationality"
    )
    date_of_birth: Optional[date] = Field(
        None,
        description="Driver's date of birth"
    )

    @validator('driver_code')
    def validate_driver_code(cls, v):
        """Validate driver code format."""
        if not v.isupper():
            raise ValueError('Driver code must be uppercase')
        return v

    @validator('driver_name')
    def validate_driver_name(cls, v):
        """Validate driver name."""
        if not v.strip():
            raise ValueError('Driver name cannot be empty')
        return v.strip()

    @validator('date_of_birth')
    def validate_date_of_birth(cls, v):
        """Validate date of birth."""
        if v and v >= date.today():
            raise ValueError('Date of birth must be in the past')
        return v


class DriverCreate(DriverBase):
    """Schema for creating a new driver."""

    current_team_id: Optional[int] = Field(
        None,
        gt=0,
        description="Current team ID"
    )
    current_elo_rating: Optional[int] = Field(
        1500,
        ge=800,
        le=3000,
        description="Current ELO rating (default: 1500)"
    )


class DriverUpdate(BaseModel):
    """Schema for updating a driver."""

    driver_name: Optional[str] = Field(
        None,
        min_length=2,
        max_length=100,
        description="Full driver name"
    )
    nationality: Optional[str] = Field(
        None,
        max_length=50,
        description="Driver nationality"
    )
    date_of_birth: Optional[date] = Field(
        None,
        description="Driver's date of birth"
    )
    current_team_id: Optional[int] = Field(
        None,
        gt=0,
        description="Current team ID"
    )
    current_elo_rating: Optional[int] = Field(
        None,
        ge=800,
        le=3000,
        description="Current ELO rating"
    )

    @validator('driver_name')
    def validate_driver_name(cls, v):
        """Validate driver name."""
        if v is not None and not v.strip():
            raise ValueError('Driver name cannot be empty')
        return v.strip() if v else v

    @validator('date_of_birth')
    def validate_date_of_birth(cls, v):
        """Validate date of birth."""
        if v and v >= date.today():
            raise ValueError('Date of birth must be in the past')
        return v


class DriverResponse(DriverBase, TimestampMixin):
    """Schema for driver response."""

    driver_id: int = Field(..., description="Unique driver identifier")
    current_team_id: Optional[int] = Field(None, description="Current team ID")
    current_elo_rating: int = Field(..., description="Current ELO rating")

    # Related data
    current_team: Optional['TeamBasic'] = Field(None, description="Current team information")


class DriverBasic(BaseSchema):
    """Basic driver information for nested responses."""

    driver_id: int = Field(..., description="Unique driver identifier")
    driver_code: str = Field(..., description="Three-letter driver code")
    driver_name: str = Field(..., description="Full driver name")
    current_elo_rating: int = Field(..., description="Current ELO rating")


class DriverRanking(BaseSchema):
    """Schema for driver rankings."""

    position: int = Field(..., ge=1, description="Current ranking position")
    driver_id: int = Field(..., description="Unique driver identifier")
    driver_code: str = Field(..., description="Three-letter driver code")
    driver_name: str = Field(..., description="Full driver name")
    current_team_id: Optional[int] = Field(None, description="Current team ID")
    team_name: Optional[str] = Field(None, description="Current team name")
    current_elo_rating: int = Field(..., description="Current ELO rating")
    season_wins: int = Field(0, ge=0, description="Number of wins this season")
    season_points: float = Field(0, ge=0, description="Total points this season")
    championship_position: Optional[int] = Field(None, ge=1, description="Championship standing")


class DriverStatistics(BaseSchema):
    """Schema for driver statistics."""

    driver_id: int = Field(..., description="Unique driver identifier")
    total_races: int = Field(0, ge=0, description="Total races participated")
    total_wins: int = Field(0, ge=0, description="Total race wins")
    total_podiums: int = Field(0, ge=0, description="Total podium finishes")
    total_points: float = Field(0, ge=0, description="Total career points")
    win_rate: float = Field(0, ge=0, le=1, description="Win rate percentage")
    podium_rate: float = Field(0, ge=0, le=1, description="Podium rate percentage")
    average_finish_position: Optional[float] = Field(None, ge=1, le=20, description="Average finish position")
    current_streak: int = Field(0, description="Current win/podium streak")


class DriverListResponse(PaginatedResponse):
    """Paginated driver list response."""

    data: List[DriverResponse] = Field(..., description="List of drivers")


class DriverRankingsResponse(BaseSchema):
    """Driver rankings response."""

    season: int = Field(..., description="Championship season")
    last_updated: str = Field(..., description="Last update timestamp")
    rankings: List[DriverRanking] = Field(..., description="Driver rankings list")


# Import after definitions to avoid circular imports
try:
    from .team import TeamBasic
    DriverResponse.model_rebuild()
except ImportError:
    pass