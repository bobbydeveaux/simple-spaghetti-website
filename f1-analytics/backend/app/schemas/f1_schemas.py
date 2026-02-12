"""
Pydantic schemas for F1 data validation and serialization.

This module defines schemas for validating data from external APIs
and converting it to database models.
"""

from datetime import datetime, date
from decimal import Decimal
from typing import Optional, List, Union
from pydantic import BaseModel, Field, validator, root_validator


class DriverCreate(BaseModel):
    """Schema for creating a new driver."""
    driver_code: str = Field(..., min_length=3, max_length=3, description="3-letter driver code")
    driver_name: str = Field(..., min_length=1, max_length=100, description="Full driver name")
    nationality: Optional[str] = Field(None, max_length=50, description="Driver nationality")
    date_of_birth: Optional[date] = Field(None, description="Driver birth date")
    current_team_id: Optional[int] = Field(None, description="Current team ID")
    current_elo_rating: int = Field(1500, description="Current ELO rating")

    @validator('driver_code')
    def validate_driver_code(cls, v):
        if not v.isupper():
            v = v.upper()
        if not v.isalpha():
            raise ValueError('Driver code must contain only letters')
        return v

    @validator('date_of_birth')
    def validate_birth_date(cls, v):
        if v and v > date.today():
            raise ValueError('Birth date cannot be in the future')
        return v


class TeamCreate(BaseModel):
    """Schema for creating a new team/constructor."""
    team_name: str = Field(..., min_length=1, max_length=100, description="Team name")
    nationality: Optional[str] = Field(None, max_length=50, description="Team nationality")
    team_color: Optional[str] = Field(None, max_length=7, description="Hex color code")
    current_elo_rating: int = Field(1500, description="Current ELO rating")

    @validator('team_color')
    def validate_team_color(cls, v):
        if v and not (v.startswith('#') and len(v) == 7):
            raise ValueError('Team color must be a valid hex color code (e.g., #FF0000)')
        return v


class CircuitCreate(BaseModel):
    """Schema for creating a new circuit."""
    circuit_name: str = Field(..., min_length=1, max_length=100, description="Circuit name")
    location: str = Field(..., min_length=1, max_length=100, description="Circuit location")
    country: str = Field(..., min_length=1, max_length=50, description="Country")
    track_length_km: Optional[Decimal] = Field(None, ge=0, description="Track length in kilometers")
    track_type: str = Field("permanent", description="Track type (street/permanent)")

    @validator('track_type')
    def validate_track_type(cls, v):
        valid_types = ['street', 'permanent']
        if v.lower() not in valid_types:
            raise ValueError(f'Track type must be one of: {valid_types}')
        return v.lower()


class RaceCreate(BaseModel):
    """Schema for creating a new race."""
    season_year: int = Field(..., ge=1950, le=2030, description="Season year")
    round_number: int = Field(..., ge=1, le=30, description="Round number in season")
    circuit_id: int = Field(..., description="Circuit ID")
    race_name: str = Field(..., min_length=1, max_length=100, description="Race name")
    race_date: date = Field(..., description="Race date")
    status: str = Field("scheduled", description="Race status")

    @validator('status')
    def validate_status(cls, v):
        valid_statuses = ['scheduled', 'completed', 'cancelled']
        if v.lower() not in valid_statuses:
            raise ValueError(f'Race status must be one of: {valid_statuses}')
        return v.lower()


class RaceResultCreate(BaseModel):
    """Schema for creating a race result."""
    race_id: int = Field(..., description="Race ID")
    driver_id: int = Field(..., description="Driver ID")
    team_id: int = Field(..., description="Team ID")
    grid_position: Optional[int] = Field(None, ge=1, description="Starting grid position")
    final_position: Optional[int] = Field(None, ge=1, description="Final race position")
    points: Optional[Decimal] = Field(None, ge=0, description="Points awarded")
    fastest_lap_time: Optional[str] = Field(None, description="Fastest lap time")
    status: str = Field("finished", description="Result status")

    @validator('status')
    def validate_status(cls, v):
        valid_statuses = ['finished', 'retired', 'dnf', 'disqualified']
        if v.lower() not in valid_statuses:
            raise ValueError(f'Result status must be one of: {valid_statuses}')
        return v.lower()

    @validator('fastest_lap_time')
    def validate_lap_time(cls, v):
        if v and not cls._is_valid_lap_time(v):
            raise ValueError('Lap time must be in format MM:SS.mmm or SS.mmm')
        return v

    @staticmethod
    def _is_valid_lap_time(time_str: str) -> bool:
        """Validate lap time format."""
        import re
        # Match formats like "1:23.456" or "83.456"
        pattern = r'^(\d{1,2}:)?\d{1,3}\.\d{3}$'
        return bool(re.match(pattern, time_str))


