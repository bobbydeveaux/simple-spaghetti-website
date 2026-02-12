"""
Circuit model for F1 Prediction Analytics
"""

from sqlalchemy import Column, Integer, String, Numeric, DateTime, CheckConstraint
from sqlalchemy.orm import relationship
from datetime import datetime
from api.database import Base


class Circuit(Base):
    """
    Circuit ORM model representing F1 racing circuits
    """
    __tablename__ = "circuits"

    circuit_id = Column(Integer, primary_key=True, index=True)
    circuit_name = Column(String(100), unique=True, nullable=False)
    location = Column(String(100))
    country = Column(String(50))
    track_length_km = Column(Numeric(5, 2))
    track_type = Column(String(20), CheckConstraint("track_type IN ('street', 'permanent')"))
    created_at = Column(DateTime, default=datetime.utcnow)

    # Relationships
    races = relationship("Race", back_populates="circuit")

    def __repr__(self):
        return f"<Circuit(circuit_id={self.circuit_id}, name='{self.circuit_name}', location='{self.location}')>"