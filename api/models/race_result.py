"""
Race Result model for F1 Prediction Analytics
"""

from sqlalchemy import Column, Integer, ForeignKey, Numeric, Interval, String, DateTime, CheckConstraint, UniqueConstraint
from sqlalchemy.orm import relationship
from datetime import datetime
from api.database import Base


class RaceResult(Base):
    """
    Race Result ORM model representing F1 race results
    """
    __tablename__ = "race_results"

    result_id = Column(Integer, primary_key=True, index=True)
    race_id = Column(Integer, ForeignKey("races.race_id"), nullable=False, index=True)
    driver_id = Column(Integer, ForeignKey("drivers.driver_id"), nullable=False, index=True)
    team_id = Column(Integer, ForeignKey("teams.team_id"), nullable=False)
    grid_position = Column(Integer)
    final_position = Column(Integer)
    points = Column(Numeric(4, 1))
    fastest_lap_time = Column(Interval)
    status = Column(
        String(20),
        default="finished",
        CheckConstraint("status IN ('finished', 'retired', 'dnf', 'disqualified')")
    )
    created_at = Column(DateTime, default=datetime.utcnow)

    # Composite unique constraint
    __table_args__ = (
        UniqueConstraint('race_id', 'driver_id', name='_race_driver_uc'),
    )

    # Relationships
    race = relationship("Race", back_populates="race_results")
    driver = relationship("Driver", back_populates="race_results")
    team = relationship("Team", back_populates="race_results")

    def __repr__(self):
        return f"<RaceResult(result_id={self.result_id}, race_id={self.race_id}, driver_id={self.driver_id}, position={self.final_position})>"