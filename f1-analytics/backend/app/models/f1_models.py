"""
F1 Analytics SQLAlchemy models.

This module defines all the database models for F1 prediction analytics including
drivers, teams, circuits, races, results, and predictions.
"""

from datetime import datetime, timezone, date
from decimal import Decimal
from typing import Optional

from sqlalchemy import (
    Column, Integer, String, Date, DateTime, Decimal as SQLDecimal,
    Boolean, ForeignKey, Text, Index, CheckConstraint, UniqueConstraint,
    Enum as SQLEnum
)
from sqlalchemy.orm import relationship
import enum

from ..database import Base


class TrackType(enum.Enum):
    """Track type enumeration."""
    STREET = "street"
    PERMANENT = "permanent"


class RaceStatus(enum.Enum):
    """Race status enumeration."""
    SCHEDULED = "scheduled"
    COMPLETED = "completed"
    CANCELLED = "cancelled"


class ResultStatus(enum.Enum):
    """Result status enumeration."""
    FINISHED = "finished"
    RETIRED = "retired"
    DNF = "dnf"
    DISQUALIFIED = "disqualified"


class WeatherCondition(enum.Enum):
    """Weather condition enumeration."""
    DRY = "dry"
    WET = "wet"
    MIXED = "mixed"


class Driver(Base):
    """Driver model for Formula 1 drivers."""

    __tablename__ = "drivers"

    driver_id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    driver_code = Column(String(3), unique=True, nullable=False, index=True)
    driver_name = Column(String(100), nullable=False, index=True)
    nationality = Column(String(50), nullable=True)
    date_of_birth = Column(Date, nullable=True)
    current_team_id = Column(Integer, ForeignKey("teams.team_id"), nullable=True)
    current_elo_rating = Column(Integer, default=1500, nullable=False, index=True)

    # Timestamps
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)
    updated_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc), nullable=False)

    # Relationships
    current_team = relationship("Team", back_populates="drivers", foreign_keys=[current_team_id])
    race_results = relationship("RaceResult", back_populates="driver")
    qualifying_results = relationship("QualifyingResult", back_populates="driver")
    predictions = relationship("Prediction", back_populates="driver")

    # Indexes
    __table_args__ = (
        Index('idx_drivers_code', 'driver_code'),
        Index('idx_drivers_elo_desc', 'current_elo_rating', postgresql_using='btree', postgresql_ops={'current_elo_rating': 'DESC'}),
        Index('idx_drivers_team', 'current_team_id'),
        Index('idx_drivers_name', 'driver_name'),
    )

    def __repr__(self) -> str:
        return f"<Driver(driver_id={self.driver_id}, code='{self.driver_code}', name='{self.driver_name}')>"

    def to_dict(self) -> dict:
        """Convert driver to dictionary."""
        return {
            "driver_id": self.driver_id,
            "driver_code": self.driver_code,
            "driver_name": self.driver_name,
            "nationality": self.nationality,
            "date_of_birth": self.date_of_birth.isoformat() if self.date_of_birth else None,
            "current_team_id": self.current_team_id,
            "current_elo_rating": self.current_elo_rating,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None
        }


class Team(Base):
    """Team/Constructor model for Formula 1 teams."""

    __tablename__ = "teams"

    team_id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    team_name = Column(String(100), unique=True, nullable=False, index=True)
    nationality = Column(String(50), nullable=True)
    current_elo_rating = Column(Integer, default=1500, nullable=False, index=True)
    team_color = Column(String(7), nullable=True)  # Hex color code

    # Timestamps
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)
    updated_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc), nullable=False)

    # Relationships
    drivers = relationship("Driver", back_populates="current_team", foreign_keys=[Driver.current_team_id])
    race_results = relationship("RaceResult", back_populates="team")

    def __repr__(self) -> str:
        return f"<Team(team_id={self.team_id}, name='{self.team_name}')>"

    def to_dict(self) -> dict:
        """Convert team to dictionary."""
        return {
            "team_id": self.team_id,
            "team_name": self.team_name,
            "nationality": self.nationality,
            "current_elo_rating": self.current_elo_rating,
            "team_color": self.team_color,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None
        }


