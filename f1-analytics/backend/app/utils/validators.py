"""
Advanced validation utilities and decorators for F1 Analytics.

This module provides sophisticated validation patterns, custom validators,
and decorators for API endpoints and business logic validation.
"""

import functools
import logging
from typing import Any, Callable, Dict, List, Optional, Type, Union
from datetime import date, datetime
from decimal import Decimal

from fastapi import HTTPException, status
from pydantic import BaseModel, ValidationError as PydanticValidationError
from sqlalchemy.orm import Session

from ..services.base import ValidationError, DataTransformationError
from ..models.f1_models import Driver, Race, Team, Circuit

logger = logging.getLogger(__name__)


def validate_request_data(schema: Type[BaseModel]):
    """
    Decorator to validate request data against a Pydantic schema.

    Usage:
        @validate_request_data(DriverCreate)
        def create_driver(data: dict) -> DriverResponse:
            # data is automatically validated and converted
            pass
    """
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            try:
                # Find the data parameter (usually the second parameter after db)
                if len(args) > 1 and isinstance(args[1], dict):
                    # Validate and convert the data
                    validated_data = schema(**args[1])
                    # Replace the dict with the validated Pydantic model
                    args = (args[0], validated_data) + args[2:]
                elif 'data' in kwargs and isinstance(kwargs['data'], dict):
                    kwargs['data'] = schema(**kwargs['data'])

                return func(*args, **kwargs)

            except PydanticValidationError as e:
                logger.warning(f"Validation error in {func.__name__}: {e}")
                raise HTTPException(
                    status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                    detail=f"Validation error: {str(e)}"
                )
            except Exception as e:
                logger.error(f"Unexpected error in {func.__name__}: {e}")
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail="Internal server error"
                )

        return wrapper
    return decorator


def validate_database_constraints(
    unique_fields: Optional[List[str]] = None,
    foreign_keys: Optional[Dict[str, Type]] = None,
    custom_validators: Optional[List[Callable]] = None
):
    """
    Decorator to validate database constraints before operations.

    Args:
        unique_fields: List of fields that must be unique
        foreign_keys: Dict of field_name -> Model for foreign key validation
        custom_validators: List of custom validation functions
    """
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            try:
                # Get database session (usually first parameter)
                db: Session = args[0] if args else None
                if not db:
                    raise ValueError("Database session not found")

                # Get the data to validate (second parameter or 'data' kwarg)
                data = args[1] if len(args) > 1 else kwargs.get('data')
                if not data:
                    raise ValueError("Data to validate not found")

                # Convert to dict if it's a Pydantic model
                if hasattr(data, 'model_dump'):
                    data_dict = data.model_dump(exclude_unset=True)
                else:
                    data_dict = data if isinstance(data, dict) else {}

                # Validate unique fields
                if unique_fields:
                    _validate_unique_constraints(db, data_dict, unique_fields, func.__name__)

                # Validate foreign keys
                if foreign_keys:
                    _validate_foreign_keys(db, data_dict, foreign_keys)

                # Run custom validators
                if custom_validators:
                    for validator in custom_validators:
                        validator(db, data_dict)

                return func(*args, **kwargs)

            except (ValidationError, DataTransformationError) as e:
                logger.warning(f"Database validation error in {func.__name__}: {e}")
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=str(e)
                )
            except Exception as e:
                logger.error(f"Unexpected error in database validation {func.__name__}: {e}")
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail="Internal server error"
                )

        return wrapper
    return decorator


def validate_business_rules(*rules: Callable):
    """
    Decorator to validate business rules before operations.

    Usage:
        @validate_business_rules(
            lambda db, data: validate_race_not_completed(db, data['race_id']),
            lambda db, data: validate_driver_exists(db, data['driver_id'])
        )
        def create_prediction(db: Session, data: dict):
            pass
    """
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            try:
                db: Session = args[0] if args else None
                data = args[1] if len(args) > 1 else kwargs.get('data')

                if db and data:
                    data_dict = data.model_dump() if hasattr(data, 'model_dump') else data

                    for rule in rules:
                        rule(db, data_dict)

                return func(*args, **kwargs)

            except (ValidationError, DataTransformationError) as e:
                logger.warning(f"Business rule validation error in {func.__name__}: {e}")
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=str(e)
                )

        return wrapper
    return decorator


