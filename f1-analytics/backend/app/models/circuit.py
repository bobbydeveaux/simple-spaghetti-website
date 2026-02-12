"""
Circuit model for F1 Prediction Analytics.

This module defines the Circuit SQLAlchemy model representing Formula 1 racing
circuits and tracks with their characteristics.
"""

from datetime import datetime
from sqlalchemy import Column, Integer, String, DateTime, Numeric
from sqlalchemy.orm import relationship

from app.database import Base


class Circuit(Base):
    """
    SQLAlchemy model for Formula 1 racing circuits.

    This model stores circuit information including track characteristics
    that may influence race predictions and performance analysis.

    Attributes:
        circuit_id: Primary key, unique identifier for circuit
        circuit_name: Official name of the racing circuit
        location: City/region where circuit is located
        country: Country where circuit is located
        track_length_km: Length of circuit in kilometers
        track_type: Type of circuit ('street', 'permanent')
        created_at: Timestamp when record was created
    """

    __tablename__ = "circuits"

    circuit_id = Column(Integer, primary_key=True, index=True)
    circuit_name = Column(String(100), unique=True, nullable=False)
    location = Column(String(100))
    country = Column(String(50))
    track_length_km = Column(Numeric(5, 2))  # e.g., 5.891 km
    track_type = Column(String(20))  # 'street', 'permanent'
    created_at = Column(DateTime, default=datetime.utcnow)

    # Relationships
    races = relationship("Race", back_populates="circuit")

    def __repr__(self) -> str:
        """String representation of Circuit instance."""
        return f"<Circuit(id={self.circuit_id}, name='{self.circuit_name}', location='{self.location}')>"

    def __str__(self) -> str:
        """Human-readable string representation."""
        return f"{self.circuit_name} ({self.location})"

    @property
    def full_name(self) -> str:
        """Full descriptive name including location."""
        if self.location and self.country:
            return f"{self.circuit_name}, {self.location}, {self.country}"
        elif self.location:
            return f"{self.circuit_name}, {self.location}"
        else:
            return self.circuit_name