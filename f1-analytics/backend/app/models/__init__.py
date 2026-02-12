"""
SQLAlchemy ORM models for F1 Analytics.

This module imports all models to ensure they are registered with SQLAlchemy
for Alembic migration detection.
"""

from .driver import Driver
from .team import Team
from .circuit import Circuit
from .race import Race
from .race_result import RaceResult
from .qualifying_result import QualifyingResult
from .weather_data import WeatherData
from .prediction import Prediction
from .prediction_accuracy import PredictionAccuracy
from .user import User

__all__ = [
    "Driver",
    "Team",
    "Circuit",
    "Race",
    "RaceResult",
    "QualifyingResult",
    "WeatherData",
    "Prediction",
    "PredictionAccuracy",
    "User",
]