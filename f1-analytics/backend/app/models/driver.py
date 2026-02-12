"""
Driver Model

Represents F1 drivers in the database.
Tracks driver information, team associations, and Elo ratings for performance analysis.
"""

from datetime import datetime, date
from typing import List, Optional, TYPE_CHECKING

from sqlalchemy import Column, Integer, String, Date, DateTime, ForeignKey, Index
from sqlalchemy.orm import relationship

from ..database import Base

if TYPE_CHECKING:
    from .team import Team
    from .race_result import RaceResult
    from .qualifying_result import QualifyingResult
    from .prediction import Prediction


class Driver(Base):
    """
    F1 Driver model.

    Represents Formula 1 drivers and their metadata including
    current team association and Elo rating for performance tracking.

    Attributes:
        driver_id: Primary key
        driver_code: Unique 3-letter driver code (e.g., 'HAM', 'VER', 'LEC')
        driver_name: Full driver name
        nationality: Driver's nationality
        date_of_birth: Driver's birth date
        current_team_id: Foreign key to current team (nullable for retired drivers)
        current_elo_rating: Current Elo rating for performance ranking (default: 1500)
        created_at: Record creation timestamp
        updated_at: Last update timestamp

    Relationships:
        current_team: Current team association
        race_results: All race results for this driver
        qualifying_results: All qualifying results for this driver
        predictions: Predictions about this driver's performance
    """

    __tablename__ = "drivers"

    # Primary key
    driver_id = Column(Integer, primary_key=True, autoincrement=True)

    # Driver information
    driver_code = Column(String(3), nullable=False, unique=True, index=True)
    driver_name = Column(String(100), nullable=False, index=True)
    nationality = Column(String(50), nullable=False)
    date_of_birth = Column(Date, nullable=False)

    # Team association (nullable for retired drivers)
    current_team_id = Column(
        Integer,
        ForeignKey("teams.team_id", ondelete="SET NULL"),
        nullable=True,
        index=True
    )

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
    current_team = relationship(
        "Team",
        back_populates="drivers",
        lazy="select"
    )

    race_results = relationship(
        "RaceResult",
        back_populates="driver",
        lazy="select"
    )

    qualifying_results = relationship(
        "QualifyingResult",
        back_populates="driver",
        lazy="select"
    )

    predictions = relationship(
        "Prediction",
        back_populates="driver",
        lazy="select"
    )

    # Indexes for performance
    __table_args__ = (
        Index("idx_drivers_code", "driver_code"),
        Index("idx_drivers_name", "driver_name"),
        Index("idx_drivers_elo_rating", "current_elo_rating"),
        Index("idx_drivers_team", "current_team_id"),
    )

    def __repr__(self) -> str:
        return f"<Driver(id={self.driver_id}, code='{self.driver_code}', name='{self.driver_name}')>"

    def __str__(self) -> str:
        team_name = self.current_team.team_name if self.current_team else "No Team"
        return f"{self.driver_name} ({self.driver_code}) - {team_name}"

    @property
    def age(self) -> Optional[int]:
        """Calculate current age of the driver"""
        if self.date_of_birth:
            today = date.today()
            return today.year - self.date_of_birth.year - (
                (today.month, today.day) < (self.date_of_birth.month, self.date_of_birth.day)
            )
        return None