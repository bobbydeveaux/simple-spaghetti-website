"""
Prediction Accuracy model for F1 Prediction Analytics
"""

from sqlalchemy import Column, Integer, ForeignKey, Numeric, Boolean, DateTime
from sqlalchemy.orm import relationship
from datetime import datetime
from api.database import Base


class PredictionAccuracy(Base):
    """
    Prediction Accuracy ORM model for tracking ML model performance
    """
    __tablename__ = "prediction_accuracy"

    accuracy_id = Column(Integer, primary_key=True, index=True)
    race_id = Column(Integer, ForeignKey("races.race_id"), unique=True, nullable=False)
    brier_score = Column(Numeric(6, 4))  # Lower is better, measures calibration
    log_loss = Column(Numeric(6, 4))     # Lower is better, measures prediction quality
    correct_winner = Column(Boolean)      # Did we predict the correct winner?
    top_3_accuracy = Column(Boolean)      # Was the actual winner in our top 3?
    created_at = Column(DateTime, default=datetime.utcnow)

    # Relationships
    race = relationship("Race", back_populates="prediction_accuracy")

    def __repr__(self):
        return f"<PredictionAccuracy(accuracy_id={self.accuracy_id}, race_id={self.race_id}, brier_score={self.brier_score}, correct_winner={self.correct_winner})>"