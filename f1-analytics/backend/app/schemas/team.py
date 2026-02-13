"""
Pydantic schemas for team-related API operations.

This module provides schemas for team data validation,
serialization, and transformation.
"""

from typing import Optional, List
from pydantic import BaseModel, Field, validator

from .base import BaseSchema, TimestampMixin, PaginatedResponse


class TeamBase(BaseSchema):
    """Base team schema with common fields."""

    team_name: str = Field(
        ...,
        min_length=2,
        max_length=100,
        description="Team name"
    )
    nationality: Optional[str] = Field(
        None,
        max_length=50,
        description="Team nationality/base country"
    )
    team_color: Optional[str] = Field(
        None,
        regex=r'^#[0-9A-Fa-f]{6}$',
        description="Team color in hex format (e.g., #FF0000)"
    )

    @validator('team_name')
    def validate_team_name(cls, v):
        """Validate team name."""
        if not v.strip():
            raise ValueError('Team name cannot be empty')
        return v.strip()

    @validator('team_color')
    def validate_team_color(cls, v):
        """Validate team color format."""
        if v and not v.startswith('#'):
            raise ValueError('Team color must start with #')
        return v.upper() if v else v


class TeamCreate(TeamBase):
    """Schema for creating a new team."""

    current_elo_rating: Optional[int] = Field(
        1500,
        ge=800,
        le=3000,
        description="Current ELO rating (default: 1500)"
    )


class TeamUpdate(BaseModel):
    """Schema for updating a team."""

    team_name: Optional[str] = Field(
        None,
        min_length=2,
        max_length=100,
        description="Team name"
    )
    nationality: Optional[str] = Field(
        None,
        max_length=50,
        description="Team nationality/base country"
    )
    team_color: Optional[str] = Field(
        None,
        regex=r'^#[0-9A-Fa-f]{6}$',
        description="Team color in hex format"
    )
    current_elo_rating: Optional[int] = Field(
        None,
        ge=800,
        le=3000,
        description="Current ELO rating"
    )

    @validator('team_name')
    def validate_team_name(cls, v):
        """Validate team name."""
        if v is not None and not v.strip():
            raise ValueError('Team name cannot be empty')
        return v.strip() if v else v

    @validator('team_color')
    def validate_team_color(cls, v):
        """Validate team color format."""
        if v and not v.startswith('#'):
            raise ValueError('Team color must start with #')
        return v.upper() if v else v


class TeamResponse(TeamBase, TimestampMixin):
    """Schema for team response."""

    team_id: int = Field(..., description="Unique team identifier")
    current_elo_rating: int = Field(..., description="Current ELO rating")

    # Related data
    drivers: Optional[List['DriverBasic']] = Field(None, description="Current team drivers")
    driver_count: int = Field(0, description="Number of current drivers")


class TeamBasic(BaseSchema):
    """Basic team information for nested responses."""

    team_id: int = Field(..., description="Unique team identifier")
    team_name: str = Field(..., description="Team name")
    team_color: Optional[str] = Field(None, description="Team color in hex format")
    current_elo_rating: int = Field(..., description="Current ELO rating")


class TeamStanding(BaseSchema):
    """Schema for team championship standings."""

    position: int = Field(..., ge=1, description="Current championship position")
    team_id: int = Field(..., description="Unique team identifier")
    team_name: str = Field(..., description="Team name")
    team_color: Optional[str] = Field(None, description="Team color in hex format")
    current_elo_rating: int = Field(..., description="Current ELO rating")
    total_points: float = Field(0, ge=0, description="Total championship points")
    race_wins: int = Field(0, ge=0, description="Number of race wins")
    podium_finishes: int = Field(0, ge=0, description="Number of podium finishes")
    races_completed: int = Field(0, ge=0, description="Number of races completed")


class TeamStatistics(BaseSchema):
    """Schema for team statistics."""

    team_id: int = Field(..., description="Unique team identifier")
    total_races: int = Field(0, ge=0, description="Total races participated")
    total_wins: int = Field(0, ge=0, description="Total race wins")
    total_podiums: int = Field(0, ge=0, description="Total podium finishes")
    total_points: float = Field(0, ge=0, description="Total points earned")
    win_rate: float = Field(0, ge=0, le=1, description="Win rate percentage")
    podium_rate: float = Field(0, ge=0, le=1, description="Podium rate percentage")
    average_points_per_race: Optional[float] = Field(None, ge=0, description="Average points per race")
    championship_titles: int = Field(0, ge=0, description="Number of championship titles")
    seasons_active: int = Field(0, ge=0, description="Number of seasons active")


class TeamPerformanceMetrics(BaseSchema):
    """Schema for team performance metrics."""

    team_id: int = Field(..., description="Unique team identifier")
    season: int = Field(..., description="Season year")
    elo_trend: List[float] = Field([], description="ELO rating trend over the season")
    points_progression: List[float] = Field([], description="Points progression over the season")
    win_streak: int = Field(0, description="Current win streak")
    podium_streak: int = Field(0, description="Current podium streak")
    best_finish_position: Optional[int] = Field(None, ge=1, le=20, description="Best finish position this season")
    worst_finish_position: Optional[int] = Field(None, ge=1, le=20, description="Worst finish position this season")
    consistency_score: Optional[float] = Field(None, ge=0, le=100, description="Consistency score (0-100)")


class TeamListResponse(PaginatedResponse):
    """Paginated team list response."""

    data: List[TeamResponse] = Field(..., description="List of teams")


class TeamStandingsResponse(BaseSchema):
    """Team championship standings response."""

    season: int = Field(..., description="Championship season")
    last_updated: str = Field(..., description="Last update timestamp")
    standings: List[TeamStanding] = Field(..., description="Team standings list")


# Import after definitions to avoid circular imports
try:
    from .driver import DriverBasic
    TeamResponse.model_rebuild()
except ImportError:
    pass