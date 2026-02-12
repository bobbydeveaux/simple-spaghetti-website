"""Circuit ORM model."""
from datetime import datetime
from typing import List

from sqlalchemy import Column, Integer, String, DateTime, Numeric, CheckConstraint
from sqlalchemy.orm import relationship

from app.database import Base


class Circuit(Base):
    """
    Circuit entity representing F1 race tracks.

    Stores information about racing circuits including location, track length,
    and track type (street circuit vs permanent racing facility).
    """

    __tablename__ = "circuits"

    circuit_id = Column(Integer, primary_key=True, index=True)
    circuit_name = Column(String(100), unique=True, nullable=False)
    location = Column(String(100))
    country = Column(String(50))
    track_length_km = Column(Numeric(5, 2))  # Up to 99.99 km
    track_type = Column(String(20))
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    # Relationships
    races = relationship("Race", back_populates="circuit")

    # Constraints
    __table_args__ = (
        CheckConstraint(
            track_type.in_(["street", "permanent"]),
            name="ck_circuits_track_type"
        ),
    )

    def __repr__(self) -> str:
        return f"<Circuit(circuit_id={self.circuit_id}, name='{self.circuit_name}', country='{self.country}')>"

    @property
    def track_length_miles(self) -> float:
        """Convert track length to miles."""
        if self.track_length_km:
            return float(self.track_length_km) * 0.621371
        return 0.0