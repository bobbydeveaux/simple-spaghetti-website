"""
Advanced data transformation utilities for F1 Analytics.

This module provides sophisticated data transformation patterns,
format converters, and data enrichment utilities.
"""

import json
import re
from typing import Any, Dict, List, Optional, Union, Callable
from datetime import datetime, date, timedelta
from decimal import Decimal
from dataclasses import dataclass

from ..models.f1_models import Driver, Race, Team, RaceResult, Prediction


@dataclass
class TransformationConfig:
    """Configuration for data transformations."""
    include_metadata: bool = True
    include_relationships: bool = True
    datetime_format: str = "iso"
    decimal_places: int = 2
    include_calculated_fields: bool = True


class F1DataTransformer:
    """Advanced transformer for F1-specific data formats and calculations."""

    def __init__(self, config: Optional[TransformationConfig] = None):
        self.config = config or TransformationConfig()

    def transform_driver_for_api(
        self,
        driver: Driver,
        include_stats: bool = False,
        season: Optional[int] = None
    ) -> Dict[str, Any]:
        """Transform driver data for API response with optional statistics."""
        result = {
            "driver_id": driver.driver_id,
            "driver_code": driver.driver_code,
            "driver_name": driver.driver_name,
            "nationality": driver.nationality,
            "date_of_birth": driver.date_of_birth.isoformat() if driver.date_of_birth else None,
            "current_team_id": driver.current_team_id,
            "current_elo_rating": driver.current_elo_rating,
        }

        if self.config.include_metadata:
            result.update({
                "created_at": self._format_datetime(driver.created_at),
                "updated_at": self._format_datetime(driver.updated_at),
            })

        if self.config.include_relationships and driver.current_team:
            result["current_team"] = {
                "team_id": driver.current_team.team_id,
                "team_name": driver.current_team.team_name,
                "team_color": driver.current_team.team_color,
            }

        if self.config.include_calculated_fields:
            result.update({
                "age": self._calculate_age(driver.date_of_birth),
                "elo_category": self._categorize_elo_rating(driver.current_elo_rating),
                "experience_level": self._calculate_experience_level(driver),
            })

        return result

    def transform_race_for_api(
        self,
        race: Race,
        include_results: bool = False,
        include_predictions: bool = False
    ) -> Dict[str, Any]:
        """Transform race data for API response with optional related data."""
        result = {
            "race_id": race.race_id,
            "season_year": race.season_year,
            "round_number": race.round_number,
            "race_name": race.race_name,
            "race_date": race.race_date.isoformat(),
            "status": race.status.value,
        }

        if self.config.include_relationships and race.circuit:
            result["circuit"] = {
                "circuit_id": race.circuit.circuit_id,
                "circuit_name": race.circuit.circuit_name,
                "location": race.circuit.location,
                "country": race.circuit.country,
                "track_length_km": float(race.circuit.track_length_km) if race.circuit.track_length_km else None,
            }

        if self.config.include_calculated_fields:
            result.update({
                "is_upcoming": race.is_upcoming(),
                "is_completed": race.is_completed(),
                "days_until_race": self._calculate_days_until_race(race.race_date),
                "season_progress": self._calculate_season_progress(race),
            })

        return result

    def transform_prediction_summary(
        self,
        predictions: List[Prediction],
        race: Race
    ) -> Dict[str, Any]:
        """Transform prediction list into comprehensive summary."""
        if not predictions:
            return {}

        sorted_predictions = sorted(
            predictions,
            key=lambda p: p.predicted_win_probability,
            reverse=True
        )

        # Calculate statistics
        total_probability = sum(float(p.predicted_win_probability) for p in predictions)
        favorite = sorted_predictions[0] if sorted_predictions else None
        top_3 = sorted_predictions[:3]

        # Calculate entropy (measure of uncertainty)
        entropy = self._calculate_prediction_entropy(predictions)

        # Group predictions by probability ranges
        probability_distribution = self._group_predictions_by_probability(predictions)

        result = {
            "race_id": race.race_id,
            "race_name": race.race_name,
            "race_date": race.race_date.isoformat(),
            "model_version": predictions[0].model_version if predictions else None,
            "generated_at": self._format_datetime(predictions[0].prediction_timestamp) if predictions else None,
            "total_drivers": len(predictions),
            "statistics": {
                "total_probability": round(total_probability, 2),
                "entropy": round(entropy, 4),
                "competitiveness_score": round(self._calculate_competitiveness_score(predictions), 2),
                "prediction_spread": round(max(float(p.predicted_win_probability) for p in predictions) -
                                         min(float(p.predicted_win_probability) for p in predictions), 2),
            },
            "favorite": {
                "driver_id": favorite.driver_id,
                "predicted_win_probability": float(favorite.predicted_win_probability),
            } if favorite else None,
            "top_3_contenders": [
                {
                    "driver_id": p.driver_id,
                    "predicted_win_probability": float(p.predicted_win_probability),
                }
                for p in top_3
            ],
            "probability_distribution": probability_distribution,
        }

        return result

    def transform_race_result_with_context(
        self,
        result: RaceResult,
        include_performance_metrics: bool = True
    ) -> Dict[str, Any]:
        """Transform race result with performance context and metrics."""
        base_result = {
            "result_id": result.result_id,
            "race_id": result.race_id,
            "driver_id": result.driver_id,
            "team_id": result.team_id,
            "grid_position": result.grid_position,
            "final_position": result.final_position,
            "points": float(result.points) if result.points else 0,
            "fastest_lap_time": result.fastest_lap_time,
            "status": result.status.value,
        }

        if include_performance_metrics and result.grid_position and result.final_position:
            position_change = result.grid_position - result.final_position
            base_result.update({
                "position_change": position_change,
                "position_change_category": self._categorize_position_change(position_change),
                "performance_rating": self._calculate_performance_rating(result),
                "points_efficiency": self._calculate_points_efficiency(result),
            })

        if self.config.include_calculated_fields:
            base_result.update({
                "is_winner": result.is_winner(),
                "is_podium": result.is_podium(),
                "is_points_finish": result.is_points_finish(),
                "race_completion_rate": self._calculate_race_completion_rate(result),
            })

        return base_result

    def batch_transform_drivers(
        self,
        drivers: List[Driver],
        transformation_func: Optional[Callable] = None
    ) -> List[Dict[str, Any]]:
        """Batch transform multiple drivers with optional custom function."""
        if transformation_func:
            return [transformation_func(driver) for driver in drivers]
        return [self.transform_driver_for_api(driver) for driver in drivers]

    def enrich_prediction_with_context(
        self,
        prediction: Prediction,
        historical_accuracy: Optional[float] = None,
        market_odds: Optional[float] = None
    ) -> Dict[str, Any]:
        """Enrich prediction with additional context and metadata."""
        base_prediction = {
            "prediction_id": prediction.prediction_id,
            "race_id": prediction.race_id,
            "driver_id": prediction.driver_id,
            "predicted_win_probability": float(prediction.predicted_win_probability),
            "model_version": prediction.model_version,
            "prediction_timestamp": self._format_datetime(prediction.prediction_timestamp),
        }

        # Add confidence indicators
        confidence_level = self._calculate_confidence_level(prediction.predicted_win_probability)
        base_prediction["confidence"] = {
            "level": confidence_level,
            "category": self._categorize_confidence(confidence_level),
        }

        # Add external context if available
        if historical_accuracy is not None:
            base_prediction["model_accuracy"] = {
                "historical_accuracy": round(historical_accuracy, 3),
                "reliability_score": self._calculate_reliability_score(
                    float(prediction.predicted_win_probability),
                    historical_accuracy
                ),
            }

        if market_odds is not None:
            base_prediction["market_comparison"] = {
                "market_implied_probability": round(1 / market_odds * 100, 2),
                "model_market_diff": round(
                    float(prediction.predicted_win_probability) - (1 / market_odds * 100),
                    2
                ),
            }

        return base_prediction

    def create_season_summary(
        self,
        races: List[Race],
        results: List[RaceResult],
        predictions: List[Prediction],
        season: int
    ) -> Dict[str, Any]:
        """Create comprehensive season summary with statistics."""
        completed_races = [r for r in races if r.is_completed()]
        upcoming_races = [r for r in races if r.is_upcoming()]

        # Calculate season statistics
        total_races = len(races)
        races_completed = len(completed_races)
        completion_rate = races_completed / total_races if total_races > 0 else 0

        # Driver statistics
        driver_stats = self._calculate_season_driver_stats(results)
        team_stats = self._calculate_season_team_stats(results)

        # Prediction accuracy
        prediction_accuracy = self._calculate_season_prediction_accuracy(predictions, results)

        return {
            "season": season,
            "overview": {
                "total_races": total_races,
                "completed_races": races_completed,
                "upcoming_races": len(upcoming_races),
                "completion_rate": round(completion_rate, 3),
                "season_progress": round(completion_rate * 100, 1),
            },
            "driver_championship": driver_stats[:10],  # Top 10
            "constructor_championship": team_stats[:10],  # Top 10
            "prediction_performance": prediction_accuracy,
            "next_race": self.transform_race_for_api(upcoming_races[0]) if upcoming_races else None,
            "last_completed": self.transform_race_for_api(
                completed_races[-1]
            ) if completed_races else None,
        }

    # Helper methods for calculations and formatting

    def _format_datetime(self, dt: Optional[datetime]) -> Optional[str]:
        """Format datetime based on configuration."""
        if not dt:
            return None

        if self.config.datetime_format == "iso":
            return dt.isoformat() + 'Z'
        elif self.config.datetime_format == "timestamp":
            return int(dt.timestamp())
        else:
            return dt.strftime(self.config.datetime_format)

    def _calculate_age(self, birth_date: Optional[date]) -> Optional[int]:
        """Calculate age from birth date."""
        if not birth_date:
            return None

        today = date.today()
        return today.year - birth_date.year - (
            (today.month, today.day) < (birth_date.month, birth_date.day)
        )

    def _categorize_elo_rating(self, rating: int) -> str:
        """Categorize ELO rating into performance tiers."""
        if rating >= 2200:
            return "elite"
        elif rating >= 1800:
            return "top_tier"
        elif rating >= 1500:
            return "competitive"
        elif rating >= 1200:
            return "developing"
        else:
            return "rookie"

    def _calculate_experience_level(self, driver: Driver) -> str:
        """Calculate driver experience level based on career data."""
        # Simplified calculation - in reality would use race count, years active, etc.
        if driver.current_elo_rating >= 2000:
            return "veteran"
        elif driver.current_elo_rating >= 1700:
            return "experienced"
        elif driver.current_elo_rating >= 1400:
            return "intermediate"
        else:
            return "newcomer"

    def _calculate_days_until_race(self, race_date: date) -> Optional[int]:
        """Calculate days until race."""
        today = date.today()
        if race_date > today:
            return (race_date - today).days
        return None

    def _calculate_season_progress(self, race: Race) -> float:
        """Calculate how far through the season this race is."""
        # Simplified - assumes 24 races per season
        return min(race.round_number / 24.0, 1.0)

    def _calculate_prediction_entropy(self, predictions: List[Prediction]) -> float:
        """Calculate entropy (uncertainty) of predictions."""
        import math

        probabilities = [float(p.predicted_win_probability) / 100.0 for p in predictions]
        # Normalize probabilities to sum to 1
        total = sum(probabilities)
        if total == 0:
            return 0

        normalized_probs = [p / total for p in probabilities]
        entropy = -sum(p * math.log2(p) for p in normalized_probs if p > 0)
        return entropy

    def _calculate_competitiveness_score(self, predictions: List[Prediction]) -> float:
        """Calculate how competitive the race is based on prediction spread."""
        if len(predictions) < 2:
            return 0

        probabilities = [float(p.predicted_win_probability) for p in predictions]
        max_prob = max(probabilities)
        min_prob = min(probabilities)
        spread = max_prob - min_prob

        # More competitive = smaller spread between top and bottom
        competitiveness = 100 - (spread / len(predictions))
        return max(0, min(100, competitiveness))

    def _group_predictions_by_probability(
        self,
        predictions: List[Prediction]
    ) -> Dict[str, int]:
        """Group predictions by probability ranges."""
        ranges = {
            "very_likely": 0,    # 40%+
            "likely": 0,         # 20-40%
            "possible": 0,       # 10-20%
            "unlikely": 0,       # 5-10%
            "very_unlikely": 0,  # <5%
        }

        for prediction in predictions:
            prob = float(prediction.predicted_win_probability)
            if prob >= 40:
                ranges["very_likely"] += 1
            elif prob >= 20:
                ranges["likely"] += 1
            elif prob >= 10:
                ranges["possible"] += 1
            elif prob >= 5:
                ranges["unlikely"] += 1
            else:
                ranges["very_unlikely"] += 1

        return ranges

    def _categorize_position_change(self, position_change: int) -> str:
        """Categorize position change in race."""
        if position_change >= 10:
            return "major_gain"
        elif position_change >= 5:
            return "significant_gain"
        elif position_change >= 1:
            return "minor_gain"
        elif position_change == 0:
            return "no_change"
        elif position_change >= -5:
            return "minor_loss"
        elif position_change >= -10:
            return "significant_loss"
        else:
            return "major_loss"

    def _calculate_performance_rating(self, result: RaceResult) -> float:
        """Calculate performance rating for a race result."""
        base_score = 50.0  # Neutral performance

        # Adjust for finishing position
        if result.final_position:
            if result.final_position == 1:
                base_score += 50
            elif result.final_position <= 3:
                base_score += 30
            elif result.final_position <= 10:
                base_score += 10
            elif result.final_position <= 15:
                base_score -= 10
            else:
                base_score -= 20

        # Adjust for position change
        if result.grid_position and result.final_position:
            position_change = result.grid_position - result.final_position
            base_score += position_change * 2

        # Adjust for points
        if result.points:
            base_score += float(result.points)

        return max(0, min(100, base_score))

    def _calculate_points_efficiency(self, result: RaceResult) -> float:
        """Calculate how efficiently points were earned relative to grid position."""
        if not result.grid_position or not result.points:
            return 0.0

        # Expected points based on grid position (simplified)
        expected_points = max(0, 26 - result.grid_position)
        actual_points = float(result.points)

        if expected_points == 0:
            return actual_points * 10  # Bonus for unexpected points

        return actual_points / expected_points

    def _calculate_race_completion_rate(self, result: RaceResult) -> float:
        """Calculate race completion rate (simplified)."""
        from ..models.f1_models import ResultStatus

        if result.status == ResultStatus.FINISHED:
            return 1.0
        elif result.status == ResultStatus.RETIRED:
            return 0.8  # Assume completed 80% before retiring
        else:
            return 0.0

    def _calculate_confidence_level(self, probability: float) -> float:
        """Calculate confidence level for a prediction."""
        # Higher probability = higher confidence (simplified)
        return min(1.0, probability / 50.0)

    def _categorize_confidence(self, confidence: float) -> str:
        """Categorize confidence level."""
        if confidence >= 0.8:
            return "very_high"
        elif confidence >= 0.6:
            return "high"
        elif confidence >= 0.4:
            return "medium"
        elif confidence >= 0.2:
            return "low"
        else:
            return "very_low"

    def _calculate_reliability_score(self, probability: float, accuracy: float) -> float:
        """Calculate reliability score based on probability and historical accuracy."""
        return probability * accuracy / 100.0

    def _calculate_season_driver_stats(self, results: List[RaceResult]) -> List[Dict[str, Any]]:
        """Calculate season statistics for drivers."""
        from collections import defaultdict

        driver_stats = defaultdict(lambda: {
            "wins": 0,
            "podiums": 0,
            "points": 0.0,
            "races": 0
        })

        for result in results:
            stats = driver_stats[result.driver_id]
            stats["races"] += 1
            if result.points:
                stats["points"] += float(result.points)
            if result.final_position == 1:
                stats["wins"] += 1
            if result.final_position and result.final_position <= 3:
                stats["podiums"] += 1

        # Convert to sorted list
        return sorted([
            {
                "driver_id": driver_id,
                "position": idx + 1,
                **stats
            }
            for idx, (driver_id, stats) in enumerate(
                sorted(driver_stats.items(), key=lambda x: x[1]["points"], reverse=True)
            )
        ], key=lambda x: x["points"], reverse=True)

    def _calculate_season_team_stats(self, results: List[RaceResult]) -> List[Dict[str, Any]]:
        """Calculate season statistics for teams."""
        from collections import defaultdict

        team_stats = defaultdict(lambda: {
            "wins": 0,
            "podiums": 0,
            "points": 0.0,
            "races": 0
        })

        for result in results:
            stats = team_stats[result.team_id]
            stats["races"] += 1
            if result.points:
                stats["points"] += float(result.points)
            if result.final_position == 1:
                stats["wins"] += 1
            if result.final_position and result.final_position <= 3:
                stats["podiums"] += 1

        return sorted([
            {
                "team_id": team_id,
                "position": idx + 1,
                **stats
            }
            for idx, (team_id, stats) in enumerate(
                sorted(team_stats.items(), key=lambda x: x[1]["points"], reverse=True)
            )
        ], key=lambda x: x["points"], reverse=True)

    def _calculate_season_prediction_accuracy(
        self,
        predictions: List[Prediction],
        results: List[RaceResult]
    ) -> Dict[str, float]:
        """Calculate prediction accuracy for the season."""
        if not predictions or not results:
            return {"accuracy": 0.0, "total_predictions": 0}

        # Group by race
        from collections import defaultdict
        predictions_by_race = defaultdict(list)
        results_by_race = defaultdict(list)

        for prediction in predictions:
            predictions_by_race[prediction.race_id].append(prediction)

        for result in results:
            results_by_race[result.race_id].append(result)

        correct_predictions = 0
        total_races = 0

        for race_id in predictions_by_race.keys():
            if race_id in results_by_race:
                race_predictions = predictions_by_race[race_id]
                race_results = results_by_race[race_id]

                # Find winner
                winner = next((r for r in race_results if r.final_position == 1), None)
                predicted_winner = max(
                    race_predictions,
                    key=lambda p: p.predicted_win_probability
                ) if race_predictions else None

                if winner and predicted_winner and winner.driver_id == predicted_winner.driver_id:
                    correct_predictions += 1

                total_races += 1

        accuracy = correct_predictions / total_races if total_races > 0 else 0.0

        return {
            "accuracy": round(accuracy, 3),
            "correct_predictions": correct_predictions,
            "total_races": total_races,
            "total_predictions": len(predictions)
        }