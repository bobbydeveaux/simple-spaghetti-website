"""
Weather Data Model

Represents weather conditions during F1 races.
Tracks temperature, precipitation, wind speed, and general conditions
that can significantly impact race strategy and outcomes.
"""

from datetime import datetime
from typing import TYPE_CHECKING
from decimal import Decimal

from sqlalchemy import (
    Column, Integer, String, DateTime, ForeignKey, DECIMAL,
    Index, CheckConstraint
)
from sqlalchemy.orm import relationship

from ..database import Base

if TYPE_CHECKING:
    from .race import Race


class WeatherData(Base):
    """
    Weather Data model.

    Represents weather conditions during F1 races. Weather is a crucial
    factor in race strategy and can significantly impact results.

    Each race has one weather record representing the general conditions
    during the race period.

    Attributes:
        weather_id: Primary key
        race_id: Foreign key to race (unique - one weather record per race)
        temperature_celsius: Ambient temperature in Celsius (1 decimal place)
        precipitation_mm: Precipitation amount in millimeters (2 decimal places)
        wind_speed_kph: Wind speed in kilometers per hour (2 decimal places)
        conditions: General weather conditions category
        created_at: Record creation timestamp

    Relationships:
        race: Race these weather conditions apply to
    """

    __tablename__ = "weather_data"

    # Primary key
    weather_id = Column(Integer, primary_key=True, autoincrement=True)

    # Foreign key to race (unique - one weather record per race)
    race_id = Column(
        Integer,
        ForeignKey("races.race_id", ondelete="CASCADE"),
        nullable=False,
        unique=True,
        index=True
    )

    # Temperature data
    temperature_celsius = Column(DECIMAL(4, 1), nullable=False)

    # Precipitation data
    precipitation_mm = Column(DECIMAL(5, 2), nullable=False, default=0.00)

    # Wind data
    wind_speed_kph = Column(DECIMAL(5, 2), nullable=False, default=0.00)

    # General conditions
    conditions = Column(String(20), nullable=False, default="dry", index=True)

    # Timestamps
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)

    # Relationships
    race = relationship(
        "Race",
        back_populates="weather_data",
        lazy="select"
    )

    # Constraints and indexes
    __table_args__ = (
        # Check constraints for data validation
        CheckConstraint(
            "temperature_celsius >= -20 AND temperature_celsius <= 60",
            name="ck_weather_data_temperature_range"
        ),
        CheckConstraint(
            "precipitation_mm >= 0",
            name="ck_weather_data_precipitation_non_negative"
        ),
        CheckConstraint(
            "wind_speed_kph >= 0",
            name="ck_weather_data_wind_speed_non_negative"
        ),
        CheckConstraint(
            "conditions IN ('dry', 'wet', 'mixed', 'overcast', 'sunny')",
            name="ck_weather_data_conditions"
        ),
        # Performance indexes
        Index("idx_weather_data_race", "race_id"),
        Index("idx_weather_data_conditions", "conditions"),
        Index("idx_weather_data_temperature", "temperature_celsius"),
    )

    def __repr__(self) -> str:
        return (f"<WeatherData(id={self.weather_id}, race_id={self.race_id}, "
                f"temp={self.temperature_celsius}°C, conditions='{self.conditions}')>")

    def __str__(self) -> str:
        if self.race:
            return (f"{self.race.race_name} Weather: {self.temperature_celsius}°C, "
                    f"{self.conditions}, {self.precipitation_mm}mm rain")
        return f"Weather Data {self.weather_id}"

    @property
    def is_dry(self) -> bool:
        """Check if conditions are dry"""
        return self.conditions == "dry" and self.precipitation_mm == 0

    @property
    def is_wet(self) -> bool:
        """Check if conditions are wet"""
        return self.conditions == "wet" or self.precipitation_mm > 0

    @property
    def is_mixed_conditions(self) -> bool:
        """Check if conditions are mixed (changing during race)"""
        return self.conditions == "mixed"

    @property
    def temperature_fahrenheit(self) -> float:
        """Get temperature in Fahrenheit"""
        return float(self.temperature_celsius) * 9/5 + 32

    @property
    def is_hot_weather(self) -> bool:
        """Check if weather is considered hot (>30°C)"""
        return self.temperature_celsius > 30

    @property
    def is_cold_weather(self) -> bool:
        """Check if weather is considered cold (<15°C)"""
        return self.temperature_celsius < 15

    @property
    def precipitation_inches(self) -> float:
        """Get precipitation in inches"""
        return float(self.precipitation_mm) / 25.4

    @property
    def wind_speed_mph(self) -> float:
        """Get wind speed in miles per hour"""
        return float(self.wind_speed_kph) * 0.621371

    @property
    def is_windy(self) -> bool:
        """Check if conditions are windy (>20 kph)"""
        return self.wind_speed_kph > 20

    @property
    def weather_impact_score(self) -> float:
        """
        Calculate a weather impact score (0-10) where higher values
        indicate more challenging conditions that could affect race outcomes.
        """
        score = 0.0

        # Temperature impact
        if self.temperature_celsius > 35 or self.temperature_celsius < 10:
            score += 2.0
        elif self.temperature_celsius > 30 or self.temperature_celsius < 15:
            score += 1.0

        # Precipitation impact
        if self.precipitation_mm > 10:
            score += 4.0  # Heavy rain
        elif self.precipitation_mm > 2:
            score += 2.0  # Light rain
        elif self.precipitation_mm > 0:
            score += 1.0  # Trace precipitation

        # Wind impact
        if self.wind_speed_kph > 30:
            score += 2.0  # Strong wind
        elif self.wind_speed_kph > 20:
            score += 1.0  # Moderate wind

        # Conditions impact
        if self.conditions == "mixed":
            score += 2.0  # Changing conditions
        elif self.conditions == "wet":
            score += 1.0

        return min(score, 10.0)  # Cap at 10