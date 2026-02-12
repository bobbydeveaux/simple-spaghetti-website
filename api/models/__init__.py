"""
Data models and schemas for F1 Prediction Analytics
"""

# ORM Models
from .user import User, UserLegacy
from .driver import Driver
from .team import Team
from .circuit import Circuit
from .race import Race
from .race_result import RaceResult
from .qualifying_result import QualifyingResult
from .weather_data import WeatherData
from .prediction import Prediction
from .prediction_accuracy import PredictionAccuracy

# Pydantic Schemas (for backward compatibility)
from .user import RegisterRequest, RegisterResponse, LoginRequest
from .token import TokenResponse, RefreshRequest, ProtectedResponse

__all__ = [
    # ORM Models
    "User",
    "UserLegacy",
    "Driver",
    "Team",
    "Circuit",
    "Race",
    "RaceResult",
    "QualifyingResult",
    "WeatherData",
    "Prediction",
    "PredictionAccuracy",
    # Pydantic Schemas
    "RegisterRequest",
    "RegisterResponse",
    "LoginRequest",
    "TokenResponse",
    "RefreshRequest",
    "ProtectedResponse"
]