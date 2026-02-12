"""
Prediction Accuracy model for F1 Prediction Analytics.

This module defines the PredictionAccuracy SQLAlchemy model for tracking
the accuracy and performance metrics of ML model predictions.
"""

from datetime import datetime
from sqlalchemy import Column, Integer, ForeignKey, DateTime, Numeric, Boolean
from sqlalchemy.orm import relationship

from app.database import Base


class PredictionAccuracy(Base):
    """
    SQLAlchemy model for Formula 1 prediction accuracy metrics.

    This model stores accuracy metrics calculated after race completion
    to evaluate prediction model performance. Metrics include Brier score,
    log loss, and binary accuracy measures.

    Attributes:
        accuracy_id: Primary key, unique identifier for accuracy record
        race_id: Foreign key to completed race (unique - one record per race)
        brier_score: Brier score metric (lower is better, 0-1 scale)
        log_loss: Logarithmic loss metric (lower is better)
        correct_winner: Boolean indicating if predicted winner was correct
        top_3_accuracy: Boolean indicating if actual winner was in predicted top 3
        created_at: Timestamp when accuracy was calculated
    """

    __tablename__ = "prediction_accuracy"

    accuracy_id = Column(Integer, primary_key=True, index=True)
    race_id = Column(Integer, ForeignKey("races.race_id"), unique=True, nullable=False)
    brier_score = Column(Numeric(6, 4))  # e.g., 0.1234 (range 0-1)
    log_loss = Column(Numeric(6, 4))  # e.g., 2.3456
    correct_winner = Column(Boolean)  # True if predicted winner was correct
    top_3_accuracy = Column(Boolean)  # True if actual winner was in predicted top 3
    created_at = Column(DateTime, default=datetime.utcnow)

    # Relationships
    race = relationship("Race", back_populates="prediction_accuracy")

    def __repr__(self) -> str:
        """String representation of PredictionAccuracy instance."""
        return (
            f"<PredictionAccuracy(id={self.accuracy_id}, race_id={self.race_id}, "
            f"brier_score={self.brier_score}, correct_winner={self.correct_winner})>"
        )

    def __str__(self) -> str:
        """Human-readable string representation."""
        winner_status = "✓" if self.correct_winner else "✗"
        top3_status = "✓" if self.top_3_accuracy else "✗"
        return f"Winner: {winner_status}, Top-3: {top3_status}, Brier: {self.brier_score}"

    @property
    def excellent_prediction(self) -> bool:
        """Check if prediction quality is excellent (Brier score < 0.10)."""
        return self.brier_score is not None and self.brier_score < 0.10

    @property
    def good_prediction(self) -> bool:
        """Check if prediction quality is good (Brier score < 0.20)."""
        return self.brier_score is not None and self.brier_score < 0.20

    @property
    def poor_prediction(self) -> bool:
        """Check if prediction quality is poor (Brier score > 0.30)."""
        return self.brier_score is not None and self.brier_score > 0.30

    @property
    def accuracy_grade(self) -> str:
        """
        Return letter grade based on prediction accuracy.

        Grading scale:
        - A: Brier score < 0.10, correct winner
        - B: Brier score < 0.20 or correct winner
        - C: Brier score < 0.30 or top-3 accuracy
        - D: Brier score >= 0.30, no winner/top-3 accuracy
        """
        if self.brier_score is None:
            return "N/A"

        if self.brier_score < 0.10 and self.correct_winner:
            return "A"
        elif self.brier_score < 0.20 or self.correct_winner:
            return "B"
        elif self.brier_score < 0.30 or self.top_3_accuracy:
            return "C"
        else:
            return "D"

    @classmethod
    def calculate_brier_score(cls, predictions: list, actual_winner_id: int) -> float:
        """
        Calculate Brier score for a set of predictions.

        Brier score = mean((predicted_prob - actual_outcome)^2)
        where actual_outcome is 1 for winner, 0 for non-winners.

        Args:
            predictions: List of Prediction objects for the race
            actual_winner_id: driver_id of the actual race winner

        Returns:
            float: Brier score (0-1, lower is better)
        """
        if not predictions:
            return 1.0  # Worst possible score

        squared_errors = []
        for prediction in predictions:
            actual_outcome = 1.0 if prediction.driver_id == actual_winner_id else 0.0
            predicted_prob = prediction.probability_decimal
            squared_error = (predicted_prob - actual_outcome) ** 2
            squared_errors.append(squared_error)

        return sum(squared_errors) / len(squared_errors)

    @classmethod
    def calculate_log_loss(cls, predictions: list, actual_winner_id: int) -> float:
        """
        Calculate logarithmic loss for a set of predictions.

        Log loss = -log(predicted_probability_of_actual_winner)

        Args:
            predictions: List of Prediction objects for the race
            actual_winner_id: driver_id of the actual race winner

        Returns:
            float: Log loss (lower is better)
        """
        import math

        winner_prediction = next(
            (p for p in predictions if p.driver_id == actual_winner_id),
            None
        )

        if not winner_prediction:
            return float('inf')  # Worst possible score

        # Add small epsilon to avoid log(0)
        probability = max(winner_prediction.probability_decimal, 1e-15)
        return -math.log(probability)