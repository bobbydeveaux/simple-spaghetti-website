"""
Race Model

Represents F1 races in the database.
Tracks race information including season, location, date, and status.
"""

from datetime import datetime, date
from typing import List, TYPE_CHECKING, Optional

from sqlalchemy import Column, Integer, String, Date, DateTime, ForeignKey, Index, CheckConstraint, UniqueConstraint
from sqlalchemy.orm import relationship

from ..database import Base

if TYPE_CHECKING:
    from .circuit import Circuit
    from .race_result import RaceResult
    from .qualifying_result import QualifyingResult
    from .weather_data import WeatherData
    from .prediction import Prediction
    from .prediction_accuracy import PredictionAccuracy


class Race(Base):
    """
    F1 Race model.

    Represents Formula 1 races within a season, including scheduling
    and completion status.

    Attributes:
        race_id: Primary key
        season_year: F1 season year
        round_number: Round number within the season (1-24)
        circuit_id: Foreign key to circuit where race is held
        race_date: Date when race is/was held
        race_name: Official race name (e.g., "Monaco Grand Prix")
        status: Race status ('scheduled', 'completed', 'cancelled')
        created_at: Record creation timestamp

    Relationships:
        circuit: Circuit where race is held
        race_results: Results from this race
        qualifying_results: Qualifying session results
        weather_data: Weather conditions during race
        predictions: Predictions for this race
        prediction_accuracy: Accuracy metrics for predictions
    """

    __tablename__ = "races"

    # Primary key
    race_id = Column(Integer, primary_key=True, autoincrement=True)

    # Race scheduling information
    season_year = Column(Integer, nullable=False, index=True)
    round_number = Column(Integer, nullable=False)
    race_date = Column(Date, nullable=False, index=True)
    race_name = Column(String(100), nullable=False)

    # Circuit association
    circuit_id = Column(
        Integer,
        ForeignKey("circuits.circuit_id", ondelete="RESTRICT"),
        nullable=False,
        index=True
    )

    # Race status
    status = Column(String(20), nullable=False, default="scheduled", index=True)

    # Timestamps
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)

    # Relationships
    circuit = relationship(
        "Circuit",
        back_populates="races",
        lazy="select"
    )

    race_results = relationship(
        "RaceResult",
        back_populates="race",
        lazy="select",
        cascade="all, delete-orphan"
    )

    qualifying_results = relationship(
        "QualifyingResult",
        back_populates="race",
        lazy="select",
        cascade="all, delete-orphan"
    )

    weather_data = relationship(
        "WeatherData",
        back_populates="race",
        uselist=False,  # One-to-one relationship
        lazy="select",
        cascade="all, delete-orphan"
    )

    predictions = relationship(
        "Prediction",
        back_populates="race",
        lazy="select",
        cascade="all, delete-orphan"
    )

    prediction_accuracy = relationship(
        "PredictionAccuracy",
        back_populates="race",
        uselist=False,  # One-to-one relationship
        lazy="select",
        cascade="all, delete-orphan"
    )

    # Constraints and indexes
    __table_args__ = (
        # Unique constraint for season/round combination
        UniqueConstraint(
            "season_year", "round_number",
            name="uq_races_season_round"
        ),
        # Check constraints
        CheckConstraint(
            "status IN ('scheduled', 'completed', 'cancelled')",
            name="ck_races_status"
        ),
        CheckConstraint(
            "season_year >= 1950",
            name="ck_races_season_year_valid"
        ),
        CheckConstraint(
            "round_number >= 1 AND round_number <= 30",
            name="ck_races_round_number_valid"
        ),
        # Performance indexes
        Index("idx_races_season_year", "season_year"),
        Index("idx_races_date", "race_date"),
        Index("idx_races_status", "status"),
        Index("idx_races_season_round", "season_year", "round_number"),
    )

    def __repr__(self) -> str:
        return f"<Race(id={self.race_id}, {self.season_year} R{self.round_number}: {self.race_name})>"

    def __str__(self) -> str:
        return f"{self.season_year} {self.race_name} (Round {self.round_number})"

    @property
    def is_completed(self) -> bool:
        """Check if race is completed"""
        return self.status == "completed"

    @property
    def is_scheduled(self) -> bool:
        """Check if race is scheduled"""
        return self.status == "scheduled"

    @property
    def is_cancelled(self) -> bool:
        """Check if race is cancelled"""
        return self.status == "cancelled"

    @property
    def is_future_race(self) -> bool:
        """Check if race is in the future"""
        return self.race_date > date.today()

    @property
    def is_current_season(self) -> bool:
        """Check if race is in current season"""
        return self.season_year == date.today().year