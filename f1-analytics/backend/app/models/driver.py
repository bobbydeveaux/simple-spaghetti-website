"""Driver ORM model."""
from datetime import datetime, date
from typing import Optional, List

from sqlalchemy import Column, Integer, String, Date, DateTime, ForeignKey, Index
from sqlalchemy.orm import relationship

from app.database import Base


class Driver(Base):
    """
    Driver entity representing F1 drivers.

    Tracks driver information including personal details, current team,
    and ELO rating for performance tracking.
    """

    __tablename__ = "drivers"

    driver_id = Column(Integer, primary_key=True, index=True)
    driver_code = Column(String(3), unique=True, nullable=False)
    driver_name = Column(String(100), nullable=False)
    nationality = Column(String(50))
    date_of_birth = Column(Date)
    current_team_id = Column(Integer, ForeignKey("teams.team_id"))
    current_elo_rating = Column(Integer, default=1500)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

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
        return f"<Driver(driver_id={self.driver_id}, driver_code='{self.driver_code}', name='{self.driver_name}')>"

    @property
    def age(self) -> Optional[int]:
        """Calculate driver's current age."""
        if self.date_of_birth:
            today = date.today()
            return today.year - self.date_of_birth.year - (
                (today.month, today.day) < (self.date_of_birth.month, self.date_of_birth.day)
            )
        return None