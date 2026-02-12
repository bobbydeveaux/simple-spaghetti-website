"""
Prediction service for ML model data transformation and management.

This module handles prediction-related operations including model predictions,
accuracy tracking, and batch processing.
"""

from typing import List, Optional, Dict, Any, Tuple
from datetime import datetime, timedelta
from decimal import Decimal
from sqlalchemy.orm import Session
from sqlalchemy import desc, and_, func

from ..models.f1_models import (
    Prediction, PredictionAccuracy, Race, Driver, Team, RaceResult,
    RaceStatus
)
from ..schemas.prediction import (
    PredictionCreate, PredictionUpdate, PredictionResponse,
    RacePredictionsSummary, PredictionAccuracyResponse,
    ModelPerformanceMetrics, BatchPredictionRequest, BatchPredictionResponse
)
from .base import BaseService, DataValidator, DataTransformationError


class PredictionService(BaseService[Prediction, PredictionCreate, PredictionUpdate, PredictionResponse]):
    """Service for prediction data operations and transformations."""

    def __init__(self):
        super().__init__(
            model=Prediction,
            create_schema=PredictionCreate,
            update_schema=PredictionUpdate,
            response_schema=PredictionResponse
        )

    def create_prediction(
        self,
        db: Session,
        prediction_data: PredictionCreate
    ) -> PredictionResponse:
        """Create a new prediction with validation."""
        # Validate race exists and is not completed
        race = db.query(Race).filter(Race.race_id == prediction_data.race_id).first()
        if not race:
            raise DataTransformationError(f"Race with ID {prediction_data.race_id} not found")

        if race.status == RaceStatus.COMPLETED:
            raise DataTransformationError("Cannot create predictions for completed races")

        # Validate driver exists
        driver = db.query(Driver).filter(Driver.driver_id == prediction_data.driver_id).first()
        if not driver:
            raise DataTransformationError(f"Driver with ID {prediction_data.driver_id} not found")

        # Check if prediction already exists for this combination
        existing_prediction = db.query(Prediction).filter(
            Prediction.race_id == prediction_data.race_id,
            Prediction.driver_id == prediction_data.driver_id,
            Prediction.model_version == prediction_data.model_version
        ).first()

        if existing_prediction:
            raise DataTransformationError(
                f"Prediction already exists for driver {prediction_data.driver_id}, "
                f"race {prediction_data.race_id}, model {prediction_data.model_version}"
            )

        # Validate probability
        DataValidator.validate_probability(float(prediction_data.predicted_win_probability))

        # Create prediction
        return self.create(db=db, obj_in=prediction_data)

    def get_race_predictions(
        self,
        db: Session,
        race_id: int,
        model_version: Optional[str] = None
    ) -> RacePredictionsSummary:
        """Get all predictions for a race."""
        race = db.query(Race).filter(Race.race_id == race_id).first()
        if not race:
            raise DataTransformationError(f"Race with ID {race_id} not found")

        # Build query
        query = db.query(Prediction).filter(Prediction.race_id == race_id)

        if model_version:
            query = query.filter(Prediction.model_version == model_version)

        # Get latest predictions if no model version specified
        if not model_version:
            # Get the most recent model version
            latest_version = db.query(Prediction.model_version).filter(
                Prediction.race_id == race_id
            ).order_by(desc(Prediction.prediction_timestamp)).first()

            if latest_version:
                query = query.filter(Prediction.model_version == latest_version.model_version)

        predictions = query.order_by(desc(Prediction.predicted_win_probability)).all()

        if not predictions:
            raise DataTransformationError(f"No predictions found for race {race_id}")

        # Transform to response schemas
        prediction_responses = [self._to_response_schema(pred) for pred in predictions]

        return RacePredictionsSummary(
            race_id=race_id,
            race_name=race.race_name,
            race_date=race.race_date.isoformat(),
            circuit_name=race.circuit.circuit_name if race.circuit else "Unknown Circuit",
            model_version=predictions[0].model_version,
            generated_at=predictions[0].prediction_timestamp,
            total_drivers=len(predictions),
            predictions=prediction_responses
        )

    def get_driver_predictions(
        self,
        db: Session,
        driver_id: int,
        season: Optional[int] = None,
        limit: int = 10
    ) -> List[PredictionResponse]:
        """Get predictions for a specific driver."""
        query = db.query(Prediction).join(Race).filter(Prediction.driver_id == driver_id)

        if season:
            query = query.filter(Race.season_year == season)

        predictions = query.order_by(desc(Prediction.prediction_timestamp)).limit(limit).all()
        return [self._to_response_schema(pred) for pred in predictions]

    def batch_create_predictions(
        self,
        db: Session,
        request: BatchPredictionRequest
    ) -> BatchPredictionResponse:
        """Create predictions for multiple races."""
        request_id = f"batch_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}"
        model_version = request.model_version or f"v{datetime.utcnow().strftime('%Y.%m.%d')}"

        predictions_by_race = {}
        errors = []
        total_predictions = 0

        for race_id in request.race_ids:
            try:
                # Generate predictions for this race
                race_predictions = self._generate_race_predictions(
                    db, race_id, model_version, request
                )
                predictions_by_race[race_id] = race_predictions
                total_predictions += len(race_predictions.predictions)

            except Exception as e:
                errors.append(f"Race {race_id}: {str(e)}")

        return BatchPredictionResponse(
            request_id=request_id,
            model_version=model_version,
            processed_at=datetime.utcnow(),
            total_races=len(request.race_ids),
            total_predictions=total_predictions,
            predictions_by_race=predictions_by_race,
            errors=errors
        )

    def update_prediction_accuracy(
        self,
        db: Session,
        race_id: int
    ) -> PredictionAccuracyResponse:
        """Calculate and update prediction accuracy after race completion."""
        race = db.query(Race).filter(Race.race_id == race_id).first()
        if not race:
            raise DataTransformationError(f"Race with ID {race_id} not found")

        if race.status != RaceStatus.COMPLETED:
            raise DataTransformationError("Cannot calculate accuracy for non-completed race")

        # Get predictions and actual results
        predictions = db.query(Prediction).filter(Prediction.race_id == race_id).all()
        results = db.query(RaceResult).filter(RaceResult.race_id == race_id).all()

        if not predictions or not results:
            raise DataTransformationError("Missing predictions or results for accuracy calculation")

        # Calculate accuracy metrics
        accuracy_metrics = self._calculate_accuracy_metrics(predictions, results)

        # Update or create accuracy record
        accuracy_record = db.query(PredictionAccuracy).filter(
            PredictionAccuracy.race_id == race_id
        ).first()

        if accuracy_record:
            for field, value in accuracy_metrics.items():
                setattr(accuracy_record, field, value)
        else:
            accuracy_record = PredictionAccuracy(
                race_id=race_id,
                **accuracy_metrics
            )
            db.add(accuracy_record)

        db.commit()
        db.refresh(accuracy_record)

        return PredictionAccuracyResponse.model_validate(accuracy_record)

    def get_model_performance(
        self,
        db: Session,
        model_version: str,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None
    ) -> ModelPerformanceMetrics:
        """Get comprehensive model performance metrics."""
        # Default to last 3 months if no dates provided
        if not end_date:
            end_date = datetime.utcnow()
        if not start_date:
            start_date = end_date - timedelta(days=90)

        # Get accuracy records for the period
        accuracy_query = db.query(PredictionAccuracy).join(Race).join(
            Prediction, PredictionAccuracy.race_id == Prediction.race_id
        ).filter(
            Prediction.model_version == model_version,
            Race.race_date >= start_date.date(),
            Race.race_date <= end_date.date()
        )

        accuracy_records = accuracy_query.all()

        if not accuracy_records:
            raise DataTransformationError(f"No accuracy data found for model {model_version}")

        # Calculate aggregate metrics
        total_races = len(accuracy_records)
        avg_brier_score = sum(float(r.brier_score) for r in accuracy_records if r.brier_score) / total_races
        avg_log_loss = sum(float(r.log_loss) for r in accuracy_records if r.log_loss) / total_races

        correct_winners = sum(1 for r in accuracy_records if r.correct_winner)
        winner_accuracy = correct_winners / total_races if total_races > 0 else 0

        top_3_correct = sum(1 for r in accuracy_records if r.top_3_accuracy)
        top_3_accuracy = top_3_correct / total_races if total_races > 0 else 0

        return ModelPerformanceMetrics(
            model_version=model_version,
            evaluation_period_start=start_date,
            evaluation_period_end=end_date,
            total_races_evaluated=total_races,
            average_brier_score=avg_brier_score,
            average_log_loss=avg_log_loss,
            winner_prediction_accuracy=winner_accuracy,
            top_3_prediction_accuracy=top_3_accuracy,
            calibration_error=None,  # Would need more complex calculation
            reliability_score=None,   # Would need more complex calculation
            prediction_spread=None,   # Would need more complex calculation
            confidence_correlation=None  # Would need confidence data
        )

    def get_next_race_predictions(
        self,
        db: Session,
        model_version: Optional[str] = None
    ) -> Optional[RacePredictionsSummary]:
        """Get predictions for the next upcoming race."""
        # Find next scheduled race
        next_race = db.query(Race).filter(
            Race.status == RaceStatus.SCHEDULED,
            Race.race_date >= datetime.now().date()
        ).order_by(Race.race_date).first()

        if not next_race:
            return None

        try:
            return self.get_race_predictions(db, next_race.race_id, model_version)
        except DataTransformationError:
            # No predictions available for next race
            return None

    def _generate_race_predictions(
        self,
        db: Session,
        race_id: int,
        model_version: str,
        request: BatchPredictionRequest
    ) -> RacePredictionsSummary:
        """Generate predictions for a single race (placeholder implementation)."""
        # This is a placeholder - in a real implementation, this would:
        # 1. Load the ML model
        # 2. Fetch feature data for drivers
        # 3. Generate predictions
        # 4. Store predictions in database
        # 5. Return formatted response

        race = db.query(Race).filter(Race.race_id == race_id).first()
        if not race:
            raise DataTransformationError(f"Race with ID {race_id} not found")

        # Get drivers (simplified - would use more sophisticated selection)
        drivers = db.query(Driver).limit(20).all()

        predictions = []
        for i, driver in enumerate(drivers):
            # Generate mock prediction (replace with actual ML model)
            probability = max(5.0, 50.0 - (i * 2.5))  # Decreasing probabilities

            prediction_data = PredictionCreate(
                race_id=race_id,
                driver_id=driver.driver_id,
                predicted_win_probability=Decimal(str(probability)),
                model_version=model_version
            )

            prediction = self.create_prediction(db, prediction_data)
            predictions.append(prediction)

        return RacePredictionsSummary(
            race_id=race_id,
            race_name=race.race_name,
            race_date=race.race_date.isoformat(),
            circuit_name=race.circuit.circuit_name if race.circuit else "Unknown Circuit",
            model_version=model_version,
            generated_at=datetime.utcnow(),
            total_drivers=len(predictions),
            predictions=predictions
        )

    def _calculate_accuracy_metrics(
        self,
        predictions: List[Prediction],
        results: List[RaceResult]
    ) -> Dict[str, Any]:
        """Calculate accuracy metrics for predictions."""
        # Create lookup for results
        results_by_driver = {r.driver_id: r for r in results}

        # Find actual winner
        actual_winner = next((r for r in results if r.final_position == 1), None)
        actual_top_3 = [r.driver_id for r in results if r.final_position and r.final_position <= 3]

        # Find predicted winner
        predicted_winner = max(predictions, key=lambda p: p.predicted_win_probability)

        # Calculate metrics
        correct_winner = actual_winner and predicted_winner.driver_id == actual_winner.driver_id
        top_3_accuracy = predicted_winner.driver_id in actual_top_3

        # Calculate Brier score
        brier_score = 0.0
        for prediction in predictions:
            actual_outcome = 1.0 if (actual_winner and prediction.driver_id == actual_winner.driver_id) else 0.0
            predicted_prob = float(prediction.predicted_win_probability) / 100.0
            brier_score += (predicted_prob - actual_outcome) ** 2

        brier_score = brier_score / len(predictions)

        # Calculate log loss
        log_loss = 0.0
        for prediction in predictions:
            actual_outcome = 1.0 if (actual_winner and prediction.driver_id == actual_winner.driver_id) else 0.0
            predicted_prob = max(0.001, min(0.999, float(prediction.predicted_win_probability) / 100.0))

            if actual_outcome == 1.0:
                log_loss -= actual_outcome * func.log(predicted_prob).compile().process(None)
            else:
                log_loss -= (1 - actual_outcome) * func.log(1 - predicted_prob).compile().process(None)

        log_loss = log_loss / len(predictions)

        return {
            'brier_score': Decimal(str(round(brier_score, 4))),
            'log_loss': Decimal(str(round(log_loss, 4))),
            'correct_winner': correct_winner,
            'top_3_accuracy': top_3_accuracy
        }