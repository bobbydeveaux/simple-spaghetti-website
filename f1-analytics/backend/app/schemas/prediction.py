"""
Pydantic schemas for prediction-related API operations.

This module provides schemas for ML prediction data validation,
serialization, and transformation.
"""

from datetime import datetime
from decimal import Decimal
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field, validator

from .base import BaseSchema, TimestampMixin, PaginatedResponse


class PredictionBase(BaseSchema):
    """Base prediction schema with common fields."""

    race_id: int = Field(..., gt=0, description="Race identifier")
    driver_id: int = Field(..., gt=0, description="Driver identifier")
    predicted_win_probability: Decimal = Field(
        ...,
        ge=0,
        le=100,
        description="Predicted win probability (0-100%)"
    )
    model_version: str = Field(
        ...,
        min_length=1,
        max_length=50,
        description="ML model version used for prediction"
    )

    @validator('predicted_win_probability')
    def validate_probability(cls, v):
        """Validate probability is within valid range."""
        if v < 0 or v > 100:
            raise ValueError('Probability must be between 0 and 100')
        return v

    @validator('model_version')
    def validate_model_version(cls, v):
        """Validate model version format."""
        if not v.strip():
            raise ValueError('Model version cannot be empty')
        return v.strip()


class PredictionCreate(PredictionBase):
    """Schema for creating a new prediction."""

    prediction_timestamp: Optional[datetime] = Field(
        None,
        description="When the prediction was generated (defaults to now)"
    )

    @validator('prediction_timestamp', pre=True, always=True)
    def set_prediction_timestamp(cls, v):
        """Set default prediction timestamp."""
        return v or datetime.utcnow()


class PredictionUpdate(BaseModel):
    """Schema for updating a prediction."""

    predicted_win_probability: Optional[Decimal] = Field(
        None,
        ge=0,
        le=100,
        description="Updated win probability"
    )
    model_version: Optional[str] = Field(
        None,
        min_length=1,
        max_length=50,
        description="Updated model version"
    )

    @validator('predicted_win_probability')
    def validate_probability(cls, v):
        """Validate probability is within valid range."""
        if v is not None and (v < 0 or v > 100):
            raise ValueError('Probability must be between 0 and 100')
        return v

    @validator('model_version')
    def validate_model_version(cls, v):
        """Validate model version format."""
        if v is not None and not v.strip():
            raise ValueError('Model version cannot be empty')
        return v.strip() if v else v


class PredictionResponse(PredictionBase, TimestampMixin):
    """Schema for prediction response."""

    prediction_id: int = Field(..., description="Unique prediction identifier")
    prediction_timestamp: datetime = Field(..., description="When prediction was generated")

    # Related data
    race: Optional['RaceBasic'] = Field(None, description="Race information")
    driver: Optional['DriverBasic'] = Field(None, description="Driver information")
    team: Optional['TeamBasic'] = Field(None, description="Team information (via driver)")


class PredictionWithDetails(PredictionResponse):
    """Extended prediction response with additional context."""

    # Driver context
    driver_elo_rating: Optional[int] = Field(None, description="Driver ELO rating at time of prediction")
    driver_recent_form: Optional[float] = Field(None, description="Driver recent performance form")

    # Team context
    team_elo_rating: Optional[int] = Field(None, description="Team ELO rating at time of prediction")
    team_recent_form: Optional[float] = Field(None, description="Team recent performance form")

    # Circuit context
    circuit_name: Optional[str] = Field(None, description="Circuit name")
    driver_circuit_history: Optional[Dict[str, Any]] = Field(None, description="Driver's history at this circuit")

    # Model context
    confidence_interval: Optional[Dict[str, float]] = Field(None, description="Prediction confidence interval")
    feature_importance: Optional[Dict[str, float]] = Field(None, description="Feature importance scores")


class RacePredictionsSummary(BaseSchema):
    """Schema for complete race predictions summary."""

    race_id: int = Field(..., description="Race identifier")
    race_name: str = Field(..., description="Race name")
    race_date: str = Field(..., description="Race date")
    circuit_name: str = Field(..., description="Circuit name")
    model_version: str = Field(..., description="Model version used")
    generated_at: datetime = Field(..., description="When predictions were generated")
    total_drivers: int = Field(..., ge=1, description="Number of drivers with predictions")

    predictions: List[PredictionResponse] = Field(..., description="Driver predictions")

    @validator('predictions')
    def validate_probabilities_sum(cls, v):
        """Validate that probabilities are reasonable (don't need to sum to 100 exactly)."""
        if not v:
            raise ValueError('At least one prediction is required')

        total_probability = sum(float(p.predicted_win_probability) for p in v)
        if total_probability > 120:  # Allow some tolerance for model uncertainties
            raise ValueError('Total probabilities seem unreasonably high')

        return v

    @property
    def favorite(self) -> Optional[PredictionResponse]:
        """Get the driver with highest win probability."""
        return max(self.predictions, key=lambda p: p.predicted_win_probability) if self.predictions else None

    @property
    def total_probability(self) -> float:
        """Get total probability across all drivers."""
        return sum(float(p.predicted_win_probability) for p in self.predictions)