class Circuit(Base):
    """Circuit model for Formula 1 race tracks."""

    __tablename__ = "circuits"

    circuit_id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    circuit_name = Column(String(100), unique=True, nullable=False, index=True)
    location = Column(String(100), nullable=True)
    country = Column(String(50), nullable=True, index=True)
    track_length_km = Column(SQLDecimal(5, 2), nullable=True)
    track_type = Column(SQLEnum(TrackType), nullable=True)

    # Timestamps
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)

    # Relationships
    races = relationship("Race", back_populates="circuit")

    def __repr__(self) -> str:
        return f"<Circuit(circuit_id={self.circuit_id}, name='{self.circuit_name}', country='{self.country}')>"

    def to_dict(self) -> dict:
        """Convert circuit to dictionary."""
        return {
            "circuit_id": self.circuit_id,
            "circuit_name": self.circuit_name,
            "location": self.location,
            "country": self.country,
            "track_length_km": float(self.track_length_km) if self.track_length_km else None,
            "track_type": self.track_type.value if self.track_type else None,
            "created_at": self.created_at.isoformat() if self.created_at else None
        }


class Race(Base):
    """Race model for Formula 1 races."""

    __tablename__ = "races"

    race_id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    season_year = Column(Integer, nullable=False, index=True)
    round_number = Column(Integer, nullable=False)
    circuit_id = Column(Integer, ForeignKey("circuits.circuit_id"), nullable=False)
    race_date = Column(Date, nullable=False, index=True)
    race_name = Column(String(100), nullable=False)
    status = Column(SQLEnum(RaceStatus), default=RaceStatus.SCHEDULED, nullable=False, index=True)

    # Timestamps
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)

    # Relationships
    circuit = relationship("Circuit", back_populates="races")
    race_results = relationship("RaceResult", back_populates="race")
    qualifying_results = relationship("QualifyingResult", back_populates="race")
    weather_data = relationship("WeatherData", back_populates="race", uselist=False)
    predictions = relationship("Prediction", back_populates="race")
    prediction_accuracy = relationship("PredictionAccuracy", back_populates="race", uselist=False)

    # Constraints and indexes
    __table_args__ = (
        UniqueConstraint('season_year', 'round_number', name='uq_races_season_round'),
        Index('idx_races_date', 'race_date'),
        Index('idx_races_season_round', 'season_year', 'round_number'),
        Index('idx_races_status', 'status'),
        Index('idx_races_upcoming', 'race_date', postgresql_where=Column('status') == RaceStatus.SCHEDULED),
    )

    def __repr__(self) -> str:
        return f"<Race(race_id={self.race_id}, name='{self.race_name}', date='{self.race_date}')>"

    def to_dict(self) -> dict:
        """Convert race to dictionary."""
        return {
            "race_id": self.race_id,
            "season_year": self.season_year,
            "round_number": self.round_number,
            "circuit_id": self.circuit_id,
            "race_date": self.race_date.isoformat() if self.race_date else None,
            "race_name": self.race_name,
            "status": self.status.value,
            "created_at": self.created_at.isoformat() if self.created_at else None
        }

    def is_upcoming(self) -> bool:
        """Check if race is upcoming."""
        return self.status == RaceStatus.SCHEDULED and self.race_date >= date.today()

    def is_completed(self) -> bool:
        """Check if race is completed."""
        return self.status == RaceStatus.COMPLETED


