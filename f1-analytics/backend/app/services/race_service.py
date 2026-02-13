"""
Race service for data transformation and business logic.

This module handles race-related operations including race management,
results processing, and calendar operations.
"""

from typing import List, Optional, Dict, Any
from datetime import date, datetime, timedelta
from sqlalchemy.orm import Session
from sqlalchemy import desc, asc, and_, or_

from ..models.f1_models import (
    Race, Circuit, RaceResult, QualifyingResult, WeatherData,
    RaceStatus, ResultStatus
)
from ..schemas.race import (
    RaceCreate, RaceUpdate, RaceResponse,
    RaceResultResponse, QualifyingResultResponse,
    WeatherDataResponse, RaceWeekendSummary, RaceCalendarResponse
)
from .base import BaseService, DataValidator, DataTransformer, DataTransformationError


class RaceService(BaseService[Race, RaceCreate, RaceUpdate, RaceResponse]):
    """Service for race data operations and transformations."""

    def __init__(self):
        super().__init__(
            model=Race,
            create_schema=RaceCreate,
            update_schema=RaceUpdate,
            response_schema=RaceResponse
        )

    def create_race(
        self,
        db: Session,
        race_data: RaceCreate
    ) -> RaceResponse:
        """Create a new race with validation."""
        # Validate season and round uniqueness
        existing_race = db.query(Race).filter(
            Race.season_year == race_data.season_year,
            Race.round_number == race_data.round_number
        ).first()

        if existing_race:
            raise DataTransformationError(
                f"Race already exists for season {race_data.season_year}, round {race_data.round_number}",
                "round_number",
                race_data.round_number
            )

        # Validate circuit exists
        circuit = db.query(Circuit).filter(Circuit.circuit_id == race_data.circuit_id).first()
        if not circuit:
            raise DataTransformationError(
                f"Circuit with ID {race_data.circuit_id} not found",
                "circuit_id",
                race_data.circuit_id
            )

        # Validate season year
        validated_season = DataValidator.validate_season_year(race_data.season_year)

        # Create race with validated data
        return self.create(
            db=db,
            obj_in=race_data,
            season_year=validated_season
        )

    def get_race_calendar(
        self,
        db: Session,
        season: Optional[int] = None
    ) -> RaceCalendarResponse:
        """Get race calendar for a season."""
        current_year = datetime.now().year
        season = season or current_year

        races = db.query(Race).filter(
            Race.season_year == season
        ).order_by(Race.round_number).all()

        # Calculate statistics
        total_races = len(races)
        completed_races = sum(1 for r in races if r.status == RaceStatus.COMPLETED)
        upcoming_races = sum(1 for r in races if r.status == RaceStatus.SCHEDULED and r.race_date >= date.today())

        return RaceCalendarResponse(
            season=season,
            total_races=total_races,
            completed_races=completed_races,
            upcoming_races=upcoming_races,
            races=[self._to_response_schema(race) for race in races]
        )

    def get_upcoming_races(
        self,
        db: Session,
        limit: int = 5
    ) -> List[RaceResponse]:
        """Get upcoming scheduled races."""
        today = date.today()

        races = db.query(Race).filter(
            Race.status == RaceStatus.SCHEDULED,
            Race.race_date >= today
        ).order_by(Race.race_date).limit(limit).all()

        return [self._to_response_schema(race) for race in races]

    def get_recent_races(
        self,
        db: Session,
        limit: int = 5
    ) -> List[RaceResponse]:
        """Get recently completed races."""
        races = db.query(Race).filter(
            Race.status == RaceStatus.COMPLETED
        ).order_by(desc(Race.race_date)).limit(limit).all()

        return [self._to_response_schema(race) for race in races]

    def get_race_weekend_summary(
        self,
        db: Session,
        race_id: int
    ) -> RaceWeekendSummary:
        """Get complete race weekend summary."""
        race = db.query(Race).filter(Race.race_id == race_id).first()
        if not race:
            raise DataTransformationError(f"Race with ID {race_id} not found")

        # Get weather data
        weather = db.query(WeatherData).filter(WeatherData.race_id == race_id).first()

        # Get qualifying results
        qualifying_results = db.query(QualifyingResult).filter(
            QualifyingResult.race_id == race_id
        ).order_by(QualifyingResult.final_grid_position).all()

        # Get race results
        race_results = db.query(RaceResult).filter(
            RaceResult.race_id == race_id
        ).order_by(RaceResult.final_position.nulls_last()).all()

        # Transform to response schemas
        from ..schemas.race import RaceWeekendSummary

        return RaceWeekendSummary(
            race=self._to_response_schema(race),
            weather=WeatherDataResponse.model_validate(weather) if weather else None,
            qualifying_results=[
                QualifyingResultResponse.model_validate(qr) for qr in qualifying_results
            ],
            race_results=[
                RaceResultResponse.model_validate(rr) for rr in race_results
            ],
            predictions=[]  # Would be populated by prediction service
        )

    def add_race_result(
        self,
        db: Session,
        race_id: int,
        driver_id: int,
        team_id: int,
        result_data: Dict[str, Any]
    ) -> RaceResultResponse:
        """Add a race result with validation."""
        # Validate race exists and is completed
        race = db.query(Race).filter(Race.race_id == race_id).first()
        if not race:
            raise DataTransformationError(f"Race with ID {race_id} not found")

        if race.status != RaceStatus.COMPLETED:
            raise DataTransformationError("Cannot add results to non-completed race")

        # Check if result already exists
        existing_result = db.query(RaceResult).filter(
            RaceResult.race_id == race_id,
            RaceResult.driver_id == driver_id
        ).first()

        if existing_result:
            raise DataTransformationError(
                f"Result already exists for driver {driver_id} in race {race_id}"
            )

        # Validate position if provided
        if 'final_position' in result_data and result_data['final_position']:
            DataValidator.validate_position(result_data['final_position'])

        if 'grid_position' in result_data and result_data['grid_position']:
            DataValidator.validate_position(result_data['grid_position'])

        # Validate lap time if provided
        if 'fastest_lap_time' in result_data and result_data['fastest_lap_time']:
            DataValidator.validate_lap_time(result_data['fastest_lap_time'])

        # Calculate points based on position if not provided
        if 'points' not in result_data or result_data['points'] is None:
            if 'final_position' in result_data and result_data['final_position']:
                result_data['points'] = DataTransformer.calculate_points_from_position(
                    result_data['final_position']
                )

        # Create race result
        race_result = RaceResult(
            race_id=race_id,
            driver_id=driver_id,
            team_id=team_id,
            **result_data
        )

        db.add(race_result)
        db.commit()
        db.refresh(race_result)

        return RaceResultResponse.model_validate(race_result)

    def add_qualifying_result(
        self,
        db: Session,
        race_id: int,
        driver_id: int,
        qualifying_data: Dict[str, Any]
    ) -> QualifyingResultResponse:
        """Add qualifying result with validation."""
        # Validate race exists
        race = db.query(Race).filter(Race.race_id == race_id).first()
        if not race:
            raise DataTransformationError(f"Race with ID {race_id} not found")

        # Check if qualifying result already exists
        existing_result = db.query(QualifyingResult).filter(
            QualifyingResult.race_id == race_id,
            QualifyingResult.driver_id == driver_id
        ).first()

        if existing_result:
            raise DataTransformationError(
                f"Qualifying result already exists for driver {driver_id} in race {race_id}"
            )

        # Validate position
        if 'final_grid_position' in qualifying_data:
            DataValidator.validate_position(qualifying_data['final_grid_position'])

        # Validate lap times
        for session in ['q1_time', 'q2_time', 'q3_time']:
            if session in qualifying_data and qualifying_data[session]:
                DataValidator.validate_lap_time(qualifying_data[session])

        # Create qualifying result
        qualifying_result = QualifyingResult(
            race_id=race_id,
            driver_id=driver_id,
            **qualifying_data
        )

        db.add(qualifying_result)
        db.commit()
        db.refresh(qualifying_result)

        return QualifyingResultResponse.model_validate(qualifying_result)

    def add_weather_data(
        self,
        db: Session,
        race_id: int,
        weather_data: Dict[str, Any]
    ) -> WeatherDataResponse:
        """Add weather data for a race."""
        # Validate race exists
        race = db.query(Race).filter(Race.race_id == race_id).first()
        if not race:
            raise DataTransformationError(f"Race with ID {race_id} not found")

        # Check if weather data already exists
        existing_weather = db.query(WeatherData).filter(WeatherData.race_id == race_id).first()
        if existing_weather:
            # Update existing weather data
            for field, value in weather_data.items():
                if hasattr(existing_weather, field):
                    setattr(existing_weather, field, value)

            db.commit()
            db.refresh(existing_weather)
            return WeatherDataResponse.model_validate(existing_weather)

        # Create new weather data
        weather = WeatherData(race_id=race_id, **weather_data)
        db.add(weather)
        db.commit()
        db.refresh(weather)

        return WeatherDataResponse.model_validate(weather)

    def update_race_status(
        self,
        db: Session,
        race_id: int,
        status: RaceStatus
    ) -> RaceResponse:
        """Update race status."""
        race = db.query(Race).filter(Race.race_id == race_id).first()
        if not race:
            raise DataTransformationError(f"Race with ID {race_id} not found")

        race.status = status
        db.commit()
        db.refresh(race)

        return self._to_response_schema(race)

    def get_race_results(
        self,
        db: Session,
        race_id: int,
        order_by: str = "final_position"
    ) -> List[RaceResultResponse]:
        """Get race results with optional ordering."""
        race = db.query(Race).filter(Race.race_id == race_id).first()
        if not race:
            raise DataTransformationError(f"Race with ID {race_id} not found")

        query = db.query(RaceResult).filter(RaceResult.race_id == race_id)

        # Apply ordering
        if order_by == "final_position":
            query = query.order_by(RaceResult.final_position.nulls_last())
        elif order_by == "grid_position":
            query = query.order_by(RaceResult.grid_position.nulls_last())
        elif order_by == "points":
            query = query.order_by(desc(RaceResult.points))

        results = query.all()
        return [RaceResultResponse.model_validate(result) for result in results]

    def get_driver_race_history(
        self,
        db: Session,
        driver_id: int,
        circuit_id: Optional[int] = None,
        limit: int = 10
    ) -> List[RaceResultResponse]:
        """Get driver's race history, optionally filtered by circuit."""
        query = db.query(RaceResult).join(Race).filter(RaceResult.driver_id == driver_id)

        if circuit_id:
            query = query.filter(Race.circuit_id == circuit_id)

        results = query.order_by(desc(Race.race_date)).limit(limit).all()
        return [RaceResultResponse.model_validate(result) for result in results]

    def search_races(
        self,
        db: Session,
        query: str,
        season: Optional[int] = None,
        limit: int = 10
    ) -> List[RaceResponse]:
        """Search races by name or circuit."""
        search_term = f"%{query.strip()}%"

        race_query = db.query(Race).join(Circuit).filter(
            or_(
                Race.race_name.ilike(search_term),
                Circuit.circuit_name.ilike(search_term),
                Circuit.location.ilike(search_term)
            )
        )

        if season:
            race_query = race_query.filter(Race.season_year == season)

        races = race_query.limit(limit).all()
        return [self._to_response_schema(race) for race in races]