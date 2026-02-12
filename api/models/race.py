"""
Race model for F1 Prediction Analytics
"""

from sqlalchemy import Column, Integer, String, Date, DateTime, ForeignKey, CheckConstraint, UniqueConstraint
from sqlalchemy.orm import relationship
from datetime import datetime
from api.database import Base


class Race(Base):
    """
    Race ORM model representing F1 races
    """
    __tablename__ = "races"

    race_id = Column(Integer, primary_key=True, index=True)
    season_year = Column(Integer, nullable=False, index=True)
    round_number = Column(Integer, nullable=False)
    circuit_id = Column(Integer, ForeignKey("circuits.circuit_id"), nullable=False)
    race_date = Column(Date, nullable=False, index=True)
    race_name = Column(String(100), nullable=False)
    status = Column(
        String(20),
        default="scheduled",
        CheckConstraint("status IN ('scheduled', 'completed', 'cancelled')"),
        index=True
    )
    created_at = Column(DateTime, default=datetime.utcnow)

    # Composite unique constraint
    __table_args__ = (
        UniqueConstraint('season_year', 'round_number', name='_season_round_uc'),
    )

    # Relationships
    circuit = relationship("Circuit", back_populates="races")
    race_results = relationship("RaceResult", back_populates="race")
    qualifying_results = relationship("QualifyingResult", back_populates="race")
    weather_data = relationship("WeatherData", back_populates="race", uselist=False)
    predictions = relationship("Prediction", back_populates="race")
    prediction_accuracy = relationship("PredictionAccuracy", back_populates="race", uselist=False)

    def __repr__(self):
        return f"<Race(race_id={self.race_id}, name='{self.race_name}', season={self.season_year}, round={self.round_number})>"