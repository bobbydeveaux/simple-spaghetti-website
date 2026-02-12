"""RaceResult ORM model."""
from datetime import datetime, time
from typing import Optional

from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Numeric, Interval, UniqueConstraint, Index, CheckConstraint
from sqlalchemy.orm import relationship

from app.database import Base


class RaceResult(Base):
    """
    Race Result entity representing driver performance in a specific race.

    Stores grid position, final position, points scored, and fastest lap time.
    Table is partitioned by race_id for improved query performance.
    """

    __tablename__ = "race_results"

    result_id = Column(Integer, primary_key=True, index=True)
    race_id = Column(Integer, ForeignKey("races.race_id"), nullable=False)
    driver_id = Column(Integer, ForeignKey("drivers.driver_id"), nullable=False)
    team_id = Column(Integer, ForeignKey("teams.team_id"), nullable=False)
    grid_position = Column(Integer)  # Starting position from qualifying
    final_position = Column(Integer)  # Finishing position (1st, 2nd, etc.)
    points = Column(Numeric(4, 1))  # Points awarded (25.0, 18.0, etc.)
    fastest_lap_time = Column(Interval)  # Fastest lap time as interval
    status = Column(String(20), default="finished")
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    # Relationships
    race = relationship("Race", back_populates="race_results")
    driver = relationship("Driver", back_populates="race_results")
    team = relationship("Team", back_populates="race_results")

    # Constraints
    __table_args__ = (
        UniqueConstraint("race_id", "driver_id", name="uq_race_results_race_driver"),
        CheckConstraint(
            status.in_(["finished", "retired", "dnf", "disqualified"]),
            name="ck_race_results_status"
        ),
        Index("idx_race_results_race", "race_id"),
        Index("idx_race_results_driver", "driver_id"),
    )

    def __repr__(self) -> str:
        return f"<RaceResult(race_id={self.race_id}, driver_id={self.driver_id}, position={self.final_position})>"

    @property
    def is_points_finish(self) -> bool:
        """Check if driver finished in points (top 10)."""
        return self.final_position is not None and self.final_position <= 10 and self.status == "finished"

    @property
    def is_podium(self) -> bool:
        """Check if driver finished on podium (top 3)."""
        return self.final_position is not None and self.final_position <= 3 and self.status == "finished"

    @property
    def is_winner(self) -> bool:
        """Check if driver won the race."""
        return self.final_position == 1 and self.status == "finished"

    def fastest_lap_seconds(self) -> Optional[float]:
        """Convert fastest lap time to total seconds."""
        if self.fastest_lap_time:
            return self.fastest_lap_time.total_seconds()
        return None