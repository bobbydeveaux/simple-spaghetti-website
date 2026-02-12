"""
F1-specific repositories for database operations.

This module provides specialized repositories for F1 data models
with domain-specific query methods.
"""

import logging
from typing import Optional, List, Dict, Any
from datetime import date, datetime, timezone

from sqlalchemy.orm import Session, joinedload
from sqlalchemy import desc, asc, func, and_, or_

from .base import BaseRepository
from ..models.f1_models import (
    Driver, Team, Circuit, Race, RaceResult, QualifyingResult,
    WeatherData, Prediction, PredictionAccuracy, RaceStatus
)

logger = logging.getLogger(__name__)


class DriverRepository(BaseRepository[Driver]):
    """Repository for Driver model with F1-specific methods."""

    def __init__(self, db_session: Session):
        super().__init__(Driver, db_session)

    def get_by_code(self, driver_code: str) -> Optional[Driver]:
        """Get driver by driver code (e.g., 'HAM', 'VER')."""
        return self.get_one_by_fields(driver_code=driver_code)

    def get_by_team(self, team_id: int) -> List[Driver]:
        """Get all drivers for a specific team."""
        return self.get_by_fields(current_team_id=team_id)

    def get_active_drivers(self) -> List[Driver]:
        """Get all drivers who currently have a team."""
        return self.db.query(Driver).filter(
            Driver.current_team_id.isnot(None)
        ).all()

    def get_drivers_by_elo_ranking(self, limit: int = 20) -> List[Driver]:
        """Get drivers ranked by ELO rating."""
        return self.db.query(Driver).order_by(
            desc(Driver.current_elo_rating)
        ).limit(limit).all()

    def update_elo_rating(self, driver_id: int, new_rating: int) -> bool:
        """Update driver's ELO rating."""
        return self.update(driver_id, {
            "current_elo_rating": new_rating
        }) is not None


class TeamRepository(BaseRepository[Team]):
    """Repository for Team model with F1-specific methods."""

    def __init__(self, db_session: Session):
        super().__init__(Team, db_session)

    def get_by_name(self, team_name: str) -> Optional[Team]:
        """Get team by name."""
        return self.get_one_by_fields(team_name=team_name)

    def get_teams_with_drivers(self) -> List[Team]:
        """Get all teams with their current drivers loaded."""
        return self.db.query(Team).options(
            joinedload(Team.drivers)
        ).all()

    def get_teams_by_elo_ranking(self, limit: int = 10) -> List[Team]:
        """Get teams ranked by ELO rating."""
        return self.db.query(Team).order_by(
            desc(Team.current_elo_rating)
        ).limit(limit).all()

    def update_elo_rating(self, team_id: int, new_rating: int) -> bool:
        """Update team's ELO rating."""
        return self.update(team_id, {
            "current_elo_rating": new_rating
        }) is not None


class CircuitRepository(BaseRepository[Circuit]):
    """Repository for Circuit model with F1-specific methods."""

    def __init__(self, db_session: Session):
        super().__init__(Circuit, db_session)

    def get_by_name(self, circuit_name: str) -> Optional[Circuit]:
        """Get circuit by name."""
        return self.get_one_by_fields(circuit_name=circuit_name)

    def get_by_country(self, country: str) -> List[Circuit]:
        """Get circuits in a specific country."""
        return self.get_by_fields(country=country)

    def get_circuits_with_upcoming_races(self, season_year: int) -> List[Circuit]:
        """Get circuits that have upcoming races in the season."""
        return self.db.query(Circuit).join(Race).filter(
            Race.season_year == season_year,
            Race.status == RaceStatus.SCHEDULED,
            Race.race_date >= date.today()
        ).all()


