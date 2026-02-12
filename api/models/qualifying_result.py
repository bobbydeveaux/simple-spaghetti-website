"""
Qualifying Result model for F1 Prediction Analytics
"""

from sqlalchemy import Column, Integer, ForeignKey, Interval, DateTime, UniqueConstraint
from sqlalchemy.orm import relationship
from datetime import datetime
from api.database import Base


class QualifyingResult(Base):
    """
    Qualifying Result ORM model representing F1 qualifying results
    """
    __tablename__ = "qualifying_results"

    qualifying_id = Column(Integer, primary_key=True, index=True)
    race_id = Column(Integer, ForeignKey("races.race_id"), nullable=False, index=True)
    driver_id = Column(Integer, ForeignKey("drivers.driver_id"), nullable=False)
    q1_time = Column(Interval)
    q2_time = Column(Interval)
    q3_time = Column(Interval)
    final_grid_position = Column(Integer)
    created_at = Column(DateTime, default=datetime.utcnow)

    # Composite unique constraint
    __table_args__ = (
        UniqueConstraint('race_id', 'driver_id', name='_qualifying_race_driver_uc'),
    )

    # Relationships
    race = relationship("Race", back_populates="qualifying_results")
    driver = relationship("Driver")

    def __repr__(self):
        return f"<QualifyingResult(qualifying_id={self.qualifying_id}, race_id={self.race_id}, driver_id={self.driver_id}, position={self.final_grid_position})>"