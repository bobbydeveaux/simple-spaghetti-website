"""
Race model for F1 Prediction Analytics.

This module defines the Race SQLAlchemy model representing Formula 1 Grand Prix
races with scheduling and status information.
"""

from datetime import datetime, date
from sqlalchemy import Column, Integer, String, Date, ForeignKey, DateTime, UniqueConstraint, CheckConstraint, Index
from sqlalchemy.orm import relationship

from app.database import Base


class Race(Base):
    """
    SQLAlchemy model for Formula 1 Grand Prix races.

    This model stores race information including scheduling, circuit association,
    and status tracking for the F1 calendar and prediction system.

    Attributes:
        race_id: Primary key, unique identifier for race
        season_year: Year of the F1 season (e.g., 2024, 2025)
        round_number: Round number within the season (1-24)
        circuit_id: Foreign key to circuit where race takes place
        race_date: Date when the race is scheduled/was held
        race_name: Official race name (e.g., "Monaco Grand Prix")
        status: Current status of race ('scheduled', 'completed', 'cancelled')
        created_at: Timestamp when record was created
        updated_at: Timestamp when record was last updated
    """

    __tablename__ = "races"

    race_id = Column(Integer, primary_key=True, index=True)
    season_year = Column(Integer, nullable=False, index=True)
    round_number = Column(Integer, nullable=False)
    circuit_id = Column(Integer, ForeignKey("circuits.circuit_id"), nullable=False)
    race_date = Column(Date, nullable=False, index=True)
    race_name = Column(String(100), nullable=False)
    status = Column(String(20), default="scheduled", index=True)  # scheduled, completed, cancelled
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    circuit = relationship("Circuit", back_populates="races")
    race_results = relationship("RaceResult", back_populates="race", cascade="all, delete-orphan")
    qualifying_results = relationship("QualifyingResult", back_populates="race", cascade="all, delete-orphan")
    weather_data = relationship("WeatherData", back_populates="race", uselist=False, cascade="all, delete-orphan")
    predictions = relationship("Prediction", back_populates="race", cascade="all, delete-orphan")
    prediction_accuracy = relationship("PredictionAccuracy", back_populates="race", uselist=False, cascade="all, delete-orphan")

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
        """String representation of Race instance."""
        return f"<Race(id={self.race_id}, name='{self.race_name}', year={self.season_year}, round={self.round_number}, status='{self.status}')>"

    def __str__(self) -> str:
        """Human-readable string representation."""
        return f"{self.race_name} {self.season_year} (Round {self.round_number})"

    @property
    def is_scheduled(self) -> bool:
        """Check if race is scheduled (not completed or cancelled)."""
        return self.status == "scheduled"

    @property
    def is_completed(self) -> bool:
        """Check if race has been completed."""
        return self.status == "completed"

    @property
    def is_upcoming(self) -> bool:
        """Check if race is scheduled and in the future."""
        return self.status == "scheduled" and self.race_date >= date.today()

    @property
    def season_round_key(self) -> str:
        """Unique key combining season and round."""
        return f"{self.season_year}-R{self.round_number:02d}"

    @property
    def season_round_identifier(self) -> str:
        """Get season-round identifier for display."""
        return f"{self.season_year}-R{self.round_number:02d}"