class RaceRepository(BaseRepository[Race]):
    """Repository for Race model with F1-specific methods."""

    def __init__(self, db_session: Session):
        super().__init__(Race, db_session)

    def get_by_season(self, season_year: int) -> List[Race]:
        """Get all races for a specific season."""
        return self.db.query(Race).filter(
            Race.season_year == season_year
        ).order_by(Race.round_number).all()

    def get_completed_races(self, season_year: Optional[int] = None) -> List[Race]:
        """Get completed races, optionally filtered by season."""
        query = self.db.query(Race).filter(Race.status == RaceStatus.COMPLETED)

        if season_year:
            query = query.filter(Race.season_year == season_year)

        return query.order_by(desc(Race.race_date)).all()

    def get_upcoming_races(self, limit: int = 5) -> List[Race]:
        """Get upcoming scheduled races."""
        return self.db.query(Race).filter(
            Race.status == RaceStatus.SCHEDULED,
            Race.race_date >= date.today()
        ).order_by(Race.race_date).limit(limit).all()

    def get_next_race(self) -> Optional[Race]:
        """Get the next upcoming race."""
        return self.db.query(Race).filter(
            Race.status == RaceStatus.SCHEDULED,
            Race.race_date >= date.today()
        ).order_by(Race.race_date).first()

    def get_race_with_results(self, race_id: int) -> Optional[Race]:
        """Get race with all results loaded."""
        return self.db.query(Race).options(
            joinedload(Race.race_results).joinedload(RaceResult.driver),
            joinedload(Race.race_results).joinedload(RaceResult.team),
            joinedload(Race.qualifying_results).joinedload(QualifyingResult.driver),
            joinedload(Race.weather_data),
            joinedload(Race.circuit)
        ).filter(Race.race_id == race_id).first()

    def get_season_calendar(self, season_year: int) -> List[Race]:
        """Get full race calendar for a season with circuit info."""
        return self.db.query(Race).options(
            joinedload(Race.circuit)
        ).filter(
            Race.season_year == season_year
        ).order_by(Race.round_number).all()


class RaceResultRepository(BaseRepository[RaceResult]):
    """Repository for RaceResult model with F1-specific methods."""

    def __init__(self, db_session: Session):
        super().__init__(RaceResult, db_session)

    def get_by_race(self, race_id: int) -> List[RaceResult]:
        """Get all results for a specific race."""
        return self.db.query(RaceResult).filter(
            RaceResult.race_id == race_id
        ).order_by(RaceResult.final_position).all()

    def get_by_driver(self, driver_id: int, season_year: Optional[int] = None) -> List[RaceResult]:
        """Get all results for a specific driver."""
        query = self.db.query(RaceResult).join(Race).filter(
            RaceResult.driver_id == driver_id
        )

        if season_year:
            query = query.filter(Race.season_year == season_year)

        return query.order_by(desc(Race.race_date)).all()

    def get_driver_wins(self, driver_id: int) -> List[RaceResult]:
        """Get all wins for a specific driver."""
        return self.db.query(RaceResult).filter(
            RaceResult.driver_id == driver_id,
            RaceResult.final_position == 1
        ).join(Race).order_by(desc(Race.race_date)).all()

    def get_driver_podiums(self, driver_id: int) -> List[RaceResult]:
        """Get all podium finishes for a specific driver."""
        return self.db.query(RaceResult).filter(
            RaceResult.driver_id == driver_id,
            RaceResult.final_position.in_([1, 2, 3])
        ).join(Race).order_by(desc(Race.race_date)).all()

    def get_season_standings(self, season_year: int) -> List[Dict[str, Any]]:
        """Get championship standings for a season."""
        results = self.db.query(
            RaceResult.driver_id,
            Driver.driver_name,
            Driver.driver_code,
            func.sum(RaceResult.points).label('total_points'),
            func.count(RaceResult.result_id).label('races_entered'),
            func.count(
                func.case([(RaceResult.final_position == 1, 1)])
            ).label('wins'),
            func.count(
                func.case([(RaceResult.final_position.in_([1, 2, 3]), 1)])
            ).label('podiums')
        ).join(Driver).join(Race).filter(
            Race.season_year == season_year,
            Race.status == RaceStatus.COMPLETED
        ).group_by(
            RaceResult.driver_id,
            Driver.driver_name,
            Driver.driver_code
        ).order_by(desc('total_points')).all()

        return [
            {
                "driver_id": result.driver_id,
                "driver_name": result.driver_name,
                "driver_code": result.driver_code,
                "total_points": float(result.total_points or 0),
                "races_entered": result.races_entered,
                "wins": result.wins,
                "podiums": result.podiums,
                "position": idx + 1
            }
            for idx, result in enumerate(results)
        ]

    def get_race_winner(self, race_id: int) -> Optional[RaceResult]:
        """Get the winner of a specific race."""
        return self.db.query(RaceResult).filter(
            RaceResult.race_id == race_id,
            RaceResult.final_position == 1
        ).first()