class RaceResult(Base):
    """Race result model for driver finishing positions and points."""

    __tablename__ = "race_results"

    result_id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    race_id = Column(Integer, ForeignKey("races.race_id"), nullable=False, index=True)
    driver_id = Column(Integer, ForeignKey("drivers.driver_id"), nullable=False, index=True)
    team_id = Column(Integer, ForeignKey("teams.team_id"), nullable=False)
    grid_position = Column(Integer, nullable=True)
    final_position = Column(Integer, nullable=True, index=True)
    points = Column(SQLDecimal(4, 1), nullable=True)
    fastest_lap_time = Column(String(20), nullable=True)  # Store as string like "1:23.456"
    status = Column(SQLEnum(ResultStatus), default=ResultStatus.FINISHED, nullable=False)

    # Timestamps
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)

    # Relationships
    race = relationship("Race", back_populates="race_results")
    driver = relationship("Driver", back_populates="race_results")
    team = relationship("Team", back_populates="race_results")

    # Constraints and indexes
    __table_args__ = (
        UniqueConstraint('race_id', 'driver_id', name='uq_race_results_race_driver'),
        Index('idx_race_results_race', 'race_id'),
        Index('idx_race_results_driver', 'driver_id'),
        Index('idx_race_results_position', 'final_position'),
        Index('idx_race_results_points_desc', 'points', postgresql_using='btree', postgresql_ops={'points': 'DESC'}),
        CheckConstraint('grid_position >= 1 AND grid_position <= 30', name='ck_race_results_grid_position'),
        CheckConstraint('final_position >= 1 AND final_position <= 30', name='ck_race_results_final_position'),
        CheckConstraint('points >= 0', name='ck_race_results_points'),
    )

    def __repr__(self) -> str:
        return f"<RaceResult(result_id={self.result_id}, race_id={self.race_id}, driver_id={self.driver_id}, position={self.final_position})>"

    def to_dict(self) -> dict:
        """Convert race result to dictionary."""
        return {
            "result_id": self.result_id,
            "race_id": self.race_id,
            "driver_id": self.driver_id,
            "team_id": self.team_id,
            "grid_position": self.grid_position,
            "final_position": self.final_position,
            "points": float(self.points) if self.points else None,
            "fastest_lap_time": self.fastest_lap_time,
            "status": self.status.value,
            "created_at": self.created_at.isoformat() if self.created_at else None
        }

    def is_winner(self) -> bool:
        """Check if this result is a race winner."""
        return self.final_position == 1 and self.status == ResultStatus.FINISHED

    def is_podium(self) -> bool:
        """Check if this result is a podium finish."""
        return self.final_position and self.final_position <= 3 and self.status == ResultStatus.FINISHED

    def is_points_finish(self) -> bool:
        """Check if this result earned points."""
        return self.points and self.points > 0


class QualifyingResult(Base):
    """Qualifying result model for qualifying session times and grid positions."""

    __tablename__ = "qualifying_results"

    qualifying_id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    race_id = Column(Integer, ForeignKey("races.race_id"), nullable=False, index=True)
    driver_id = Column(Integer, ForeignKey("drivers.driver_id"), nullable=False, index=True)
    q1_time = Column(String(20), nullable=True)  # Store as string like "1:23.456"
    q2_time = Column(String(20), nullable=True)
    q3_time = Column(String(20), nullable=True)
    final_grid_position = Column(Integer, nullable=False, index=True)

    # Timestamps
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)

    # Relationships
    race = relationship("Race", back_populates="qualifying_results")
    driver = relationship("Driver", back_populates="qualifying_results")

    # Constraints and indexes
    __table_args__ = (
        UniqueConstraint('race_id', 'driver_id', name='uq_qualifying_results_race_driver'),
        Index('idx_qualifying_race', 'race_id'),
        Index('idx_qualifying_driver', 'driver_id'),
        Index('idx_qualifying_position', 'final_grid_position'),
        CheckConstraint('final_grid_position >= 1 AND final_grid_position <= 30', name='ck_qualifying_results_position'),
    )

    def __repr__(self) -> str:
        return f"<QualifyingResult(qualifying_id={self.qualifying_id}, race_id={self.race_id}, driver_id={self.driver_id}, position={self.final_grid_position})>"

    def to_dict(self) -> dict:
        """Convert qualifying result to dictionary."""
        return {
            "qualifying_id": self.qualifying_id,
            "race_id": self.race_id,
            "driver_id": self.driver_id,
            "q1_time": self.q1_time,
            "q2_time": self.q2_time,
            "q3_time": self.q3_time,
            "final_grid_position": self.final_grid_position,
            "created_at": self.created_at.isoformat() if self.created_at else None
        }


