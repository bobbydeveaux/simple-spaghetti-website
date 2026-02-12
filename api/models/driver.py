"""
Driver model for F1 Prediction Analytics
"""

from sqlalchemy import Column, Integer, String, Date, ForeignKey, DateTime
from sqlalchemy.orm import relationship
from datetime import datetime
from api.database import Base


class Driver(Base):
    """
    Driver ORM model representing F1 drivers
    """
    __tablename__ = "drivers"

    driver_id = Column(Integer, primary_key=True, index=True)
    driver_code = Column(String(3), unique=True, nullable=False, index=True)
    driver_name = Column(String(100), nullable=False)
    nationality = Column(String(50))
    date_of_birth = Column(Date)
    current_team_id = Column(Integer, ForeignKey("teams.team_id"))
    current_elo_rating = Column(Integer, default=1500, index=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    team = relationship("Team", back_populates="drivers")
    race_results = relationship("RaceResult", back_populates="driver")
    predictions = relationship("Prediction", back_populates="driver")

    def __repr__(self):
        return f"<Driver(driver_id={self.driver_id}, name='{self.driver_name}', code='{self.driver_code}')>"