class PredictionRepository(BaseRepository[Prediction]):
    """Repository for Prediction model with ML-specific methods."""

    def __init__(self, db_session: Session):
        super().__init__(Prediction, db_session)

    def get_by_race(self, race_id: int, model_version: Optional[str] = None) -> List[Prediction]:
        """Get all predictions for a specific race."""
        query = self.db.query(Prediction).filter(
            Prediction.race_id == race_id
        )

        if model_version:
            query = query.filter(Prediction.model_version == model_version)

        return query.order_by(desc(Prediction.predicted_win_probability)).all()

    def get_latest_predictions(self, race_id: int) -> List[Prediction]:
        """Get the latest predictions for a race (most recent model version)."""
        # Get the most recent model version for this race
        latest_version = self.db.query(
            func.max(Prediction.model_version)
        ).filter(
            Prediction.race_id == race_id
        ).scalar()

        if not latest_version:
            return []

        return self.get_by_race(race_id, latest_version)

    def get_by_driver_and_race(
        self,
        driver_id: int,
        race_id: int,
        model_version: Optional[str] = None
    ) -> Optional[Prediction]:
        """Get prediction for specific driver and race."""
        query = self.db.query(Prediction).filter(
            Prediction.driver_id == driver_id,
            Prediction.race_id == race_id
        )

        if model_version:
            query = query.filter(Prediction.model_version == model_version)
        else:
            # Get most recent prediction if no model version specified
            query = query.order_by(desc(Prediction.prediction_timestamp))

        return query.first()

    def create_predictions_batch(
        self,
        predictions_data: List[Dict[str, Any]]
    ) -> List[Prediction]:
        """Create multiple predictions in a single transaction."""
        return self.bulk_create(predictions_data)

    def get_model_versions(self) -> List[str]:
        """Get all available model versions."""
        versions = self.db.query(
            Prediction.model_version
        ).distinct().order_by(desc(Prediction.model_version)).all()

        return [version[0] for version in versions]


