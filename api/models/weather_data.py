"""
Weather Data model for F1 Prediction Analytics
"""

from sqlalchemy import Column, Integer, ForeignKey, Numeric, String, DateTime, CheckConstraint
from sqlalchemy.orm import relationship
from datetime import datetime
from api.database import Base


class WeatherData(Base):
    """
    Weather Data ORM model representing weather conditions for F1 races
    """
    __tablename__ = "weather_data"

    weather_id = Column(Integer, primary_key=True, index=True)
    race_id = Column(Integer, ForeignKey("races.race_id"), unique=True, nullable=False)
    temperature_celsius = Column(Numeric(4, 1))
    precipitation_mm = Column(Numeric(5, 2))
    wind_speed_kph = Column(Numeric(5, 2))
    conditions = Column(
        String(20),
        CheckConstraint("conditions IN ('dry', 'wet', 'mixed')")
    )
    created_at = Column(DateTime, default=datetime.utcnow)

    # Relationships
    race = relationship("Race", back_populates="weather_data")

    def __repr__(self):
        return f"<WeatherData(weather_id={self.weather_id}, race_id={self.race_id}, temp={self.temperature_celsius}°C, conditions='{self.conditions}')>"