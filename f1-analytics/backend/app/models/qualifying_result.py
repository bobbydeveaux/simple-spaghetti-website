"""
Qualifying Result Model

Represents F1 qualifying session results in the database.
Tracks Q1, Q2, Q3 times and final grid positions for each driver.
"""

from datetime import datetime, timedelta
from typing import Optional, TYPE_CHECKING

from sqlalchemy import (
    Column, Integer, DateTime, ForeignKey, Interval,
    Index, CheckConstraint, UniqueConstraint
)
from sqlalchemy.orm import relationship

from ..database import Base

if TYPE_CHECKING:
    from .race import Race
    from .driver import Driver


class QualifyingResult(Base):
    """
    F1 Qualifying Result model.

    Represents qualifying session results for each driver in a specific race.
    Tracks Q1, Q2, Q3 lap times and the final grid position.

    Attributes:
        qualifying_id: Primary key
        race_id: Foreign key to race
        driver_id: Foreign key to driver
        q1_time: Best lap time in Q1 session (NULL if didn't participate)
        q2_time: Best lap time in Q2 session (NULL if eliminated in Q1)
        q3_time: Best lap time in Q3 session (NULL if eliminated in Q1/Q2)
        final_grid_position: Final starting grid position
        created_at: Record creation timestamp

    Relationships:
        race: Race this qualifying result belongs to
        driver: Driver who achieved this result
    """

    __tablename__ = "qualifying_results"

    # Primary key
    qualifying_id = Column(Integer, primary_key=True, autoincrement=True)

    # Foreign keys
    race_id = Column(
        Integer,
        ForeignKey("races.race_id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )
    driver_id = Column(
        Integer,
        ForeignKey("drivers.driver_id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )

    # Qualifying session times
    q1_time = Column(Interval, nullable=True)  # Q1 best lap time
    q2_time = Column(Interval, nullable=True)  # Q2 best lap time (NULL if eliminated in Q1)
    q3_time = Column(Interval, nullable=True)  # Q3 best lap time (NULL if eliminated in Q1/Q2)

    # Final grid position
    final_grid_position = Column(Integer, nullable=False, index=True)

    # Timestamps
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)

    # Relationships
    race = relationship(
        "Race",
        back_populates="qualifying_results",
        lazy="select"
    )

    driver = relationship(
        "Driver",
        back_populates="qualifying_results",
        lazy="select"
    )

    # Constraints and indexes
    __table_args__ = (
        # Unique constraint - one qualifying result per driver per race
        UniqueConstraint(
            "race_id", "driver_id",
            name="uq_qualifying_results_race_driver"
        ),
        # Check constraints
        CheckConstraint(
            "final_grid_position >= 1 AND final_grid_position <= 30",
            name="ck_qualifying_results_grid_position_valid"
        ),
        # Performance indexes
        Index("idx_qualifying_results_race", "race_id"),
        Index("idx_qualifying_results_driver", "driver_id"),
        Index("idx_qualifying_results_grid_position", "final_grid_position"),
        # Composite indexes for common queries
        Index("idx_qualifying_results_race_driver", "race_id", "driver_id"),
        Index("idx_qualifying_results_race_position", "race_id", "final_grid_position"),
    )

    def __repr__(self) -> str:
        return (f"<QualifyingResult(id={self.qualifying_id}, race_id={self.race_id}, "
                f"driver_id={self.driver_id}, grid_pos={self.final_grid_position})>")

    def __str__(self) -> str:
        if self.driver and self.race:
            return f"{self.driver.driver_name} - {self.race.race_name} Qualifying: P{self.final_grid_position}"
        return f"Qualifying Result {self.qualifying_id}"

    @property
    def best_time(self) -> Optional[timedelta]:
        """Get the best qualifying time across all sessions"""
        times = [t for t in [self.q3_time, self.q2_time, self.q1_time] if t is not None]
        return min(times) if times else None

    @property
    def best_time_seconds(self) -> Optional[float]:
        """Get the best qualifying time in seconds"""
        best = self.best_time
        return best.total_seconds() if best else None

    @property
    def made_q2(self) -> bool:
        """Check if driver made it to Q2"""
        return self.q2_time is not None

    @property
    def made_q3(self) -> bool:
        """Check if driver made it to Q3"""
        return self.q3_time is not None

    @property
    def pole_position(self) -> bool:
        """Check if driver achieved pole position"""
        return self.final_grid_position == 1

    @property
    def front_row(self) -> bool:
        """Check if driver starts from front row"""
        return self.final_grid_position <= 2

    @property
    def top_10(self) -> bool:
        """Check if driver qualified in top 10"""
        return self.final_grid_position <= 10

    @property
    def q1_time_seconds(self) -> Optional[float]:
        """Get Q1 time in seconds"""
        return self.q1_time.total_seconds() if self.q1_time else None

    @property
    def q2_time_seconds(self) -> Optional[float]:
        """Get Q2 time in seconds"""
        return self.q2_time.total_seconds() if self.q2_time else None

    @property
    def q3_time_seconds(self) -> Optional[float]:
        """Get Q3 time in seconds"""
        return self.q3_time.total_seconds() if self.q3_time else None

    @property
    def session_eliminated(self) -> str:
        """Get the session where driver was eliminated"""
        if self.q3_time is not None:
            return "Q3" if self.final_grid_position > 10 else "Made Q3"
        elif self.q2_time is not None:
            return "Q2"
        else:
            return "Q1"