class PredictionAccuracyRepository(BaseRepository[PredictionAccuracy]):
    """Repository for PredictionAccuracy model with evaluation methods."""

    def __init__(self, db_session: Session):
        super().__init__(PredictionAccuracy, db_session)

    def get_by_race(self, race_id: int) -> Optional[PredictionAccuracy]:
        """Get accuracy metrics for a specific race."""
        return self.get_one_by_fields(race_id=race_id)

    def get_season_accuracy(self, season_year: int) -> List[PredictionAccuracy]:
        """Get accuracy metrics for all completed races in a season."""
        return self.db.query(PredictionAccuracy).join(Race).filter(
            Race.season_year == season_year,
            Race.status == RaceStatus.COMPLETED
        ).order_by(Race.race_date).all()

    def get_overall_accuracy_stats(self) -> Dict[str, Any]:
        """Get overall prediction accuracy statistics."""
        try:
            stats = self.db.query(
                func.avg(PredictionAccuracy.brier_score).label('avg_brier_score'),
                func.avg(PredictionAccuracy.log_loss).label('avg_log_loss'),
                func.avg(
                    func.case([(PredictionAccuracy.correct_winner == True, 1.0)], else_=0.0)
                ).label('correct_winner_percentage'),
                func.avg(
                    func.case([(PredictionAccuracy.top_3_accuracy == True, 1.0)], else_=0.0)
                ).label('top_3_accuracy_percentage'),
                func.count(PredictionAccuracy.accuracy_id).label('total_races')
            ).first()

            return {
                "avg_brier_score": float(stats.avg_brier_score or 0),
                "avg_log_loss": float(stats.avg_log_loss or 0),
                "correct_winner_percentage": float(stats.correct_winner_percentage or 0) * 100,
                "top_3_accuracy_percentage": float(stats.top_3_accuracy_percentage or 0) * 100,
                "total_races_evaluated": stats.total_races
            }

        except Exception as e:
            logger.error(f"Error getting overall accuracy stats: {e}")
            return {
                "avg_brier_score": 0.0,
                "avg_log_loss": 0.0,
                "correct_winner_percentage": 0.0,
                "top_3_accuracy_percentage": 0.0,
                "total_races_evaluated": 0
            }

    def get_accuracy_trends(self, limit: int = 20) -> List[Dict[str, Any]]:
        """Get accuracy trends over recent races."""
        results = self.db.query(
            PredictionAccuracy,
            Race.race_name,
            Race.race_date
        ).join(Race).order_by(
            desc(Race.race_date)
        ).limit(limit).all()

        return [
            {
                "race_id": acc.race_id,
                "race_name": race_name,
                "race_date": race_date.isoformat(),
                "brier_score": float(acc.brier_score or 0),
                "log_loss": float(acc.log_loss or 0),
                "correct_winner": acc.correct_winner,
                "top_3_accuracy": acc.top_3_accuracy
            }
            for acc, race_name, race_date in results
        ]


class WeatherDataRepository(BaseRepository[WeatherData]):
    """Repository for WeatherData model."""

    def __init__(self, db_session: Session):
        super().__init__(WeatherData, db_session)

    def get_by_race(self, race_id: int) -> Optional[WeatherData]:
        """Get weather data for a specific race."""
        return self.get_one_by_fields(race_id=race_id)

    def get_wet_races(self, season_year: Optional[int] = None) -> List[WeatherData]:
        """Get races with wet conditions."""
        query = self.db.query(WeatherData).filter(
            WeatherData.conditions.in_(['WET', 'MIXED'])
        )

        if season_year:
            query = query.join(Race).filter(Race.season_year == season_year)

        return query.all()


class QualifyingResultRepository(BaseRepository[QualifyingResult]):
    """Repository for QualifyingResult model."""

    def __init__(self, db_session: Session):
        super().__init__(QualifyingResult, db_session)

    def get_by_race(self, race_id: int) -> List[QualifyingResult]:
        """Get all qualifying results for a specific race."""
        return self.db.query(QualifyingResult).filter(
            QualifyingResult.race_id == race_id
        ).order_by(QualifyingResult.final_grid_position).all()

    def get_by_driver(self, driver_id: int, season_year: Optional[int] = None) -> List[QualifyingResult]:
        """Get all qualifying results for a specific driver."""
        query = self.db.query(QualifyingResult).join(Race).filter(
            QualifyingResult.driver_id == driver_id
        )

        if season_year:
            query = query.filter(Race.season_year == season_year)

        return query.order_by(desc(Race.race_date)).all()

    def get_pole_positions(self, driver_id: int) -> List[QualifyingResult]:
        """Get all pole positions for a specific driver."""
        return self.db.query(QualifyingResult).filter(
            QualifyingResult.driver_id == driver_id,
            QualifyingResult.final_grid_position == 1
        ).join(Race).order_by(desc(Race.race_date)).all()