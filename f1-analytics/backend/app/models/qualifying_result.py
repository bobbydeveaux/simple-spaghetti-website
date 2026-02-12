"""QualifyingResult ORM model."""
from datetime import datetime
from typing import Optional

from sqlalchemy import Column, Integer, DateTime, ForeignKey, Interval, UniqueConstraint, Index
from sqlalchemy.orm import relationship

from app.database import Base


class QualifyingResult(Base):
    """
    Qualifying Result entity representing driver performance in qualifying sessions.

    Stores Q1, Q2, Q3 lap times and final grid position for race start.
    """

    __tablename__ = "qualifying_results"

    qualifying_id = Column(Integer, primary_key=True, index=True)
    race_id = Column(Integer, ForeignKey("races.race_id"), nullable=False)
    driver_id = Column(Integer, ForeignKey("drivers.driver_id"), nullable=False)
    q1_time = Column(Interval)  # Q1 lap time as interval
    q2_time = Column(Interval)  # Q2 lap time as interval (null if eliminated in Q1)
    q3_time = Column(Interval)  # Q3 lap time as interval (null if eliminated in Q1/Q2)
    final_grid_position = Column(Integer)  # Starting position on grid (1-20)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    # Relationships
    race = relationship("Race", back_populates="qualifying_results")
    driver = relationship("Driver", back_populates="qualifying_results")

    # Constraints
    __table_args__ = (
        UniqueConstraint("race_id", "driver_id", name="uq_qualifying_results_race_driver"),
        Index("idx_qualifying_race", "race_id"),
    )

    def __repr__(self) -> str:
        return f"<QualifyingResult(race_id={self.race_id}, driver_id={self.driver_id}, grid_pos={self.final_grid_position})>"

    @property
    def best_qualifying_time(self) -> Optional[float]:
        """Get the best qualifying time in seconds across all sessions."""
        times = []

        if self.q1_time:
            times.append(self.q1_time.total_seconds())
        if self.q2_time:
            times.append(self.q2_time.total_seconds())
        if self.q3_time:
            times.append(self.q3_time.total_seconds())

        return min(times) if times else None

    @property
    def made_q2(self) -> bool:
        """Check if driver progressed to Q2."""
        return self.q2_time is not None

    @property
    def made_q3(self) -> bool:
        """Check if driver progressed to Q3."""
        return self.q3_time is not None

    @property
    def is_pole_position(self) -> bool:
        """Check if driver achieved pole position."""
        return self.final_grid_position == 1

    def qualifying_session_times(self) -> dict:
        """Return all qualifying times in a structured format."""
        return {
            "q1": self.q1_time.total_seconds() if self.q1_time else None,
            "q2": self.q2_time.total_seconds() if self.q2_time else None,
            "q3": self.q3_time.total_seconds() if self.q3_time else None,
        }