class WeatherData(Base):
    """Weather data model for race day conditions."""

    __tablename__ = "weather_data"

    weather_id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    race_id = Column(Integer, ForeignKey("races.race_id"), unique=True, nullable=False, index=True)
    temperature_celsius = Column(SQLDecimal(4, 1), nullable=True)
    precipitation_mm = Column(SQLDecimal(5, 2), nullable=True)
    wind_speed_kph = Column(SQLDecimal(5, 2), nullable=True)
    conditions = Column(SQLEnum(WeatherCondition), nullable=True)

    # Timestamps
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)

    # Relationships
    race = relationship("Race", back_populates="weather_data")

    def __repr__(self) -> str:
        return f"<WeatherData(weather_id={self.weather_id}, race_id={self.race_id}, conditions='{self.conditions}')>"

    def to_dict(self) -> dict:
        """Convert weather data to dictionary."""
        return {
            "weather_id": self.weather_id,
            "race_id": self.race_id,
            "temperature_celsius": float(self.temperature_celsius) if self.temperature_celsius else None,
            "precipitation_mm": float(self.precipitation_mm) if self.precipitation_mm else None,
            "wind_speed_kph": float(self.wind_speed_kph) if self.wind_speed_kph else None,
            "conditions": self.conditions.value if self.conditions else None,
            "created_at": self.created_at.isoformat() if self.created_at else None
        }


class Prediction(Base):
    """Prediction model for ML model predictions."""

    __tablename__ = "predictions"

    prediction_id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    race_id = Column(Integer, ForeignKey("races.race_id"), nullable=False, index=True)
    driver_id = Column(Integer, ForeignKey("drivers.driver_id"), nullable=False, index=True)
    predicted_win_probability = Column(SQLDecimal(5, 2), nullable=False, index=True)
    model_version = Column(String(50), nullable=False)
    prediction_timestamp = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False, index=True)

    # Timestamps
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)

    # Relationships
    race = relationship("Race", back_populates="predictions")
    driver = relationship("Driver", back_populates="predictions")

    # Constraints and indexes
    __table_args__ = (
        UniqueConstraint('race_id', 'driver_id', 'model_version', name='uq_predictions_race_driver_model'),
        Index('idx_predictions_race', 'race_id'),
        Index('idx_predictions_probability_desc', 'predicted_win_probability', postgresql_using='btree', postgresql_ops={'predicted_win_probability': 'DESC'}),
        Index('idx_predictions_timestamp_desc', 'prediction_timestamp', postgresql_using='btree', postgresql_ops={'prediction_timestamp': 'DESC'}),
        CheckConstraint('predicted_win_probability >= 0 AND predicted_win_probability <= 100', name='ck_predictions_probability_range'),
    )

    def __repr__(self) -> str:
        return f"<Prediction(prediction_id={self.prediction_id}, race_id={self.race_id}, driver_id={self.driver_id}, probability={self.predicted_win_probability}%)>"

    def to_dict(self) -> dict:
        """Convert prediction to dictionary."""
        return {
            "prediction_id": self.prediction_id,
            "race_id": self.race_id,
            "driver_id": self.driver_id,
            "predicted_win_probability": float(self.predicted_win_probability),
            "model_version": self.model_version,
            "prediction_timestamp": self.prediction_timestamp.isoformat() if self.prediction_timestamp else None,
            "created_at": self.created_at.isoformat() if self.created_at else None
        }


class PredictionAccuracy(Base):
    """Prediction accuracy model for evaluating model performance."""

    __tablename__ = "prediction_accuracy"

    accuracy_id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    race_id = Column(Integer, ForeignKey("races.race_id"), unique=True, nullable=False, index=True)
    brier_score = Column(SQLDecimal(6, 4), nullable=True)
    log_loss = Column(SQLDecimal(6, 4), nullable=True)
    correct_winner = Column(Boolean, nullable=True)
    top_3_accuracy = Column(Boolean, nullable=True)

    # Timestamps
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)

    # Relationships
    race = relationship("Race", back_populates="prediction_accuracy")

    # Indexes
    __table_args__ = (
        Index('idx_accuracy_race', 'race_id'),
        Index('idx_accuracy_brier', 'brier_score'),
        Index('idx_accuracy_correct_winner', 'correct_winner'),
    )

    def __repr__(self) -> str:
        return f"<PredictionAccuracy(accuracy_id={self.accuracy_id}, race_id={self.race_id}, brier_score={self.brier_score})>"

    def to_dict(self) -> dict:
        """Convert prediction accuracy to dictionary."""
        return {
            "accuracy_id": self.accuracy_id,
            "race_id": self.race_id,
            "brier_score": float(self.brier_score) if self.brier_score else None,
            "log_loss": float(self.log_loss) if self.log_loss else None,
            "correct_winner": self.correct_winner,
            "top_3_accuracy": self.top_3_accuracy,
            "created_at": self.created_at.isoformat() if self.created_at else None
        }