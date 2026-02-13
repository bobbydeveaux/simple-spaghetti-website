"""
Pydantic schemas for race-related API operations.

This module provides schemas for race data validation,
serialization, and transformation.
"""

from datetime import date, datetime
from decimal import Decimal
from typing import Optional, List
from enum import Enum
from pydantic import BaseModel, Field, validator

from .base import BaseSchema, TimestampMixin, PaginatedResponse


class RaceStatus(str, Enum):
    """Race status enumeration."""
    SCHEDULED = "scheduled"
    COMPLETED = "completed"
    CANCELLED = "cancelled"


class ResultStatus(str, Enum):
    """Result status enumeration."""
    FINISHED = "finished"
    RETIRED = "retired"
    DNF = "dnf"
    DISQUALIFIED = "disqualified"


class WeatherCondition(str, Enum):
    """Weather condition enumeration."""
    DRY = "dry"
    WET = "wet"
    MIXED = "mixed"


class RaceBase(BaseSchema):
    """Base race schema with common fields."""

    season_year: int = Field(
        ...,
        ge=1950,
        le=2050,
        description="Racing season year"
    )
    round_number: int = Field(
        ...,
        ge=1,
        le=30,
        description="Round number in the season"
    )
    race_name: str = Field(
        ...,
        min_length=5,
        max_length=100,
        description="Official race name"
    )
    race_date: date = Field(
        ...,
        description="Race date"
    )
    circuit_id: int = Field(
        ...,
        gt=0,
        description="Circuit identifier"
    )

    @validator('race_name')
    def validate_race_name(cls, v):
        """Validate race name."""
        if not v.strip():
            raise ValueError('Race name cannot be empty')
        return v.strip()


class RaceCreate(RaceBase):
    """Schema for creating a new race."""

    status: Optional[RaceStatus] = Field(
        RaceStatus.SCHEDULED,
        description="Race status"
    )


class RaceUpdate(BaseModel):
    """Schema for updating a race."""

    race_name: Optional[str] = Field(
        None,
        min_length=5,
        max_length=100,
        description="Official race name"
    )
    race_date: Optional[date] = Field(
        None,
        description="Race date"
    )
    status: Optional[RaceStatus] = Field(
        None,
        description="Race status"
    )

    @validator('race_name')
    def validate_race_name(cls, v):
        """Validate race name."""
        if v is not None and not v.strip():
            raise ValueError('Race name cannot be empty')
        return v.strip() if v else v


class RaceResponse(RaceBase, TimestampMixin):
    """Schema for race response."""

    race_id: int = Field(..., description="Unique race identifier")
    status: RaceStatus = Field(..., description="Current race status")

    # Related data
    circuit: Optional['CircuitBasic'] = Field(None, description="Circuit information")
    weather_data: Optional['WeatherDataResponse'] = Field(None, description="Weather information")
    result_count: int = Field(0, description="Number of race results")
    prediction_count: int = Field(0, description="Number of predictions")

    @property
    def is_upcoming(self) -> bool:
        """Check if race is upcoming."""
        return self.status == RaceStatus.SCHEDULED and self.race_date >= date.today()

    @property
    def is_completed(self) -> bool:
        """Check if race is completed."""
        return self.status == RaceStatus.COMPLETED


class RaceBasic(BaseSchema):
    """Basic race information for nested responses."""

    race_id: int = Field(..., description="Unique race identifier")
    season_year: int = Field(..., description="Racing season year")
    round_number: int = Field(..., description="Round number in the season")
    race_name: str = Field(..., description="Official race name")
    race_date: date = Field(..., description="Race date")
    status: RaceStatus = Field(..., description="Current race status")


class CircuitBase(BaseSchema):
    """Base circuit schema."""

    circuit_name: str = Field(
        ...,
        min_length=5,
        max_length=100,
        description="Circuit name"
    )
    location: Optional[str] = Field(
        None,
        max_length=100,
        description="Circuit location"
    )
    country: Optional[str] = Field(
        None,
        max_length=50,
        description="Country"
    )
    track_length_km: Optional[Decimal] = Field(
        None,
        gt=0,
        le=50,
        description="Track length in kilometers"
    )


class CircuitResponse(CircuitBase, TimestampMixin):
    """Schema for circuit response."""

    circuit_id: int = Field(..., description="Unique circuit identifier")
    race_count: int = Field(0, description="Number of races at this circuit")


class CircuitBasic(BaseSchema):
    """Basic circuit information for nested responses."""

    circuit_id: int = Field(..., description="Unique circuit identifier")
    circuit_name: str = Field(..., description="Circuit name")
    country: Optional[str] = Field(None, description="Country")
    track_length_km: Optional[float] = Field(None, description="Track length in kilometers")


