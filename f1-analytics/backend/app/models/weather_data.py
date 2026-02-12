"""WeatherData ORM model."""
from datetime import datetime
from typing import Optional

from sqlalchemy import Column, Integer, DateTime, ForeignKey, Numeric, String, CheckConstraint
from sqlalchemy.orm import relationship

from app.database import Base


class WeatherData(Base):
    """
    Weather Data entity representing race conditions.

    Stores weather information for each race including temperature,
    precipitation, wind speed, and overall conditions.
    One-to-one relationship with Race.
    """

    __tablename__ = "weather_data"

    weather_id = Column(Integer, primary_key=True, index=True)
    race_id = Column(Integer, ForeignKey("races.race_id"), unique=True, nullable=False)
    temperature_celsius = Column(Numeric(4, 1))  # Range: -99.9 to 999.9
    precipitation_mm = Column(Numeric(5, 2))  # Range: 0.00 to 999.99
    wind_speed_kph = Column(Numeric(5, 2))  # Range: 0.00 to 999.99
    conditions = Column(String(20))
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    # Relationships
    race = relationship("Race", back_populates="weather_data")

    # Constraints
    __table_args__ = (
        CheckConstraint(
            conditions.in_(["dry", "wet", "mixed"]),
            name="ck_weather_data_conditions"
        ),
    )

    def __repr__(self) -> str:
        return f"<WeatherData(race_id={self.race_id}, temp={self.temperature_celsius}°C, conditions='{self.conditions}')>"

    @property
    def temperature_fahrenheit(self) -> Optional[float]:
        """Convert temperature to Fahrenheit."""
        if self.temperature_celsius:
            return float(self.temperature_celsius) * 9 / 5 + 32
        return None

    @property
    def wind_speed_mph(self) -> Optional[float]:
        """Convert wind speed to miles per hour."""
        if self.wind_speed_kph:
            return float(self.wind_speed_kph) * 0.621371
        return None

    @property
    def precipitation_inches(self) -> Optional[float]:
        """Convert precipitation to inches."""
        if self.precipitation_mm:
            return float(self.precipitation_mm) * 0.0393701
        return None

    @property
    def is_wet_race(self) -> bool:
        """Check if race conditions are wet."""
        return self.conditions in ["wet", "mixed"]

    @property
    def is_dry_race(self) -> bool:
        """Check if race conditions are dry."""
        return self.conditions == "dry"

    @property
    def has_precipitation(self) -> bool:
        """Check if there was any precipitation."""
        return self.precipitation_mm is not None and self.precipitation_mm > 0