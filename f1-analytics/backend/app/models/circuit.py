"""
Circuit Model

Represents F1 circuits/tracks in the database.
Tracks circuit information including location and track characteristics.
"""

from datetime import datetime
from typing import List, TYPE_CHECKING
from decimal import Decimal

from sqlalchemy import Column, Integer, String, DateTime, DECIMAL, Index, CheckConstraint
from sqlalchemy.orm import relationship

from ..database import Base

if TYPE_CHECKING:
    from .race import Race


class Circuit(Base):
    """
    F1 Circuit model.

    Represents Formula 1 circuits/tracks and their characteristics.

    Attributes:
        circuit_id: Primary key
        circuit_name: Official circuit name (unique)
        location: City/region where circuit is located
        country: Country where circuit is located
        track_length_km: Track length in kilometers (2 decimal places)
        track_type: Type of track ('street' or 'permanent')
        created_at: Record creation timestamp

    Relationships:
        races: All races held at this circuit
    """

    __tablename__ = "circuits"

    # Primary key
    circuit_id = Column(Integer, primary_key=True, autoincrement=True)

    # Circuit information
    circuit_name = Column(String(100), nullable=False, unique=True, index=True)
    location = Column(String(100), nullable=False)
    country = Column(String(50), nullable=False, index=True)

    # Track characteristics
    track_length_km = Column(DECIMAL(5, 2), nullable=False)
    track_type = Column(String(20), nullable=False, index=True)

    # Timestamps
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)

    # Relationships
    races = relationship(
        "Race",
        back_populates="circuit",
        lazy="select"
    )

    # Constraints and indexes
    __table_args__ = (
        CheckConstraint(
            "track_type IN ('street', 'permanent')",
            name="ck_circuits_track_type"
        ),
        CheckConstraint(
            "track_length_km > 0",
            name="ck_circuits_track_length_positive"
        ),
        Index("idx_circuits_name", "circuit_name"),
        Index("idx_circuits_country", "country"),
        Index("idx_circuits_type", "track_type"),
    )

    def __repr__(self) -> str:
        return f"<Circuit(id={self.circuit_id}, name='{self.circuit_name}', country='{self.country}')>"

    def __str__(self) -> str:
        return f"{self.circuit_name} ({self.location}, {self.country})"

    @property
    def is_street_circuit(self) -> bool:
        """Check if this is a street circuit"""
        return self.track_type == "street"

    @property
    def is_permanent_circuit(self) -> bool:
        """Check if this is a permanent circuit"""
        return self.track_type == "permanent"