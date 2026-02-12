"""Prediction ORM model."""
from datetime import datetime
from typing import Optional

from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Numeric, UniqueConstraint, Index, CheckConstraint
from sqlalchemy.orm import relationship

from app.database import Base


class Prediction(Base):
    """
    Prediction entity representing ML model predictions for race outcomes.

    Stores predicted win probability for each driver in a race,
    including model version and timestamp for tracking.
    Table is partitioned by race_id for improved query performance.
    """

    __tablename__ = "predictions"

    prediction_id = Column(Integer, primary_key=True, index=True)
    race_id = Column(Integer, ForeignKey("races.race_id"), nullable=False)
    driver_id = Column(Integer, ForeignKey("drivers.driver_id"), nullable=False)
    predicted_win_probability = Column(Numeric(5, 2), nullable=False)  # Range: 0.00 to 100.00
    model_version = Column(String(50), nullable=False)
    prediction_timestamp = Column(DateTime, default=datetime.utcnow, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    # Relationships
    race = relationship("Race", back_populates="predictions")
    driver = relationship("Driver", back_populates="predictions")

    # Constraints
    __table_args__ = (
        UniqueConstraint("race_id", "driver_id", "model_version", name="uq_predictions_race_driver_model"),
        CheckConstraint(
            predicted_win_probability.between(0, 100),
            name="ck_predictions_probability_range"
        ),
        Index("idx_predictions_race", "race_id"),
        Index("idx_predictions_timestamp", "prediction_timestamp"),
    )

    def __repr__(self) -> str:
        return f"<Prediction(race_id={self.race_id}, driver_id={self.driver_id}, prob={self.predicted_win_probability}%)>"

    @property
    def probability_decimal(self) -> float:
        """Get probability as decimal (0.0 to 1.0)."""
        return float(self.predicted_win_probability) / 100

    @property
    def is_favorite(self) -> bool:
        """Check if this driver is predicted to have highest win probability."""
        # This would need to be calculated relative to other predictions in the same race
        return float(self.predicted_win_probability) >= 50.0

    @property
    def confidence_level(self) -> str:
        """Get confidence level based on probability."""
        prob = float(self.predicted_win_probability)
        if prob >= 60:
            return "high"
        elif prob >= 30:
            return "medium"
        else:
            return "low"

    @property
    def model_name(self) -> str:
        """Extract model name from version string."""
        # Assuming format like "random_forest_v1", "xgboost_v2", etc.
        return self.model_version.split('_')[0] if '_' in self.model_version else self.model_version

    @property
    def model_iteration(self) -> Optional[str]:
        """Extract model iteration from version string."""
        parts = self.model_version.split('_')
        return parts[-1] if len(parts) > 1 and parts[-1].startswith('v') else None