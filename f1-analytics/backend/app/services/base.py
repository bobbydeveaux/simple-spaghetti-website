"""
Base service classes and utilities for data transformation.

This module provides common patterns and utilities for all F1 analytics services.
"""

from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional, Type, TypeVar, Generic
from datetime import datetime
from decimal import Decimal
import logging

from sqlalchemy.orm import Session
from pydantic import BaseModel

from ..database import Base

logger = logging.getLogger(__name__)

# Type variables for generic services
ModelType = TypeVar("ModelType", bound=Base)
CreateSchemaType = TypeVar("CreateSchemaType", bound=BaseModel)
UpdateSchemaType = TypeVar("UpdateSchemaType", bound=BaseModel)
ResponseSchemaType = TypeVar("ResponseSchemaType", bound=BaseModel)


class DataTransformationError(Exception):
    """Base exception for data transformation errors."""

    def __init__(self, message: str, field: Optional[str] = None, value: Any = None):
        self.message = message
        self.field = field
        self.value = value
        super().__init__(message)


class ValidationError(DataTransformationError):
    """Exception for validation errors."""
    pass


class TransformationService(ABC):
    """Abstract base class for data transformation services."""

    @abstractmethod
    def transform(self, data: Any, **kwargs) -> Any:
        """Transform data from one format to another."""
        pass

    @abstractmethod
    def validate(self, data: Any, **kwargs) -> bool:
        """Validate data meets requirements."""
        pass


class BaseService(Generic[ModelType, CreateSchemaType, UpdateSchemaType, ResponseSchemaType]):
    """
    Base service class providing CRUD operations with data transformation.

    This class handles common database operations with automatic data validation,
    transformation, and serialization using Pydantic schemas.
    """

    def __init__(
        self,
        model: Type[ModelType],
        create_schema: Type[CreateSchemaType],
        update_schema: Type[UpdateSchemaType],
        response_schema: Type[ResponseSchemaType],
    ):
        self.model = model
        self.create_schema = create_schema
        self.update_schema = update_schema
        self.response_schema = response_schema

    def create(
        self,
        db: Session,
        obj_in: CreateSchemaType,
        **kwargs
    ) -> ResponseSchemaType:
        """Create a new instance with validation and transformation."""
        try:
            # Validate input data
            if isinstance(obj_in, dict):
                obj_in = self.create_schema(**obj_in)

            # Transform to database model
            obj_data = obj_in.model_dump(exclude_unset=True)
            obj_data.update(kwargs)

            # Create database instance
            db_obj = self.model(**obj_data)
            db.add(db_obj)
            db.commit()
            db.refresh(db_obj)

            # Transform to response schema
            return self._to_response_schema(db_obj)

        except Exception as e:
            db.rollback()
            logger.error(f"Error creating {self.model.__name__}: {e}")
            raise DataTransformationError(f"Failed to create {self.model.__name__}: {str(e)}")

    def get(self, db: Session, id: int) -> Optional[ResponseSchemaType]:
        """Get instance by ID with transformation."""
        db_obj = db.query(self.model).filter(self.model.id == id).first()
        if db_obj:
            return self._to_response_schema(db_obj)
        return None

    def update(
        self,
        db: Session,
        db_obj: ModelType,
        obj_in: UpdateSchemaType,
        **kwargs
    ) -> ResponseSchemaType:
        """Update instance with validation and transformation."""
        try:
            # Validate input data
            if isinstance(obj_in, dict):
                obj_in = self.update_schema(**obj_in)

            # Get update data, excluding unset fields
            update_data = obj_in.model_dump(exclude_unset=True)
            update_data.update(kwargs)

            # Update database object
            for field, value in update_data.items():
                if hasattr(db_obj, field):
                    setattr(db_obj, field, value)

            # Update timestamp if available
            if hasattr(db_obj, 'updated_at'):
                db_obj.updated_at = datetime.utcnow()

            db.commit()
            db.refresh(db_obj)

            # Transform to response schema
            return self._to_response_schema(db_obj)

        except Exception as e:
            db.rollback()
            logger.error(f"Error updating {self.model.__name__}: {e}")
            raise DataTransformationError(f"Failed to update {self.model.__name__}: {str(e)}")

    def delete(self, db: Session, id: int) -> bool:
        """Delete instance by ID."""
        try:
            db_obj = db.query(self.model).filter(self.model.id == id).first()
            if db_obj:
                db.delete(db_obj)
                db.commit()
                return True
            return False

        except Exception as e:
            db.rollback()
            logger.error(f"Error deleting {self.model.__name__}: {e}")
            raise DataTransformationError(f"Failed to delete {self.model.__name__}: {str(e)}")

    def list(
        self,
        db: Session,
        skip: int = 0,
        limit: int = 100,
        filters: Optional[Dict[str, Any]] = None,
        order_by: Optional[str] = None
    ) -> List[ResponseSchemaType]:
        """List instances with pagination and filtering."""
        query = db.query(self.model)

        # Apply filters
        if filters:
            for field, value in filters.items():
                if hasattr(self.model, field):
                    query = query.filter(getattr(self.model, field) == value)

        # Apply ordering
        if order_by and hasattr(self.model, order_by):
            query = query.order_by(getattr(self.model, order_by))

        # Apply pagination
        db_objs = query.offset(skip).limit(limit).all()

        # Transform to response schemas
        return [self._to_response_schema(obj) for obj in db_objs]

    def count(
        self,
        db: Session,
        filters: Optional[Dict[str, Any]] = None
    ) -> int:
        """Count instances with optional filtering."""
        query = db.query(self.model)

        # Apply filters
        if filters:
            for field, value in filters.items():
                if hasattr(self.model, field):
                    query = query.filter(getattr(self.model, field) == value)

        return query.count()

    def _to_response_schema(self, db_obj: ModelType) -> ResponseSchemaType:
        """Transform database object to response schema."""
        return self.response_schema.model_validate(db_obj)


