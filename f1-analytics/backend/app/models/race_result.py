"""
Race Result model for F1 Prediction Analytics.

This module defines the RaceResult SQLAlchemy model representing the results
and performance data from completed Formula 1 races.
"""

from datetime import datetime
from sqlalchemy import Column, Integer, String, ForeignKey, DateTime, Numeric, Interval, UniqueConstraint
from sqlalchemy.orm import relationship

from app.database import Base


class RaceResult(Base):
    """
    SQLAlchemy model for Formula 1 race results.

    This model stores the results and performance data from completed races,
    including finishing positions, points scored, and lap times. This data
    is crucial for ELO calculations and ML model training.

    Attributes:
        result_id: Primary key, unique identifier for race result
        race_id: Foreign key to the race
        driver_id: Foreign key to the driver
        team_id: Foreign key to the team/constructor
        grid_position: Starting position on the grid (from qualifying)
        final_position: Final finishing position (1st, 2nd, etc.)
        points: Championship points awarded for this result
        fastest_lap_time: Fastest lap time achieved during race (interval)
        status: Result status (finished, retired, dnf, disqualified)
        created_at: Timestamp when record was created
    """

    __tablename__ = "race_results"

    result_id = Column(Integer, primary_key=True, index=True)
    race_id = Column(Integer, ForeignKey("races.race_id"), nullable=False, index=True)
    driver_id = Column(Integer, ForeignKey("drivers.driver_id"), nullable=False, index=True)
    team_id = Column(Integer, ForeignKey("teams.team_id"), nullable=False)
    grid_position = Column(Integer)  # Starting position
    final_position = Column(Integer)  # Finishing position (null if DNF)
    points = Column(Numeric(4, 1), default=0.0)  # Championship points (e.g., 25.0, 18.0)
    fastest_lap_time = Column(Interval)  # PostgreSQL interval type for lap times
    status = Column(String(20), default="finished")  # finished, retired, dnf, disqualified
    created_at = Column(DateTime, default=datetime.utcnow)

    # Ensure unique constraint: one result per driver per race
    __table_args__ = (
        UniqueConstraint("race_id", "driver_id", name="uq_race_result_race_driver"),
    )

    # Relationships
    race = relationship("Race", back_populates="race_results")
    driver = relationship("Driver", back_populates="race_results")
    team = relationship("Team", back_populates="race_results")

    def __repr__(self) -> str:
        """String representation of RaceResult instance."""
        return (
            f"<RaceResult(id={self.result_id}, race_id={self.race_id}, "
            f"driver_id={self.driver_id}, position={self.final_position}, "
            f"points={self.points}, status='{self.status}')>"
        )

    def __str__(self) -> str:
        """Human-readable string representation."""
        if self.final_position:
            return f"P{self.final_position} - {self.points} pts ({self.status})"
        else:
            return f"DNF ({self.status})"

    @property
    def finished_race(self) -> bool:
        """Check if driver finished the race (not DNF/retired)."""
        return self.status == "finished" and self.final_position is not None

    @property
    def points_scoring_position(self) -> bool:
        """Check if driver finished in points-scoring position (typically top 10)."""
        return self.finished_race and self.final_position <= 10 and self.points > 0

    @property
    def podium_finish(self) -> bool:
        """Check if driver achieved a podium finish (top 3)."""
        return self.finished_race and self.final_position <= 3

    @property
    def race_winner(self) -> bool:
        """Check if driver won the race."""
        return self.finished_race and self.final_position == 1