class QualifyingResultCreate(BaseModel):
    """Schema for creating a qualifying result."""
    race_id: int = Field(..., description="Race ID")
    driver_id: int = Field(..., description="Driver ID")
    team_id: int = Field(..., description="Team ID")
    q1_time: Optional[str] = Field(None, description="Q1 session time")
    q2_time: Optional[str] = Field(None, description="Q2 session time")
    q3_time: Optional[str] = Field(None, description="Q3 session time")
    final_grid_position: int = Field(..., ge=1, description="Final qualifying position")

    @validator('q1_time', 'q2_time', 'q3_time')
    def validate_qualifying_times(cls, v):
        if v and not RaceResultCreate._is_valid_lap_time(v):
            raise ValueError('Qualifying time must be in format MM:SS.mmm or SS.mmm')
        return v


class WeatherDataCreate(BaseModel):
    """Schema for creating weather data."""
    race_id: int = Field(..., description="Race ID")
    temperature_celsius: Optional[Decimal] = Field(None, description="Temperature in Celsius")
    precipitation_mm: Optional[Decimal] = Field(None, ge=0, description="Precipitation in mm")
    wind_speed_kph: Optional[Decimal] = Field(None, ge=0, description="Wind speed in km/h")
    conditions: str = Field("dry", description="Weather conditions")

    @validator('conditions')
    def validate_conditions(cls, v):
        valid_conditions = ['dry', 'wet', 'mixed']
        if v.lower() not in valid_conditions:
            raise ValueError(f'Weather conditions must be one of: {valid_conditions}')
        return v.lower()


# Response schemas for API endpoints
class DriverResponse(BaseModel):
    """Schema for driver API responses."""
    driver_id: int
    driver_code: str
    driver_name: str
    nationality: Optional[str]
    date_of_birth: Optional[date]
    current_team_id: Optional[int]
    current_elo_rating: int
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class TeamResponse(BaseModel):
    """Schema for team API responses."""
    team_id: int
    team_name: str
    nationality: Optional[str]
    team_color: Optional[str]
    current_elo_rating: int
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class RaceResponse(BaseModel):
    """Schema for race API responses."""
    race_id: int
    season_year: int
    round_number: int
    circuit_id: int
    race_name: str
    race_date: date
    status: str
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class RaceResultResponse(BaseModel):
    """Schema for race result API responses."""
    result_id: int
    race_id: int
    driver_id: int
    team_id: int
    grid_position: Optional[int]
    final_position: Optional[int]
    points: Optional[Decimal]
    fastest_lap_time: Optional[str]
    status: str
    created_at: datetime

    class Config:
        from_attributes = True


class WeatherSummary(BaseModel):
    """Schema for simplified weather data."""
    temperature_celsius: Optional[float] = Field(None, description="Temperature in Celsius")
    humidity_percent: Optional[int] = Field(None, ge=0, le=100, description="Humidity percentage")
    precipitation_mm: Optional[float] = Field(None, ge=0, description="Precipitation in mm")
    wind_speed_kph: Optional[float] = Field(None, ge=0, description="Wind speed in km/h")
    wind_direction_degrees: Optional[int] = Field(None, ge=0, le=360, description="Wind direction")
    weather_condition: Optional[str] = Field(None, description="Main weather condition")
    weather_description: Optional[str] = Field(None, description="Detailed weather description")
    conditions: str = Field("dry", description="F1-specific conditions classification")

    @validator('conditions')
    def classify_conditions(cls, v, values):
        """Automatically classify F1 conditions based on weather data."""
        # Auto-classify based on weather data
        weather_condition = values.get('weather_condition', '').lower()
        precipitation = values.get('precipitation_mm', 0) or 0

        if precipitation > 1.0 or 'rain' in weather_condition or 'storm' in weather_condition:
            return 'wet'
        elif precipitation > 0.1 or 'drizzle' in weather_condition:
            return 'mixed'
        else:
            return 'dry'


# Bulk operation schemas
class BulkRaceResultsCreate(BaseModel):
    """Schema for bulk race result creation."""
    race_id: int
    results: List[RaceResultCreate]

    @validator('results')
    def validate_results_length(cls, v):
        if len(v) > 30:  # Reasonable upper bound for F1 grid
            raise ValueError('Cannot create more than 30 race results at once')
        return v