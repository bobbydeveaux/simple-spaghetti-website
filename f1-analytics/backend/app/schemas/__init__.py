"""
Pydantic schemas for F1 Analytics API request/response validation.

This module provides comprehensive data validation, serialization, and
transformation schemas for all F1 analytics data types.

Key Features:
- Request/response validation using Pydantic
- Automatic data transformation and serialization
- Comprehensive error handling with detailed field validation
- Support for nested relationships and complex data structures
- Consistent API response patterns
"""

from .base import (
    BaseSchema,
    TimestampMixin,
    PaginationParams,
    PaginatedResponse,
    ErrorDetail,
    ErrorResponse,
    SuccessResponse,
)

from .driver import (
    DriverBase,
    DriverCreate,
    DriverUpdate,
    DriverResponse,
    DriverBasic,
    DriverRanking,
    DriverStatistics,
    DriverListResponse,
    DriverRankingsResponse,
)

from .team import (
    TeamBase,
    TeamCreate,
    TeamUpdate,
    TeamResponse,
    TeamBasic,
    TeamStanding,
    TeamStatistics,
    TeamPerformanceMetrics,
    TeamListResponse,
    TeamStandingsResponse,
)

from .race import (
    RaceStatus,
    ResultStatus,
    WeatherCondition,
    RaceBase,
    RaceCreate,
    RaceUpdate,
    RaceResponse,
    RaceBasic,
    CircuitBase,
    CircuitResponse,
    CircuitBasic,
    WeatherDataBase,
    WeatherDataResponse,
    RaceResultBase,
    RaceResultResponse,
    QualifyingResultBase,
    QualifyingResultResponse,
    RaceWeekendSummary,
    RaceCalendarResponse,
    RaceListResponse,
)

from .prediction import (
    PredictionBase,
    PredictionCreate,
    PredictionUpdate,
    PredictionResponse,
    PredictionWithDetails,
    RacePredictionsSummary,
    PredictionAccuracyBase,
    PredictionAccuracyResponse,
    ModelPerformanceMetrics,
    BatchPredictionRequest,
    BatchPredictionResponse,
    PredictionListResponse,
)

# Re-export all schemas for easy importing
__all__ = [
    # Base schemas
    "BaseSchema",
    "TimestampMixin",
    "PaginationParams",
    "PaginatedResponse",
    "ErrorDetail",
    "ErrorResponse",
    "SuccessResponse",

    # Driver schemas
    "DriverBase",
    "DriverCreate",
    "DriverUpdate",
    "DriverResponse",
    "DriverBasic",
    "DriverRanking",
    "DriverStatistics",
    "DriverListResponse",
    "DriverRankingsResponse",

    # Team schemas
    "TeamBase",
    "TeamCreate",
    "TeamUpdate",
    "TeamResponse",
    "TeamBasic",
    "TeamStanding",
    "TeamStatistics",
    "TeamPerformanceMetrics",
    "TeamListResponse",
    "TeamStandingsResponse",

    # Race schemas
    "RaceStatus",
    "ResultStatus",
    "WeatherCondition",
    "RaceBase",
    "RaceCreate",
    "RaceUpdate",
    "RaceResponse",
    "RaceBasic",
    "CircuitBase",
    "CircuitResponse",
    "CircuitBasic",
    "WeatherDataBase",
    "WeatherDataResponse",
    "RaceResultBase",
    "RaceResultResponse",
    "QualifyingResultBase",
    "QualifyingResultResponse",
    "RaceWeekendSummary",
    "RaceCalendarResponse",
    "RaceListResponse",

    # Prediction schemas
    "PredictionBase",
    "PredictionCreate",
    "PredictionUpdate",
    "PredictionResponse",
    "PredictionWithDetails",
    "RacePredictionsSummary",
    "PredictionAccuracyBase",
    "PredictionAccuracyResponse",
    "ModelPerformanceMetrics",
    "BatchPredictionRequest",
    "BatchPredictionResponse",
    "PredictionListResponse",
]