def handle_service_errors(func: Callable) -> Callable:
    """
    Decorator to handle service layer errors and convert them to HTTP exceptions.
    """
    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        try:
            return func(*args, **kwargs)

        except ValidationError as e:
            logger.warning(f"Validation error in {func.__name__}: {e}")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail={
                    "error": "Validation Error",
                    "message": e.message,
                    "field": e.field,
                    "value": str(e.value) if e.value is not None else None
                }
            )

        except DataTransformationError as e:
            logger.error(f"Data transformation error in {func.__name__}: {e}")
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail={
                    "error": "Data Transformation Error",
                    "message": e.message,
                    "field": e.field,
                    "value": str(e.value) if e.value is not None else None
                }
            )

        except Exception as e:
            logger.error(f"Unexpected error in {func.__name__}: {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Internal server error"
            )

    return wrapper


class F1DataValidator:
    """Advanced validator for F1-specific business rules and constraints."""

    @staticmethod
    def validate_race_season_consistency(db: Session, data: Dict[str, Any]) -> None:
        """Validate that race dates are consistent with season years."""
        if 'race_date' in data and 'season_year' in data:
            race_date = data['race_date']
            season_year = data['season_year']

            if isinstance(race_date, str):
                race_date = datetime.fromisoformat(race_date).date()

            if race_date.year != season_year:
                raise ValidationError(
                    f"Race date year {race_date.year} does not match season year {season_year}",
                    "race_date",
                    race_date
                )

    @staticmethod
    def validate_driver_team_consistency(db: Session, data: Dict[str, Any]) -> None:
        """Validate that driver belongs to the specified team."""
        if 'driver_id' in data and 'team_id' in data:
            driver = db.query(Driver).filter(Driver.driver_id == data['driver_id']).first()
            if driver and driver.current_team_id != data['team_id']:
                raise ValidationError(
                    f"Driver {data['driver_id']} does not belong to team {data['team_id']}",
                    "team_id",
                    data['team_id']
                )

    @staticmethod
    def validate_prediction_probabilities(db: Session, race_id: int) -> None:
        """Validate that total prediction probabilities for a race are reasonable."""
        from ..models.f1_models import Prediction

        predictions = db.query(Prediction).filter(Prediction.race_id == race_id).all()
        if predictions:
            total_probability = sum(float(p.predicted_win_probability) for p in predictions)
            if total_probability > 120:  # Allow some tolerance
                raise ValidationError(
                    f"Total prediction probabilities ({total_probability:.1f}%) exceed reasonable limits",
                    "predicted_win_probability",
                    total_probability
                )

    @staticmethod
    def validate_race_result_consistency(db: Session, data: Dict[str, Any]) -> None:
        """Validate race result data consistency."""
        # Check that final position and grid position are reasonable
        if 'final_position' in data and 'grid_position' in data:
            final_pos = data.get('final_position')
            grid_pos = data.get('grid_position')

            if final_pos and grid_pos:
                if abs(final_pos - grid_pos) > 25:  # Unlikely to gain/lose 25+ positions
                    logger.warning(
                        f"Large position change: grid {grid_pos} to final {final_pos}"
                    )

        # Validate points based on position
        if 'final_position' in data and 'points' in data:
            from ..services.base import DataTransformer
            expected_points = DataTransformer.calculate_points_from_position(data['final_position'])
            actual_points = float(data.get('points', 0))

            # Allow for fastest lap bonus
            if actual_points > expected_points + 1:
                raise ValidationError(
                    f"Points {actual_points} too high for position {data['final_position']}",
                    "points",
                    actual_points
                )

    @staticmethod
    def validate_qualifying_progression(db: Session, data: Dict[str, Any]) -> None:
        """Validate qualifying session progression logic."""
        q1_time = data.get('q1_time')
        q2_time = data.get('q2_time')
        q3_time = data.get('q3_time')
        grid_position = data.get('final_grid_position')

        # Validate session progression
        if grid_position:
            # Top 10 should have Q3 times
            if grid_position <= 10 and not q3_time:
                logger.warning(f"Top 10 qualifier (P{grid_position}) missing Q3 time")

            # Top 15 should have Q2 times
            if grid_position <= 15 and not q2_time:
                logger.warning(f"Top 15 qualifier (P{grid_position}) missing Q2 time")

            # All should have Q1 times
            if not q1_time:
                logger.warning(f"Qualifier (P{grid_position}) missing Q1 time")

    @staticmethod
    def validate_elo_rating_bounds(value: Union[int, float], field_name: str = "elo_rating") -> int:
        """Validate ELO rating with more sophisticated bounds checking."""
        rating = int(value)

        # Standard bounds
        if not 800 <= rating <= 3000:
            raise ValidationError(
                f"{field_name} must be between 800 and 3000",
                field_name,
                rating
            )

        # Warn for extreme values
        if rating < 1000:
            logger.warning(f"Very low ELO rating: {rating}")
        elif rating > 2500:
            logger.warning(f"Very high ELO rating: {rating}")

        return rating

    @staticmethod
    def validate_lap_time_format(lap_time: str, field_name: str = "lap_time") -> str:
        """Validate and normalize lap time format."""
        import re

        if not isinstance(lap_time, str):
            raise ValidationError(f"{field_name} must be a string", field_name, lap_time)

        # Allow various formats and normalize
        patterns = [
            r'^(\d+):(\d{2})\.(\d{3})$',  # M:SS.mmm
            r'^(\d+):(\d{2})\.(\d{2})$',   # M:SS.mm
            r'^(\d+)\.(\d{3})$',           # SS.mmm (for very fast laps)
        ]

        for pattern in patterns:
            match = re.match(pattern, lap_time)
            if match:
                groups = match.groups()
                if len(groups) == 3:
                    if len(groups[2]) == 2:  # Convert mm to mmm
                        return f"{groups[0]}:{groups[1]}.{groups[2]}0"
                    return lap_time
                elif len(groups) == 2:  # SS.mmm format
                    return f"0:{groups[0].zfill(2)}.{groups[1]}"

        raise ValidationError(
            f"{field_name} must be in format M:SS.mmm, M:SS.mm, or SS.mmm",
            field_name,
            lap_time
        )


