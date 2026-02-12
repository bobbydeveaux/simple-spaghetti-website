"""
Prediction Accuracy Model

Represents accuracy metrics for ML predictions after races are completed.
Tracks various accuracy measures including Brier score, log loss, and classification accuracy.
"""

from datetime import datetime
from typing import TYPE_CHECKING
from decimal import Decimal

from sqlalchemy import (
    Column, Integer, Boolean, DateTime, ForeignKey, DECIMAL,
    Index, CheckConstraint
)
from sqlalchemy.orm import relationship

from ..database import Base

if TYPE_CHECKING:
    from .race import Race


class PredictionAccuracy(Base):
    """
    Prediction Accuracy model.

    Represents accuracy metrics for ML predictions after race completion.
    Calculated by comparing predictions against actual race results.

    One accuracy record per race, aggregating all predictions for that race.

    Attributes:
        accuracy_id: Primary key
        race_id: Foreign key to race (unique - one accuracy record per race)
        brier_score: Brier score (0-1, lower is better) for probabilistic accuracy
        log_loss: Log loss (0+, lower is better) for probabilistic accuracy
        correct_winner: Boolean indicating if winner was correctly predicted
        top_3_accuracy: Boolean indicating if top 3 was correctly predicted
        created_at: Record creation timestamp

    Relationships:
        race: Race these accuracy metrics apply to

    Accuracy Metrics:
        - Brier Score: Measures accuracy of probabilistic predictions (0 = perfect, 1 = worst)
        - Log Loss: Measures uncertainty of predictions relative to actual outcome
        - Correct Winner: Simple binary accuracy for race winner prediction
        - Top 3 Accuracy: Binary accuracy for podium predictions
    """

    __tablename__ = "prediction_accuracy"

    # Primary key
    accuracy_id = Column(Integer, primary_key=True, autoincrement=True)

    # Foreign key to race (unique - one accuracy record per race)
    race_id = Column(
        Integer,
        ForeignKey("races.race_id", ondelete="CASCADE"),
        nullable=False,
        unique=True,
        index=True
    )

    # Probabilistic accuracy metrics
    brier_score = Column(
        DECIMAL(6, 4),
        nullable=False,
        index=True
    )  # 0-1, lower is better

    log_loss = Column(
        DECIMAL(6, 4),
        nullable=False,
        index=True
    )  # 0+, lower is better

    # Classification accuracy metrics
    correct_winner = Column(Boolean, nullable=False, index=True)
    top_3_accuracy = Column(Boolean, nullable=False, index=True)

    # Additional metrics (can be added later)
    # mean_absolute_error = Column(DECIMAL(6, 4), nullable=True)
    # rank_correlation = Column(DECIMAL(6, 4), nullable=True)

    # Timestamps
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)

    # Relationships
    race = relationship(
        "Race",
        back_populates="prediction_accuracy",
        lazy="select"
    )

    # Constraints and indexes
    __table_args__ = (
        # Check constraints for metric validation
        CheckConstraint(
            "brier_score >= 0 AND brier_score <= 1",
            name="ck_prediction_accuracy_brier_score_range"
        ),
        CheckConstraint(
            "log_loss >= 0",
            name="ck_prediction_accuracy_log_loss_non_negative"
        ),
        # Performance indexes
        Index("idx_prediction_accuracy_race", "race_id"),
        Index("idx_prediction_accuracy_brier", "brier_score"),
        Index("idx_prediction_accuracy_log_loss", "log_loss"),
        Index("idx_prediction_accuracy_winner", "correct_winner"),
        Index("idx_prediction_accuracy_top3", "top_3_accuracy"),
    )

    def __repr__(self) -> str:
        return (f"<PredictionAccuracy(id={self.accuracy_id}, race_id={self.race_id}, "
                f"brier={self.brier_score}, winner={self.correct_winner})>")

    def __str__(self) -> str:
        if self.race:
            winner_status = "✓" if self.correct_winner else "✗"
            top3_status = "✓" if self.top_3_accuracy else "✗"
            return (f"{self.race.race_name} Accuracy: Winner {winner_status}, "
                    f"Top3 {top3_status}, Brier: {self.brier_score}")
        return f"Prediction Accuracy {self.accuracy_id}"

    @property
    def brier_score_percentage(self) -> float:
        """Get Brier score as percentage (0-100%)"""
        return float(self.brier_score) * 100

    @property
    def accuracy_grade(self) -> str:
        """
        Grade the prediction accuracy based on Brier score:
        - Excellent: < 0.1 (10%)
        - Good: 0.1-0.2 (10-20%)
        - Fair: 0.2-0.3 (20-30%)
        - Poor: 0.3-0.4 (30-40%)
        - Very Poor: > 0.4 (40%+)
        """
        score = float(self.brier_score)
        if score < 0.1:
            return "excellent"
        elif score < 0.2:
            return "good"
        elif score < 0.3:
            return "fair"
        elif score < 0.4:
            return "poor"
        else:
            return "very_poor"

    @property
    def is_good_prediction(self) -> bool:
        """Check if this represents a good prediction (Brier < 0.2 and winner correct)"""
        return float(self.brier_score) < 0.2 and self.correct_winner

    @property
    def log_loss_capped(self) -> float:
        """Get log loss capped at reasonable maximum for display"""
        return min(float(self.log_loss), 10.0)

    @property
    def overall_accuracy_score(self) -> float:
        """
        Calculate overall accuracy score (0-100) combining multiple metrics.
        Weighted combination of:
        - Brier score (40% weight, inverted)
        - Winner accuracy (30% weight)
        - Top 3 accuracy (20% weight)
        - Log loss (10% weight, inverted and capped)
        """
        # Brier score component (inverted, 40% weight)
        brier_component = (1 - float(self.brier_score)) * 0.4

        # Winner accuracy (30% weight)
        winner_component = (1.0 if self.correct_winner else 0.0) * 0.3

        # Top 3 accuracy (20% weight)
        top3_component = (1.0 if self.top_3_accuracy else 0.0) * 0.2

        # Log loss component (inverted and capped, 10% weight)
        log_loss_capped = min(float(self.log_loss), 5.0)  # Cap at 5
        log_loss_component = max(0, (1 - log_loss_capped / 5.0)) * 0.1

        total_score = (brier_component + winner_component +
                      top3_component + log_loss_component)

        return total_score * 100  # Convert to percentage

    def to_dict(self) -> dict:
        """Convert accuracy metrics to dictionary for API responses"""
        return {
            "accuracy_id": self.accuracy_id,
            "race_id": self.race_id,
            "brier_score": float(self.brier_score),
            "brier_score_percentage": self.brier_score_percentage,
            "log_loss": float(self.log_loss),
            "correct_winner": self.correct_winner,
            "top_3_accuracy": self.top_3_accuracy,
            "accuracy_grade": self.accuracy_grade,
            "overall_accuracy_score": self.overall_accuracy_score,
            "is_good_prediction": self.is_good_prediction
        }