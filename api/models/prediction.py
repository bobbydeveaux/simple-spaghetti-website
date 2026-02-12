"""
Prediction model for F1 Prediction Analytics
"""

from sqlalchemy import Column, Integer, ForeignKey, Numeric, String, DateTime, CheckConstraint, UniqueConstraint
from sqlalchemy.orm import relationship
from datetime import datetime
from api.database import Base


class Prediction(Base):
    """
    Prediction ORM model representing ML-generated race winner predictions
    """
    __tablename__ = "predictions"

    prediction_id = Column(Integer, primary_key=True, index=True)
    race_id = Column(Integer, ForeignKey("races.race_id"), nullable=False, index=True)
    driver_id = Column(Integer, ForeignKey("drivers.driver_id"), nullable=False)
    predicted_win_probability = Column(
        Numeric(5, 2),
        nullable=False,
        CheckConstraint("predicted_win_probability >= 0 AND predicted_win_probability <= 100")
    )
    model_version = Column(String(50), nullable=False)
    prediction_timestamp = Column(DateTime, default=datetime.utcnow, index=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    # Composite unique constraint - one prediction per race/driver/model version
    __table_args__ = (
        UniqueConstraint('race_id', 'driver_id', 'model_version', name='_race_driver_model_uc'),
    )

    # Relationships
    race = relationship("Race", back_populates="predictions")
    driver = relationship("Driver", back_populates="predictions")

    def __repr__(self):
        return f"<Prediction(prediction_id={self.prediction_id}, race_id={self.race_id}, driver_id={self.driver_id}, probability={self.predicted_win_probability}%)>"