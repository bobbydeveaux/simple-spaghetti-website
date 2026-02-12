"""PredictionAccuracy ORM model."""
from datetime import datetime
from typing import Optional

from sqlalchemy import Column, Integer, DateTime, ForeignKey, Numeric, Boolean, Index
from sqlalchemy.orm import relationship

from app.database import Base


class PredictionAccuracy(Base):
    """
    Prediction Accuracy entity for tracking model performance.

    Stores accuracy metrics for predictions after race completion,
    including Brier score, log loss, and categorical accuracy measures.
    One-to-one relationship with Race.
    """

    __tablename__ = "prediction_accuracy"

    accuracy_id = Column(Integer, primary_key=True, index=True)
    race_id = Column(Integer, ForeignKey("races.race_id"), unique=True, nullable=False)
    brier_score = Column(Numeric(6, 4))  # Range: 0.0000 to 99.9999
    log_loss = Column(Numeric(6, 4))  # Range: 0.0000 to 99.9999
    correct_winner = Column(Boolean)  # True if predicted winner was actual winner
    top_3_accuracy = Column(Boolean)  # True if actual winner was in predicted top 3
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    # Relationships
    race = relationship("Race", back_populates="prediction_accuracy")

    # Constraints
    __table_args__ = (
        Index("idx_accuracy_race", "race_id"),
    )

    def __repr__(self) -> str:
        return f"<PredictionAccuracy(race_id={self.race_id}, brier={self.brier_score}, correct_winner={self.correct_winner})>"

    @property
    def accuracy_grade(self) -> str:
        """Get letter grade based on Brier score."""
        if self.brier_score is None:
            return "N/A"

        score = float(self.brier_score)
        if score <= 0.1:
            return "A"
        elif score <= 0.2:
            return "B"
        elif score <= 0.3:
            return "C"
        elif score <= 0.4:
            return "D"
        else:
            return "F"

    @property
    def is_good_prediction(self) -> bool:
        """Check if prediction quality is considered good (Brier score <= 0.2)."""
        return self.brier_score is not None and float(self.brier_score) <= 0.2

    @property
    def prediction_quality(self) -> str:
        """Get qualitative assessment of prediction quality."""
        if self.brier_score is None:
            return "unknown"

        score = float(self.brier_score)
        if score <= 0.15:
            return "excellent"
        elif score <= 0.25:
            return "good"
        elif score <= 0.4:
            return "fair"
        else:
            return "poor"

    def accuracy_summary(self) -> dict:
        """Return a summary of all accuracy metrics."""
        return {
            "brier_score": float(self.brier_score) if self.brier_score else None,
            "log_loss": float(self.log_loss) if self.log_loss else None,
            "correct_winner": self.correct_winner,
            "top_3_accuracy": self.top_3_accuracy,
            "grade": self.accuracy_grade,
            "quality": self.prediction_quality,
        }