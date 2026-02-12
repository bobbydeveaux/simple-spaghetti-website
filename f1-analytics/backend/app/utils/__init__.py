"""
Utility modules for F1 Analytics API.

This module provides advanced utilities for data validation, transformation,
and processing across the F1 analytics platform.

Key Features:
- Advanced validation decorators and business rule validators
- Sophisticated data transformers with F1-specific calculations
- JWT and session management utilities
- Performance optimization utilities
"""

from .validators import (
    validate_request_data,
    validate_database_constraints,
    validate_business_rules,
    handle_service_errors,
    F1DataValidator,
    validate_race_not_completed,
    validate_race_is_completed,
    validate_future_race_date,
)

from .transformers import (
    TransformationConfig,
    F1DataTransformer,
)

# Import existing utilities if available
try:
    from .jwt_manager import *
    from .session_manager import *
except ImportError:
    pass

__all__ = [
    # Validation utilities
    "validate_request_data",
    "validate_database_constraints",
    "validate_business_rules",
    "handle_service_errors",
    "F1DataValidator",
    "validate_race_not_completed",
    "validate_race_is_completed",
    "validate_future_race_date",

    # Transformation utilities
    "TransformationConfig",
    "F1DataTransformer",
]