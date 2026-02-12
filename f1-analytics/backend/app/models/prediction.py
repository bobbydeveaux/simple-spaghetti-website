"""
Prediction Model

Represents ML-generated predictions for F1 driver performance in races.
Tracks win probabilities and model versions for accuracy evaluation.
This table uses partitioning by race_id for performance with large datasets.
"""

from datetime import datetime
from typing import TYPE_CHECKING
from decimal import Decimal

from sqlalchemy import (
    Column, Integer, String, DateTime, ForeignKey, DECIMAL,
    Index, CheckConstraint, UniqueConstraint
)
from sqlalchemy.orm import relationship

from ..database import Base

if TYPE_CHECKING:
    from .race import Race
    from .driver import Driver


class Prediction(Base):
    """
    ML Prediction model.

    Represents machine learning predictions for driver performance in specific races.
    Stores win probability and model metadata for later accuracy evaluation.

    This table is designed to be partitioned by race_id ranges for performance
    when dealing with large prediction datasets across multiple seasons.

    Attributes:
        prediction_id: Primary key
        race_id: Foreign key to race
        driver_id: Foreign key to driver
        predicted_win_probability: Predicted probability of winning (0-100%)
        model_version: Version identifier of the ML model used
        prediction_timestamp: When prediction was generated
        created_at: Record creation timestamp

    Relationships:
        race: Race this prediction is for
        driver: Driver this prediction is about
    """

    __tablename__ = "predictions"

    # Primary key
    prediction_id = Column(Integer, primary_key=True, autoincrement=True)

    # Foreign keys
    race_id = Column(
        Integer,
        ForeignKey("races.race_id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )
    driver_id = Column(
        Integer,
        ForeignKey("drivers.driver_id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )

    # Prediction data
    predicted_win_probability = Column(
        DECIMAL(5, 2),
        nullable=False,
        index=True
    )  # Probability as percentage (0-100)

    # Model metadata
    model_version = Column(String(50), nullable=False, index=True)

    # Timing information
    prediction_timestamp = Column(
        DateTime,
        nullable=False,
        default=datetime.utcnow,
        index=True
    )

    # Record timestamp
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)

    # Relationships
    race = relationship(
        "Race",
        back_populates="predictions",
        lazy="select"
    )

    driver = relationship(
        "Driver",
        back_populates="predictions",
        lazy="select"
    )

    # Constraints and indexes
    __table_args__ = (
        # Unique constraint - one prediction per driver per race per model version
        UniqueConstraint(
            "race_id", "driver_id", "model_version",
            name="uq_predictions_race_driver_model"
        ),
        # Check constraints
        CheckConstraint(
            "predicted_win_probability >= 0 AND predicted_win_probability <= 100",
            name="ck_predictions_probability_range"
        ),
        # Performance indexes
        Index("idx_predictions_race", "race_id"),
        Index("idx_predictions_driver", "driver_id"),
        Index("idx_predictions_model", "model_version"),
        Index("idx_predictions_timestamp", "prediction_timestamp", postgresql_using='brin'),
        Index("idx_predictions_probability", "predicted_win_probability"),
        # Composite indexes for common queries
        Index("idx_predictions_race_driver", "race_id", "driver_id"),
        Index("idx_predictions_race_model", "race_id", "model_version"),
        Index("idx_predictions_race_probability", "race_id", "predicted_win_probability"),
    )

    def __repr__(self) -> str:
        return (f"<Prediction(id={self.prediction_id}, race_id={self.race_id}, "
                f"driver_id={self.driver_id}, prob={self.predicted_win_probability}%, "
                f"model='{self.model_version}')>")

    def __str__(self) -> str:
        if self.driver and self.race:
            return (f"{self.race.race_name} - {self.driver.driver_name}: "
                    f"{self.predicted_win_probability}% win chance ({self.model_version})")
        return f"Prediction {self.prediction_id}"

    @property
    def probability_decimal(self) -> float:
        """Get probability as decimal (0-1) instead of percentage"""
        return float(self.predicted_win_probability) / 100.0

    @property
    def is_favorite(self) -> bool:
        """Check if this driver is predicted to be the race favorite (>20% win prob)"""
        return self.predicted_win_probability > 20

    @property
    def is_longshot(self) -> bool:
        """Check if this driver is a longshot (<5% win prob)"""
        return self.predicted_win_probability < 5

    @property
    def confidence_category(self) -> str:
        """Categorize prediction confidence based on probability"""
        prob = float(self.predicted_win_probability)
        if prob >= 30:
            return "high_confidence"
        elif prob >= 15:
            return "medium_confidence"
        elif prob >= 5:
            return "low_confidence"
        else:
            return "very_low_confidence"

    @property
    def model_family(self) -> str:
        """Extract model family from version string (e.g., 'xgboost' from 'xgboost_v2.1')"""
        return self.model_version.split('_')[0] if '_' in self.model_version else self.model_version

    @property
    def days_until_race(self) -> int:
        """Calculate days between prediction and race (if race has date)"""
        if self.race and self.race.race_date:
            delta = self.race.race_date - self.prediction_timestamp.date()
            return delta.days
        return 0

    @property
    def is_recent_prediction(self) -> bool:
        """Check if prediction was made recently (within 7 days of race)"""
        return self.days_until_race <= 7

    def to_dict(self) -> dict:
        """Convert prediction to dictionary for API responses"""
        return {
            "prediction_id": self.prediction_id,
            "race_id": self.race_id,
            "driver_id": self.driver_id,
            "predicted_win_probability": float(self.predicted_win_probability),
            "model_version": self.model_version,
            "prediction_timestamp": self.prediction_timestamp.isoformat(),
            "confidence_category": self.confidence_category,
            "is_favorite": self.is_favorite,
            "is_longshot": self.is_longshot
        }