class WeatherDataBase(BaseSchema):
    """Base weather data schema."""

    temperature_celsius: Optional[Decimal] = Field(
        None,
        ge=-30,
        le=60,
        description="Temperature in Celsius"
    )
    precipitation_mm: Optional[Decimal] = Field(
        None,
        ge=0,
        le=200,
        description="Precipitation in millimeters"
    )
    wind_speed_kph: Optional[Decimal] = Field(
        None,
        ge=0,
        le=200,
        description="Wind speed in km/h"
    )
    conditions: Optional[WeatherCondition] = Field(
        None,
        description="Weather conditions"
    )


class WeatherDataResponse(WeatherDataBase, TimestampMixin):
    """Schema for weather data response."""

    weather_id: int = Field(..., description="Unique weather data identifier")
    race_id: int = Field(..., description="Associated race identifier")


class RaceResultBase(BaseSchema):
    """Base race result schema."""

    driver_id: int = Field(..., gt=0, description="Driver identifier")
    team_id: int = Field(..., gt=0, description="Team identifier")
    grid_position: Optional[int] = Field(
        None,
        ge=1,
        le=30,
        description="Starting grid position"
    )
    final_position: Optional[int] = Field(
        None,
        ge=1,
        le=30,
        description="Final finishing position"
    )
    points: Optional[Decimal] = Field(
        None,
        ge=0,
        le=50,
        description="Points earned"
    )
    fastest_lap_time: Optional[str] = Field(
        None,
        regex=r'^\d+:\d{2}\.\d{3}$',
        description="Fastest lap time (format: M:SS.mmm)"
    )
    status: Optional[ResultStatus] = Field(
        ResultStatus.FINISHED,
        description="Result status"
    )


class RaceResultResponse(RaceResultBase, TimestampMixin):
    """Schema for race result response."""

    result_id: int = Field(..., description="Unique result identifier")
    race_id: int = Field(..., description="Race identifier")

    # Related data
    driver: Optional['DriverBasic'] = Field(None, description="Driver information")
    team: Optional['TeamBasic'] = Field(None, description="Team information")

    @property
    def is_winner(self) -> bool:
        """Check if this result is a race winner."""
        return self.final_position == 1 and self.status == ResultStatus.FINISHED

    @property
    def is_podium(self) -> bool:
        """Check if this result is a podium finish."""
        return (self.final_position and self.final_position <= 3
                and self.status == ResultStatus.FINISHED)

    @property
    def is_points_finish(self) -> bool:
        """Check if this result earned points."""
        return self.points and self.points > 0


class QualifyingResultBase(BaseSchema):
    """Base qualifying result schema."""

    driver_id: int = Field(..., gt=0, description="Driver identifier")
    q1_time: Optional[str] = Field(
        None,
        regex=r'^\d+:\d{2}\.\d{3}$',
        description="Q1 time (format: M:SS.mmm)"
    )
    q2_time: Optional[str] = Field(
        None,
        regex=r'^\d+:\d{2}\.\d{3}$',
        description="Q2 time (format: M:SS.mmm)"
    )
    q3_time: Optional[str] = Field(
        None,
        regex=r'^\d+:\d{2}\.\d{3}$',
        description="Q3 time (format: M:SS.mmm)"
    )
    final_grid_position: int = Field(
        ...,
        ge=1,
        le=30,
        description="Final grid position"
    )


class QualifyingResultResponse(QualifyingResultBase, TimestampMixin):
    """Schema for qualifying result response."""

    qualifying_id: int = Field(..., description="Unique qualifying result identifier")
    race_id: int = Field(..., description="Race identifier")

    # Related data
    driver: Optional['DriverBasic'] = Field(None, description="Driver information")


class RaceWeekendSummary(BaseSchema):
    """Schema for complete race weekend summary."""

    race: RaceResponse = Field(..., description="Race information")
    weather: Optional[WeatherDataResponse] = Field(None, description="Weather data")
    qualifying_results: List[QualifyingResultResponse] = Field([], description="Qualifying results")
    race_results: List[RaceResultResponse] = Field([], description="Race results")
    predictions: List['PredictionResponse'] = Field([], description="Predictions")


class RaceCalendarResponse(BaseSchema):
    """Schema for race calendar response."""

    season: int = Field(..., description="Championship season")
    total_races: int = Field(..., description="Total number of races in season")
    completed_races: int = Field(..., description="Number of completed races")
    upcoming_races: int = Field(..., description="Number of upcoming races")
    races: List[RaceResponse] = Field(..., description="List of races")


class RaceListResponse(PaginatedResponse):
    """Paginated race list response."""

    data: List[RaceResponse] = Field(..., description="List of races")


# Import after definitions to avoid circular imports
try:
    from .driver import DriverBasic
    from .team import TeamBasic
    from .prediction import PredictionResponse
    RaceResultResponse.model_rebuild()
    QualifyingResultResponse.model_rebuild()
    RaceWeekendSummary.model_rebuild()
except ImportError:
    pass