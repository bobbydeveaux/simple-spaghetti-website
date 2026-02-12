"""
Team/Constructor model for F1 Prediction Analytics
"""

from sqlalchemy import Column, Integer, String, DateTime
from sqlalchemy.orm import relationship
from datetime import datetime
from api.database import Base


class Team(Base):
    """
    Team/Constructor ORM model representing F1 teams
    """
    __tablename__ = "teams"

    team_id = Column(Integer, primary_key=True, index=True)
    team_name = Column(String(100), unique=True, nullable=False)
    nationality = Column(String(50))
    current_elo_rating = Column(Integer, default=1500, index=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    drivers = relationship("Driver", back_populates="team")
    race_results = relationship("RaceResult", back_populates="team")

    def __repr__(self):
        return f"<Team(team_id={self.team_id}, name='{self.team_name}')>"