class PredictionAccuracyBase(BaseSchema):
    """Base prediction accuracy schema."""

    race_id: int = Field(..., gt=0, description="Race identifier")
    brier_score: Optional[Decimal] = Field(
        None,
        ge=0,
        le=2,
        description="Brier score (lower is better)"
    )
    log_loss: Optional[Decimal] = Field(
        None,
        ge=0,
        description="Log loss (lower is better)"
    )
    correct_winner: Optional[bool] = Field(
        None,
        description="Whether the predicted winner was correct"
    )
    top_3_accuracy: Optional[bool] = Field(
        None,
        description="Whether the actual winner was in predicted top 3"
    )


class PredictionAccuracyResponse(PredictionAccuracyBase, TimestampMixin):
    """Schema for prediction accuracy response."""

    accuracy_id: int = Field(..., description="Unique accuracy record identifier")
    race: Optional['RaceBasic'] = Field(None, description="Race information")


class ModelPerformanceMetrics(BaseSchema):
    """Schema for overall model performance metrics."""

    model_version: str = Field(..., description="Model version")
    evaluation_period_start: datetime = Field(..., description="Start of evaluation period")
    evaluation_period_end: datetime = Field(..., description="End of evaluation period")
    total_races_evaluated: int = Field(..., ge=0, description="Number of races evaluated")

    # Accuracy metrics
    average_brier_score: Optional[float] = Field(None, description="Average Brier score")
    average_log_loss: Optional[float] = Field(None, description="Average log loss")
    winner_prediction_accuracy: Optional[float] = Field(None, ge=0, le=1, description="Percentage of correct winner predictions")
    top_3_prediction_accuracy: Optional[float] = Field(None, ge=0, le=1, description="Percentage of winners in predicted top 3")

    # Calibration metrics
    calibration_error: Optional[float] = Field(None, description="Calibration error")
    reliability_score: Optional[float] = Field(None, ge=0, le=1, description="Model reliability score")

    # Additional metrics
    prediction_spread: Optional[float] = Field(None, description="Average spread of predictions")
    confidence_correlation: Optional[float] = Field(None, ge=-1, le=1, description="Correlation between confidence and accuracy")


class BatchPredictionRequest(BaseSchema):
    """Schema for batch prediction requests."""

    race_ids: List[int] = Field(..., min_items=1, description="List of race IDs to generate predictions for")
    model_version: Optional[str] = Field(None, description="Specific model version to use")
    include_confidence: bool = Field(False, description="Whether to include confidence intervals")
    include_feature_importance: bool = Field(False, description="Whether to include feature importance")

    @validator('race_ids')
    def validate_race_ids(cls, v):
        """Validate race IDs."""
        if not v:
            raise ValueError('At least one race ID is required')
        if len(set(v)) != len(v):
            raise ValueError('Race IDs must be unique')
        return v


class BatchPredictionResponse(BaseSchema):
    """Schema for batch prediction response."""

    request_id: str = Field(..., description="Unique request identifier")
    model_version: str = Field(..., description="Model version used")
    processed_at: datetime = Field(..., description="When predictions were processed")
    total_races: int = Field(..., description="Number of races processed")
    total_predictions: int = Field(..., description="Total number of predictions generated")

    predictions_by_race: Dict[int, RacePredictionsSummary] = Field(..., description="Predictions grouped by race")
    errors: List[str] = Field([], description="Any errors encountered during processing")


class PredictionListResponse(PaginatedResponse):
    """Paginated prediction list response."""

    data: List[PredictionResponse] = Field(..., description="List of predictions")


# Import after definitions to avoid circular imports
try:
    from .race import RaceBasic
    from .driver import DriverBasic
    from .team import TeamBasic
    PredictionResponse.model_rebuild()
    PredictionWithDetails.model_rebuild()
    PredictionAccuracyResponse.model_rebuild()
except ImportError:
    pass