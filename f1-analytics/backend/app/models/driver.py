"""
Driver model for F1 Prediction Analytics.

This module defines the Driver SQLAlchemy model representing Formula 1 drivers
with their personal information, team associations, and ELO ratings.
"""

from datetime import datetime, date
from typing import Optional
from sqlalchemy import Column, Integer, String, Date, ForeignKey, DateTime, Index
from sqlalchemy.orm import relationship

from app.database import Base


class Driver(Base):
    """
    SQLAlchemy model for Formula 1 drivers.

    This model stores driver information including personal details,
    current team association, and performance rating (ELO).

    Attributes:
        driver_id: Primary key, unique identifier for driver
        driver_code: Three-letter code (e.g., 'VER', 'HAM', 'LEC')
        driver_name: Full name of the driver
        nationality: Driver's nationality
        date_of_birth: Driver's birth date
        current_team_id: Foreign key to current team (nullable for retired drivers)
        current_elo_rating: Current ELO rating for performance ranking
        created_at: Timestamp when record was created
        updated_at: Timestamp when record was last updated
    """

    __tablename__ = "drivers"

    driver_id = Column(Integer, primary_key=True, index=True)
    driver_code = Column(String(3), unique=True, nullable=False, index=True)
    driver_name = Column(String(100), nullable=False)
    nationality = Column(String(50))
    date_of_birth = Column(Date)
    current_team_id = Column(Integer, ForeignKey("teams.team_id"), nullable=True)
    current_elo_rating = Column(Integer, default=1500, index=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    team = relationship("Team", back_populates="drivers")
    race_results = relationship("RaceResult", back_populates="driver")
    qualifying_results = relationship("QualifyingResult", back_populates="driver")
    predictions = relationship("Prediction", back_populates="driver")

    # Indexes
    __table_args__ = (
        Index("idx_drivers_code", "driver_code"),
        Index("idx_drivers_elo", "current_elo_rating"),
    )

    def __repr__(self) -> str:
        """String representation of Driver instance."""
        return f"<Driver(id={self.driver_id}, code='{self.driver_code}', name='{self.driver_name}', elo={self.current_elo_rating})>"

    def __str__(self) -> str:
        """Human-readable string representation."""
        return f"{self.driver_name} ({self.driver_code})"

    @property
    def age(self) -> Optional[int]:
        """Calculate driver's current age."""
        if self.date_of_birth:
            today = date.today()
            return today.year - self.date_of_birth.year - (
                (today.month, today.day) < (self.date_of_birth.month, self.date_of_birth.day)
            )
        return None