def _validate_unique_constraints(
    db: Session,
    data: Dict[str, Any],
    unique_fields: List[str],
    operation: str
) -> None:
    """Internal function to validate unique field constraints."""
    # This would need to be implemented based on the specific model
    # For now, this is a placeholder
    pass


def _validate_foreign_keys(
    db: Session,
    data: Dict[str, Any],
    foreign_keys: Dict[str, Type]
) -> None:
    """Internal function to validate foreign key constraints."""
    for field_name, model_class in foreign_keys.items():
        if field_name in data:
            fk_value = data[field_name]
            if fk_value is not None:
                # Get the primary key field name (assumes 'id' or modelname_id)
                pk_field = f"{model_class.__tablename__.rstrip('s')}_id"
                if hasattr(model_class, pk_field):
                    existing = db.query(model_class).filter(
                        getattr(model_class, pk_field) == fk_value
                    ).first()
                else:
                    # Fallback to 'id' field
                    existing = db.query(model_class).filter(
                        getattr(model_class, 'id', None) == fk_value
                    ).first()

                if not existing:
                    raise ValidationError(
                        f"{model_class.__name__} with ID {fk_value} does not exist",
                        field_name,
                        fk_value
                    )


# Business rule validators for common F1 scenarios
def validate_race_not_completed(db: Session, race_id: int) -> None:
    """Validate that a race is not completed (for predictions, etc.)."""
    from ..models.f1_models import RaceStatus

    race = db.query(Race).filter(Race.race_id == race_id).first()
    if not race:
        raise ValidationError(f"Race with ID {race_id} not found", "race_id", race_id)

    if race.status == RaceStatus.COMPLETED:
        raise ValidationError("Cannot modify data for completed races", "race_id", race_id)


def validate_race_is_completed(db: Session, race_id: int) -> None:
    """Validate that a race is completed (for accuracy calculations, etc.)."""
    from ..models.f1_models import RaceStatus

    race = db.query(Race).filter(Race.race_id == race_id).first()
    if not race:
        raise ValidationError(f"Race with ID {race_id} not found", "race_id", race_id)

    if race.status != RaceStatus.COMPLETED:
        raise ValidationError("Race must be completed for this operation", "race_id", race_id)


def validate_future_race_date(db: Session, data: Dict[str, Any]) -> None:
    """Validate that race date is in the future (for new races)."""
    if 'race_date' in data:
        race_date = data['race_date']
        if isinstance(race_date, str):
            race_date = datetime.fromisoformat(race_date).date()

        if race_date <= date.today():
            raise ValidationError(
                "Race date must be in the future",
                "race_date",
                race_date
            )