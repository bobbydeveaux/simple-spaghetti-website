"""Race ORM model."""
from datetime import datetime, date
from typing import List

from sqlalchemy import Column, Integer, String, Date, DateTime, ForeignKey, UniqueConstraint, Index, CheckConstraint
from sqlalchemy.orm import relationship

from app.database import Base


class Race(Base):
    """
    Race entity representing F1 Grand Prix races.

    Stores race information including season, round number, circuit, and status.
    Each race is uniquely identified by season year and round number.
    """

    __tablename__ = "races"

    race_id = Column(Integer, primary_key=True, index=True)
    season_year = Column(Integer, nullable=False)
    round_number = Column(Integer, nullable=False)
    circuit_id = Column(Integer, ForeignKey("circuits.circuit_id"))
    race_date = Column(Date, nullable=False)
    race_name = Column(String(100), nullable=False)
    status = Column(String(20), default="scheduled")
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    # Relationships
    circuit = relationship("Circuit", back_populates="races")
    race_results = relationship("RaceResult", back_populates="race")
    qualifying_results = relationship("QualifyingResult", back_populates="race")
    weather_data = relationship("WeatherData", back_populates="race", uselist=False)  # One-to-one
    predictions = relationship("Prediction", back_populates="race")
    prediction_accuracy = relationship("PredictionAccuracy", back_populates="race", uselist=False)  # One-to-one

    # Constraints
    __table_args__ = (
        UniqueConstraint("season_year", "round_number", name="uq_races_season_round"),
        CheckConstraint(
            status.in_(["scheduled", "completed", "cancelled"]),
            name="ck_races_status"
        ),
        Index("idx_races_date", "race_date"),
        Index("idx_races_season", "season_year", "round_number"),
        Index("idx_races_status", "status"),
    )

    def __repr__(self) -> str:
        return f"<Race(race_id={self.race_id}, {self.season_year} R{self.round_number}, '{self.race_name}')>"

    @property
    def is_completed(self) -> bool:
        """Check if race has been completed."""
        return self.status == "completed"

    @property
    def is_upcoming(self) -> bool:
        """Check if race is scheduled and in the future."""
        return self.status == "scheduled" and self.race_date >= date.today()

    @property
    def season_round_identifier(self) -> str:
        """Get season-round identifier for display."""
        return f"{self.season_year}-R{self.round_number:02d}"