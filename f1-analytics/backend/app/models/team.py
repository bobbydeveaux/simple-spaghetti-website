"""Team (Constructor) ORM model."""
from datetime import datetime
from typing import List

from sqlalchemy import Column, Integer, String, DateTime
from sqlalchemy.orm import relationship

from app.database import Base


class Team(Base):
    """
    Team (Constructor) entity representing F1 constructors.

    Tracks team information including name, nationality, and current ELO rating.
    """

    __tablename__ = "teams"

    team_id = Column(Integer, primary_key=True, index=True)
    team_name = Column(String(100), unique=True, nullable=False)
    nationality = Column(String(50))
    current_elo_rating = Column(Integer, default=1500)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    # Relationships
    drivers = relationship("Driver", back_populates="team")
    race_results = relationship("RaceResult", back_populates="team")

    def __repr__(self) -> str:
        return f"<Team(team_id={self.team_id}, team_name='{self.team_name}', elo={self.current_elo_rating})>"