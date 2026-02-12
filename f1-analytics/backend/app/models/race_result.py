"""
Race Result Model

Represents F1 race results in the database.
Tracks final race positions, points, lap times, and race status for each driver.
This table uses partitioning by race_id for performance with large datasets.
"""

from datetime import datetime, timedelta
from typing import Optional, TYPE_CHECKING
from decimal import Decimal

from sqlalchemy import (
    Column, Integer, String, DateTime, ForeignKey, DECIMAL, Interval,
    Index, CheckConstraint, UniqueConstraint
)
from sqlalchemy.orm import relationship

from ..database import Base

if TYPE_CHECKING:
    from .race import Race
    from .driver import Driver
    from .team import Team


class RaceResult(Base):
    """
    F1 Race Result model.

    Represents the final race results for each driver in a specific race.
    Includes grid position, final position, points scored, and race status.

    This table is designed to be partitioned by race_id ranges for performance
    when dealing with large historical datasets.

    Attributes:
        result_id: Primary key
        race_id: Foreign key to race
        driver_id: Foreign key to driver
        team_id: Foreign key to team (at time of race)
        grid_position: Starting grid position
        final_position: Final race position (NULL for DNF/DSQ)
        points: Championship points scored
        fastest_lap_time: Fastest lap time during race (NULL if not set)
        status: Race completion status
        created_at: Record creation timestamp

    Relationships:
        race: Race this result belongs to
        driver: Driver who achieved this result
        team: Team the driver was racing for
    """

    __tablename__ = "race_results"

    # Primary key
    result_id = Column(Integer, primary_key=True, autoincrement=True)

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
    team_id = Column(
        Integer,
        ForeignKey("teams.team_id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )

    # Race position information
    grid_position = Column(Integer, nullable=False)
    final_position = Column(Integer, nullable=True)  # NULL for DNF/DSQ

    # Performance metrics
    points = Column(DECIMAL(4, 1), nullable=False, default=0.0)
    fastest_lap_time = Column(Interval, nullable=True)  # Best lap time

    # Race completion status
    status = Column(String(20), nullable=False, default="finished", index=True)

    # Timestamps
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)

    # Relationships
    race = relationship(
        "Race",
        back_populates="race_results",
        lazy="select"
    )

    driver = relationship(
        "Driver",
        back_populates="race_results",
        lazy="select"
    )

    team = relationship(
        "Team",
        back_populates="race_results",
        lazy="select"
    )

    # Constraints and indexes
    __table_args__ = (
        # Unique constraint - one result per driver per race
        UniqueConstraint(
            "race_id", "driver_id",
            name="uq_race_results_race_driver"
        ),
        # Check constraints
        CheckConstraint(
            "grid_position >= 1 AND grid_position <= 30",
            name="ck_race_results_grid_position_valid"
        ),
        CheckConstraint(
            "final_position IS NULL OR (final_position >= 1 AND final_position <= 30)",
            name="ck_race_results_final_position_valid"
        ),
        CheckConstraint(
            "points >= 0",
            name="ck_race_results_points_non_negative"
        ),
        CheckConstraint(
            "status IN ('finished', 'retired', 'dnf', 'disqualified', 'dns')",
            name="ck_race_results_status"
        ),
        # Performance indexes
        Index("idx_race_results_race", "race_id"),
        Index("idx_race_results_driver", "driver_id"),
        Index("idx_race_results_team", "team_id"),
        Index("idx_race_results_final_position", "final_position"),
        Index("idx_race_results_points", "points"),
        Index("idx_race_results_status", "status"),
        # Composite indexes for common queries
        Index("idx_race_results_race_driver", "race_id", "driver_id"),
        Index("idx_race_results_race_position", "race_id", "final_position"),
    )

    def __repr__(self) -> str:
        return (f"<RaceResult(id={self.result_id}, race_id={self.race_id}, "
                f"driver_id={self.driver_id}, position={self.final_position}, "
                f"points={self.points})>")

    def __str__(self) -> str:
        if self.driver and self.race:
            position_str = f"P{self.final_position}" if self.final_position else self.status.upper()
            return f"{self.driver.driver_name} - {self.race.race_name}: {position_str} ({self.points} pts)"
        return f"Race Result {self.result_id}"

    @property
    def finished_race(self) -> bool:
        """Check if driver finished the race"""
        return self.status == "finished"

    @property
    def scored_points(self) -> bool:
        """Check if driver scored points"""
        return self.points > 0

    @property
    def on_podium(self) -> bool:
        """Check if driver finished on the podium (top 3)"""
        return self.final_position is not None and self.final_position <= 3

    @property
    def won_race(self) -> bool:
        """Check if driver won the race"""
        return self.final_position == 1

    @property
    def fastest_lap_seconds(self) -> Optional[float]:
        """Get fastest lap time in seconds"""
        if self.fastest_lap_time:
            return self.fastest_lap_time.total_seconds()
        return None

    @property
    def grid_penalty(self) -> Optional[int]:
        """Calculate grid penalty (positions lost from qualifying to grid)"""
        # This would need qualifying result data to calculate properly
        # For now, just indicate if started from back of grid
        if self.grid_position >= 20:
            return self.grid_position - 20
        return None