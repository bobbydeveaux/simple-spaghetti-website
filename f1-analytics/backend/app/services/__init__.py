"""
Business logic services for F1 Analytics API.

This module provides comprehensive data transformation and validation services
for all F1 analytics operations. Services handle business logic, data validation,
transformation between different formats, and complex database operations.

Key Features:
- Base service classes with common CRUD patterns
- Specialized services for each domain (drivers, races, predictions)
- Comprehensive data validation and transformation utilities
- Error handling with detailed context
- Performance optimization for complex queries

Services:
- BaseService: Generic CRUD operations with validation
- DriverService: Driver management and statistics
- RaceService: Race management and results processing
- PredictionService: ML prediction management and accuracy tracking
"""

from .base import (
    BaseService,
    TransformationService,
    DataTransformationError,
    ValidationError,
    DataValidator,
    DataTransformer,
)

from .driver_service import DriverService
from .race_service import RaceService
from .prediction_service import PredictionService

# Create service instances for dependency injection
driver_service = DriverService()
race_service = RaceService()
prediction_service = PredictionService()

__all__ = [
    # Base classes and utilities
    "BaseService",
    "TransformationService",
    "DataTransformationError",
    "ValidationError",
    "DataValidator",
    "DataTransformer",

    # Service classes
    "DriverService",
    "RaceService",
    "PredictionService",

    # Service instances
    "driver_service",
    "race_service",
    "prediction_service",
]