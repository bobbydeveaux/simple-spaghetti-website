"""
Qualifying Result model for F1 Prediction Analytics.

This module defines the QualifyingResult SQLAlchemy model representing
qualifying session results that determine grid positions for races.
"""

from datetime import datetime
from sqlalchemy import Column, Integer, ForeignKey, DateTime, Interval, UniqueConstraint
from sqlalchemy.orm import relationship

from app.database import Base


class QualifyingResult(Base):
    """
    SQLAlchemy model for Formula 1 qualifying results.

    This model stores qualifying session results including lap times
    from Q1, Q2, and Q3 sessions, which determine grid positions
    for the race. Qualifying performance is a key feature for predictions.

    Attributes:
        qualifying_id: Primary key, unique identifier for qualifying result
        race_id: Foreign key to the race
        driver_id: Foreign key to the driver
        q1_time: Best lap time from Q1 session (interval)
        q2_time: Best lap time from Q2 session (interval, null if eliminated in Q1)
        q3_time: Best lap time from Q3 session (interval, null if eliminated before Q3)
        final_grid_position: Final grid position for race start
        created_at: Timestamp when record was created
    """

    __tablename__ = "qualifying_results"

    qualifying_id = Column(Integer, primary_key=True, index=True)
    race_id = Column(Integer, ForeignKey("races.race_id"), nullable=False, index=True)
    driver_id = Column(Integer, ForeignKey("drivers.driver_id"), nullable=False, index=True)
    q1_time = Column(Interval)  # Q1 lap time (all drivers participate)
    q2_time = Column(Interval)  # Q2 lap time (top 15 advance)
    q3_time = Column(Interval)  # Q3 lap time (top 10 compete for pole)
    final_grid_position = Column(Integer, nullable=False)  # 1-20 grid position
    created_at = Column(DateTime, default=datetime.utcnow)

    # Ensure unique constraint: one qualifying result per driver per race
    __table_args__ = (
        UniqueConstraint("race_id", "driver_id", name="uq_qualifying_race_driver"),
    )

    # Relationships
    race = relationship("Race", back_populates="qualifying_results")
    driver = relationship("Driver", back_populates="qualifying_results")

    def __repr__(self) -> str:
        """String representation of QualifyingResult instance."""
        return (
            f"<QualifyingResult(id={self.qualifying_id}, race_id={self.race_id}, "
            f"driver_id={self.driver_id}, grid_pos={self.final_grid_position})>"
        )

    def __str__(self) -> str:
        """Human-readable string representation."""
        return f"Grid P{self.final_grid_position}"

    @property
    def pole_position(self) -> bool:
        """Check if driver achieved pole position (P1 on grid)."""
        return self.final_grid_position == 1

    @property
    def front_row(self) -> bool:
        """Check if driver starts from front row (P1 or P2)."""
        return self.final_grid_position <= 2

    @property
    def top_10_start(self) -> bool:
        """Check if driver starts from top 10 (Q3 participants)."""
        return self.final_grid_position <= 10

    @property
    def advanced_to_q2(self) -> bool:
        """Check if driver advanced to Q2 session."""
        return self.q2_time is not None

    @property
    def advanced_to_q3(self) -> bool:
        """Check if driver advanced to Q3 session."""
        return self.q3_time is not None

    @property
    def best_qualifying_time(self) -> Interval:
        """Return the best lap time from any qualifying session."""
        times = [self.q1_time, self.q2_time, self.q3_time]
        valid_times = [t for t in times if t is not None]

        if not valid_times:
            return None

        # Return the fastest (minimum) time
        return min(valid_times)