class DataValidator:
    """Utility class for common data validation patterns."""

    @staticmethod
    def validate_probability(value: float, field_name: str = "probability") -> float:
        """Validate probability value (0-100)."""
        if not isinstance(value, (int, float, Decimal)):
            raise ValidationError(f"{field_name} must be a number", field_name, value)

        value = float(value)
        if not 0 <= value <= 100:
            raise ValidationError(f"{field_name} must be between 0 and 100", field_name, value)

        return value

    @staticmethod
    def validate_elo_rating(value: int, field_name: str = "elo_rating") -> int:
        """Validate ELO rating value."""
        if not isinstance(value, (int, float)):
            raise ValidationError(f"{field_name} must be a number", field_name, value)

        value = int(value)
        if not 800 <= value <= 3000:
            raise ValidationError(f"{field_name} must be between 800 and 3000", field_name, value)

        return value

    @staticmethod
    def validate_driver_code(value: str, field_name: str = "driver_code") -> str:
        """Validate driver code format."""
        if not isinstance(value, str):
            raise ValidationError(f"{field_name} must be a string", field_name, value)

        value = value.upper().strip()
        if len(value) != 3 or not value.isalpha():
            raise ValidationError(f"{field_name} must be exactly 3 letters", field_name, value)

        return value

    @staticmethod
    def validate_position(value: int, field_name: str = "position", max_position: int = 30) -> int:
        """Validate racing position."""
        if not isinstance(value, (int, float)):
            raise ValidationError(f"{field_name} must be a number", field_name, value)

        value = int(value)
        if not 1 <= value <= max_position:
            raise ValidationError(f"{field_name} must be between 1 and {max_position}", field_name, value)

        return value

    @staticmethod
    def validate_lap_time(value: str, field_name: str = "lap_time") -> str:
        """Validate lap time format (M:SS.mmm)."""
        if not isinstance(value, str):
            raise ValidationError(f"{field_name} must be a string", field_name, value)

        import re
        pattern = r'^\d+:\d{2}\.\d{3}$'
        if not re.match(pattern, value):
            raise ValidationError(f"{field_name} must be in format M:SS.mmm", field_name, value)

        return value

    @staticmethod
    def validate_season_year(value: int, field_name: str = "season_year") -> int:
        """Validate F1 season year."""
        if not isinstance(value, (int, float)):
            raise ValidationError(f"{field_name} must be a number", field_name, value)

        value = int(value)
        current_year = datetime.now().year
        if not 1950 <= value <= current_year + 2:
            raise ValidationError(f"{field_name} must be between 1950 and {current_year + 2}", field_name, value)

        return value


class DataTransformer:
    """Utility class for common data transformations."""

    @staticmethod
    def normalize_driver_name(name: str) -> str:
        """Normalize driver name format."""
        if not isinstance(name, str):
            return str(name)

        return " ".join(word.capitalize() for word in name.strip().split())

    @staticmethod
    def normalize_team_name(name: str) -> str:
        """Normalize team name format."""
        if not isinstance(name, str):
            return str(name)

        return name.strip().title()

    @staticmethod
    def format_lap_time(seconds: float) -> str:
        """Convert seconds to lap time format (M:SS.mmm)."""
        if not isinstance(seconds, (int, float)):
            return "0:00.000"

        minutes = int(seconds // 60)
        remaining_seconds = seconds % 60
        return f"{minutes}:{remaining_seconds:06.3f}"

    @staticmethod
    def parse_lap_time(lap_time: str) -> Optional[float]:
        """Parse lap time string to seconds."""
        if not isinstance(lap_time, str):
            return None

        try:
            import re
            match = re.match(r'^(\d+):(\d{2})\.(\d{3})$', lap_time)
            if not match:
                return None

            minutes, seconds, milliseconds = match.groups()
            return int(minutes) * 60 + int(seconds) + int(milliseconds) / 1000

        except (ValueError, AttributeError):
            return None

    @staticmethod
    def calculate_points_from_position(position: int) -> float:
        """Calculate F1 points based on finishing position."""
        points_system = {
            1: 25.0, 2: 18.0, 3: 15.0, 4: 12.0, 5: 10.0,
            6: 8.0, 7: 6.0, 8: 4.0, 9: 2.0, 10: 1.0
        }
        return points_system.get(position, 0.0)

    @staticmethod
    def format_percentage(value: float, decimals: int = 1) -> str:
        """Format decimal as percentage string."""
        if not isinstance(value, (int, float, Decimal)):
            return "0.0%"

        return f"{float(value):.{decimals}f}%"

    @staticmethod
    def safe_divide(numerator: float, denominator: float, default: float = 0.0) -> float:
        """Safely divide two numbers, returning default if denominator is zero."""
        try:
            if denominator == 0:
                return default
            return float(numerator) / float(denominator)
        except (TypeError, ValueError):
            return default