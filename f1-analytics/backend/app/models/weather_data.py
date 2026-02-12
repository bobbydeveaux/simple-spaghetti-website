"""
Weather Data model for F1 Prediction Analytics.

This module defines the WeatherData SQLAlchemy model representing
weather conditions during races, which significantly impact race outcomes.
"""

from datetime import datetime
from sqlalchemy import Column, Integer, ForeignKey, DateTime, Numeric, String
from sqlalchemy.orm import relationship

from app.database import Base


class WeatherData(Base):
    """
    SQLAlchemy model for Formula 1 race weather conditions.

    This model stores weather data for races, including temperature,
    precipitation, wind conditions, and track surface conditions.
    Weather is a crucial factor in race performance and predictions.

    Attributes:
        weather_id: Primary key, unique identifier for weather data
        race_id: Foreign key to the race (unique - one weather record per race)
        temperature_celsius: Air temperature in Celsius
        precipitation_mm: Precipitation amount in millimeters
        wind_speed_kph: Wind speed in kilometers per hour
        conditions: Overall conditions category (dry, wet, mixed)
        created_at: Timestamp when record was created
    """

    __tablename__ = "weather_data"

    weather_id = Column(Integer, primary_key=True, index=True)
    race_id = Column(Integer, ForeignKey("races.race_id"), unique=True, nullable=False)
    temperature_celsius = Column(Numeric(4, 1))  # e.g., 25.5°C
    precipitation_mm = Column(Numeric(5, 2))  # e.g., 12.50 mm
    wind_speed_kph = Column(Numeric(5, 2))  # e.g., 15.75 kph
    conditions = Column(String(20))  # dry, wet, mixed
    created_at = Column(DateTime, default=datetime.utcnow)

    # Relationships
    race = relationship("Race", back_populates="weather_data")

    def __repr__(self) -> str:
        """String representation of WeatherData instance."""
        return (
            f"<WeatherData(id={self.weather_id}, race_id={self.race_id}, "
            f"temp={self.temperature_celsius}°C, conditions='{self.conditions}')>"
        )

    def __str__(self) -> str:
        """Human-readable string representation."""
        return f"{self.temperature_celsius}°C, {self.conditions}"

    @property
    def is_dry_conditions(self) -> bool:
        """Check if race conditions are dry."""
        return self.conditions == "dry"

    @property
    def is_wet_conditions(self) -> bool:
        """Check if race conditions are wet."""
        return self.conditions in ("wet", "mixed")

    @property
    def high_temperature(self) -> bool:
        """Check if temperature is considered high (>30°C)."""
        return self.temperature_celsius and self.temperature_celsius > 30.0

    @property
    def low_temperature(self) -> bool:
        """Check if temperature is considered low (<15°C)."""
        return self.temperature_celsius and self.temperature_celsius < 15.0

    @property
    def windy_conditions(self) -> bool:
        """Check if wind speed is considered high (>20 kph)."""
        return self.wind_speed_kph and self.wind_speed_kph > 20.0

    @property
    def has_precipitation(self) -> bool:
        """Check if there was any measurable precipitation."""
        return self.precipitation_mm and self.precipitation_mm > 0.0

    @property
    def weather_summary(self) -> str:
        """Generate human-readable weather summary."""
        summary_parts = []

        if self.temperature_celsius:
            summary_parts.append(f"{self.temperature_celsius}°C")

        if self.conditions:
            summary_parts.append(self.conditions)

        if self.has_precipitation:
            summary_parts.append(f"{self.precipitation_mm}mm rain")

        if self.windy_conditions:
            summary_parts.append(f"{self.wind_speed_kph}kph wind")

        return ", ".join(summary_parts) if summary_parts else "No data"