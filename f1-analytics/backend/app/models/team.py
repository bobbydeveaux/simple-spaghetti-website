"""
Team model for F1 Prediction Analytics.

This module defines the Team SQLAlchemy model representing Formula 1 constructor
teams with their information and ELO ratings.
"""

from datetime import datetime
from sqlalchemy import Column, Integer, String, DateTime
from sqlalchemy.orm import relationship

from app.database import Base


class Team(Base):
    """
    SQLAlchemy model for Formula 1 constructor teams.

    This model stores team/constructor information including team details
    and performance rating (ELO) used for predictions.

    Attributes:
        team_id: Primary key, unique identifier for team
        team_name: Official team/constructor name
        nationality: Team's base nationality/country
        current_elo_rating: Current ELO rating for team performance
        created_at: Timestamp when record was created
        updated_at: Timestamp when record was last updated
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

    def __repr__(self) -> str:
        """String representation of Team instance."""
        return f"<Team(id={self.team_id}, name='{self.team_name}', elo={self.current_elo_rating})>"

    def __str__(self) -> str:
        """Human-readable string representation."""
        return self.team_name
