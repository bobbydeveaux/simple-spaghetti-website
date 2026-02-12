"""
F1 Prediction Analytics Models

This module exports all SQLAlchemy ORM models for the F1 prediction analytics system.
These models represent the database schema for drivers, teams, races, results,
weather data, and predictions.

All models inherit from the Base class defined in the database module and include
proper relationships, constraints, and indexes for optimal query performance.
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
    "User"
]