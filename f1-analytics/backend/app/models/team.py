"""
Team Model

Represents F1 constructors/teams in the database.
Tracks team information including Elo ratings for performance analysis.
"""

from datetime import datetime
from typing import List, TYPE_CHECKING

from sqlalchemy import Column, Integer, String, DateTime, Index
from sqlalchemy.orm import relationship

from ..database import Base

if TYPE_CHECKING:
    from .driver import Driver
    from .race_result import RaceResult


class Team(Base):
    """
    F1 Team/Constructor model.

    Represents Formula 1 constructors and their metadata including
    current Elo rating for performance tracking.

    Attributes:
        team_id: Primary key
        team_name: Official team name (unique)
        nationality: Team's nationality
        current_elo_rating: Current Elo rating for performance ranking (default: 1500)
        created_at: Record creation timestamp
        updated_at: Last update timestamp

    Relationships:
        drivers: Current drivers in this team
        race_results: All race results for this team
    """

    __tablename__ = "teams"

    # Primary key
    team_id = Column(Integer, primary_key=True, autoincrement=True)

    # Team information
    team_name = Column(String(100), nullable=False, unique=True, index=True)
    nationality = Column(String(50), nullable=False)

    # Performance tracking
    current_elo_rating = Column(Integer, nullable=False, default=1500, index=True)

    # Timestamps
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    updated_at = Column(
        DateTime,
        nullable=False,
        default=datetime.utcnow,
        onupdate=datetime.utcnow
    )

    # Relationships
    drivers = relationship(
        "Driver",
        back_populates="current_team",
        lazy="select"
    )

    race_results = relationship(
        "RaceResult",
        back_populates="team",
        lazy="select"
    )

    # Indexes for performance
    __table_args__ = (
        Index("idx_teams_elo_rating", "current_elo_rating"),
        Index("idx_teams_name", "team_name"),
    )

    def __repr__(self) -> str:
        return f"<Team(id={self.team_id}, name='{self.team_name}', elo={self.current_elo_rating})>"

    def __str__(self) -> str:
        return f"{self.team_name} (ELO: {self.current_elo_rating})"