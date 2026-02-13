"""
Comprehensive tests for the data transformation and validation layer.

This test module validates all components of the data validation and transformation
system including schemas, services, validators, and transformers.
"""

import pytest
from datetime import date, datetime, timedelta
from decimal import Decimal
from unittest.mock import Mock, patch
from sqlalchemy.orm import Session

from app.schemas.base import BaseSchema, PaginationParams
from app.schemas.driver import DriverCreate, DriverUpdate, DriverResponse
from app.schemas.race import RaceCreate, RaceResponse
from app.schemas.prediction import PredictionCreate, RacePredictionsSummary

from app.services.base import DataValidator, DataTransformer, ValidationError
from app.services.driver_service import DriverService
from app.services.race_service import RaceService
from app.services.prediction_service import PredictionService

from app.utils.validators import F1DataValidator, validate_race_not_completed
from app.utils.transformers import F1DataTransformer, TransformationConfig

from app.models.f1_models import Driver, Race, Team, RaceResult, Prediction, RaceStatus


class TestPydanticSchemas:
    """Test Pydantic schema validation."""

    def test_driver_create_validation(self):
        """Test driver creation schema validation."""
        # Valid data
        valid_data = {
            "driver_code": "VER",
            "driver_name": "Max Verstappen",
            "nationality": "Dutch",
            "date_of_birth": "1997-09-30"
        }
        driver = DriverCreate(**valid_data)
        assert driver.driver_code == "VER"
        assert driver.driver_name == "Max Verstappen"

    def test_driver_create_invalid_code(self):
        """Test driver code validation."""
        invalid_data = {
            "driver_code": "INVALID",  # Too long
            "driver_name": "Test Driver"
        }
        with pytest.raises(ValueError):
            DriverCreate(**invalid_data)

    def test_pagination_params(self):
        """Test pagination parameter validation."""
        # Valid pagination
        params = PaginationParams(page=1, page_size=20)
        assert params.offset == 0

        params = PaginationParams(page=2, page_size=10)
        assert params.offset == 10

        # Invalid pagination
        with pytest.raises(ValueError):
            PaginationParams(page=0, page_size=20)  # Page must be >= 1

        with pytest.raises(ValueError):
            PaginationParams(page=1, page_size=101)  # Page size too large

    def test_race_create_validation(self):
        """Test race creation schema validation."""
        valid_data = {
            "season_year": 2024,
            "round_number": 1,
            "race_name": "Bahrain Grand Prix",
            "race_date": "2024-03-01",
            "circuit_id": 1
        }
        race = RaceCreate(**valid_data)
        assert race.season_year == 2024
        assert race.round_number == 1

    def test_prediction_create_validation(self):
        """Test prediction creation schema validation."""
        valid_data = {
            "race_id": 1,
            "driver_id": 1,
            "predicted_win_probability": Decimal("25.5"),
            "model_version": "v1.0"
        }
        prediction = PredictionCreate(**valid_data)
        assert float(prediction.predicted_win_probability) == 25.5

        # Test invalid probability
        invalid_data = valid_data.copy()
        invalid_data["predicted_win_probability"] = Decimal("150.0")  # > 100
        with pytest.raises(ValueError):
            PredictionCreate(**invalid_data)


class TestDataValidators:
    """Test data validation utilities."""

    def test_validate_probability(self):
        """Test probability validation."""
        # Valid probabilities
        assert DataValidator.validate_probability(50.0) == 50.0
        assert DataValidator.validate_probability(0.0) == 0.0
        assert DataValidator.validate_probability(100.0) == 100.0

        # Invalid probabilities
        with pytest.raises(ValidationError):
            DataValidator.validate_probability(-1.0)

        with pytest.raises(ValidationError):
            DataValidator.validate_probability(101.0)

        with pytest.raises(ValidationError):
            DataValidator.validate_probability("invalid")

    def test_validate_elo_rating(self):
        """Test ELO rating validation."""
        # Valid ratings
        assert DataValidator.validate_elo_rating(1500) == 1500
        assert DataValidator.validate_elo_rating(2500.0) == 2500

        # Invalid ratings
        with pytest.raises(ValidationError):
            DataValidator.validate_elo_rating(700)  # Too low

        with pytest.raises(ValidationError):
            DataValidator.validate_elo_rating(3100)  # Too high

    def test_validate_driver_code(self):
        """Test driver code validation."""
        # Valid codes
        assert DataValidator.validate_driver_code("VER") == "VER"
        assert DataValidator.validate_driver_code("ham") == "HAM"  # Should uppercase

        # Invalid codes
        with pytest.raises(ValidationError):
            DataValidator.validate_driver_code("VE")  # Too short

        with pytest.raises(ValidationError):
            DataValidator.validate_driver_code("VERY")  # Too long

        with pytest.raises(ValidationError):
            DataValidator.validate_driver_code("V3R")  # Contains number

    def test_validate_lap_time(self):
        """Test lap time validation."""
        # Valid lap times
        assert DataValidator.validate_lap_time("1:23.456") == "1:23.456"
        assert DataValidator.validate_lap_time("2:05.789") == "2:05.789"

        # Invalid lap times
        with pytest.raises(ValidationError):
            DataValidator.validate_lap_time("1:23")  # Missing milliseconds

        with pytest.raises(ValidationError):
            DataValidator.validate_lap_time("invalid")

    def test_validate_season_year(self):
        """Test season year validation."""
        current_year = datetime.now().year

        # Valid years
        assert DataValidator.validate_season_year(2024) == 2024
        assert DataValidator.validate_season_year(current_year) == current_year

        # Invalid years
        with pytest.raises(ValidationError):
            DataValidator.validate_season_year(1949)  # Too early

        with pytest.raises(ValidationError):
            DataValidator.validate_season_year(current_year + 5)  # Too far future


class TestDataTransformers:
    """Test data transformation utilities."""

    def test_normalize_driver_name(self):
        """Test driver name normalization."""
        assert DataTransformer.normalize_driver_name("max verstappen") == "Max Verstappen"
        assert DataTransformer.normalize_driver_name("LEWIS HAMILTON") == "Lewis Hamilton"
        assert DataTransformer.normalize_driver_name("  charles   leclerc  ") == "Charles Leclerc"

    def test_format_lap_time(self):
        """Test lap time formatting."""
        assert DataTransformer.format_lap_time(83.456) == "1:23.456"
        assert DataTransformer.format_lap_time(125.789) == "2:05.789"
        assert DataTransformer.format_lap_time(59.123) == "0:59.123"

    def test_parse_lap_time(self):
        """Test lap time parsing."""
        assert DataTransformer.parse_lap_time("1:23.456") == 83.456
        assert DataTransformer.parse_lap_time("2:05.789") == 125.789
        assert DataTransformer.parse_lap_time("0:59.123") == 59.123
        assert DataTransformer.parse_lap_time("invalid") is None

    def test_calculate_points_from_position(self):
        """Test points calculation."""
        assert DataTransformer.calculate_points_from_position(1) == 25.0
        assert DataTransformer.calculate_points_from_position(2) == 18.0
        assert DataTransformer.calculate_points_from_position(3) == 15.0
        assert DataTransformer.calculate_points_from_position(10) == 1.0
        assert DataTransformer.calculate_points_from_position(11) == 0.0

    def test_safe_divide(self):
        """Test safe division."""
        assert DataTransformer.safe_divide(10, 2) == 5.0
        assert DataTransformer.safe_divide(10, 0) == 0.0  # Default
        assert DataTransformer.safe_divide(10, 0, default=999) == 999  # Custom default


class TestF1DataValidator:
    """Test F1-specific validation rules."""

    def test_validate_race_season_consistency(self):
        """Test race season validation."""
        mock_db = Mock()

        # Valid data
        valid_data = {
            "race_date": date(2024, 3, 1),
            "season_year": 2024
        }
        # Should not raise
        F1DataValidator.validate_race_season_consistency(mock_db, valid_data)

        # Invalid data
        invalid_data = {
            "race_date": date(2024, 3, 1),
            "season_year": 2023  # Wrong year
        }
        with pytest.raises(ValidationError):
            F1DataValidator.validate_race_season_consistency(mock_db, invalid_data)

    def test_validate_elo_rating_bounds(self):
        """Test ELO rating bounds validation."""
        # Valid ratings
        assert F1DataValidator.validate_elo_rating_bounds(1500) == 1500
        assert F1DataValidator.validate_elo_rating_bounds(2000.5) == 2000

        # Invalid ratings
        with pytest.raises(ValidationError):
            F1DataValidator.validate_elo_rating_bounds(700)

        with pytest.raises(ValidationError):
            F1DataValidator.validate_elo_rating_bounds(3100)

    def test_validate_lap_time_format(self):
        """Test lap time format validation and normalization."""
        # Valid formats
        assert F1DataValidator.validate_lap_time_format("1:23.456") == "1:23.456"
        assert F1DataValidator.validate_lap_time_format("1:23.45") == "1:23.450"  # Normalize
        assert F1DataValidator.validate_lap_time_format("59.123") == "0:59.123"  # Convert format

        # Invalid formats
        with pytest.raises(ValidationError):
            F1DataValidator.validate_lap_time_format("invalid")

        with pytest.raises(ValidationError):
            F1DataValidator.validate_lap_time_format(123)  # Not string


class TestF1DataTransformer:
    """Test F1-specific data transformer."""

    def setup_method(self):
        """Set up test fixtures."""
        self.transformer = F1DataTransformer()
        self.config = TransformationConfig(
            include_metadata=True,
            include_relationships=True,
            include_calculated_fields=True
        )
        self.transformer_with_config = F1DataTransformer(self.config)

    def test_transform_driver_for_api(self):
        """Test driver transformation for API response."""
        # Mock driver
        driver = Mock(spec=Driver)
        driver.driver_id = 1
        driver.driver_code = "VER"
        driver.driver_name = "Max Verstappen"
        driver.nationality = "Dutch"
        driver.date_of_birth = date(1997, 9, 30)
        driver.current_team_id = 1
        driver.current_elo_rating = 2100
        driver.created_at = datetime(2023, 1, 1)
        driver.updated_at = datetime(2023, 12, 1)
        driver.current_team = None

        result = self.transformer.transform_driver_for_api(driver)

        assert result["driver_id"] == 1
        assert result["driver_code"] == "VER"
        assert result["driver_name"] == "Max Verstappen"
        assert result["current_elo_rating"] == 2100
        assert "age" in result  # Calculated field
        assert "elo_category" in result  # Calculated field

    def test_transform_prediction_summary(self):
        """Test prediction summary transformation."""
        # Mock race
        race = Mock(spec=Race)
        race.race_id = 1
        race.race_name = "Monaco Grand Prix"
        race.race_date = date(2024, 5, 26)

        # Mock predictions
        prediction1 = Mock(spec=Prediction)
        prediction1.driver_id = 1
        prediction1.predicted_win_probability = Decimal("35.0")
        prediction1.model_version = "v1.0"
        prediction1.prediction_timestamp = datetime.now()

        prediction2 = Mock(spec=Prediction)
        prediction2.driver_id = 2
        prediction2.predicted_win_probability = Decimal("25.0")
        prediction2.model_version = "v1.0"
        prediction2.prediction_timestamp = datetime.now()

        predictions = [prediction1, prediction2]

        result = self.transformer.transform_prediction_summary(predictions, race)

        assert result["race_id"] == 1
        assert result["race_name"] == "Monaco Grand Prix"
        assert result["total_drivers"] == 2
        assert "statistics" in result
        assert "favorite" in result
        assert result["favorite"]["driver_id"] == 1  # Highest probability

    def test_calculate_prediction_entropy(self):
        """Test prediction entropy calculation."""
        # Mock predictions with equal probabilities (high entropy)
        predictions = []
        for i in range(5):
            pred = Mock(spec=Prediction)
            pred.predicted_win_probability = Decimal("20.0")  # Equal probabilities
            predictions.append(pred)

        entropy = self.transformer._calculate_prediction_entropy(predictions)
        assert entropy > 2.0  # Should be high for equal probabilities

        # Mock predictions with unequal probabilities (lower entropy)
        predictions[0].predicted_win_probability = Decimal("80.0")
        for i in range(1, 5):
            predictions[i].predicted_win_probability = Decimal("5.0")

        entropy = self.transformer._calculate_prediction_entropy(predictions)
        assert entropy < 2.0  # Should be lower for skewed probabilities

    def test_calculate_competitiveness_score(self):
        """Test competitiveness score calculation."""
        # High competitiveness (small spread)
        predictions = []
        for i in range(5):
            pred = Mock(spec=Prediction)
            pred.predicted_win_probability = Decimal(str(20.0 + i))  # 20, 21, 22, 23, 24
            predictions.append(pred)

        score = self.transformer._calculate_competitiveness_score(predictions)
        assert score > 90  # Should be highly competitive

        # Low competitiveness (large spread)
        predictions[0].predicted_win_probability = Decimal("50.0")
        predictions[1].predicted_win_probability = Decimal("5.0")

        score = self.transformer._calculate_competitiveness_score(predictions)
        assert score < 90  # Should be less competitive


class TestServiceValidation:
    """Test service layer validation."""

    def test_driver_service_create_validation(self):
        """Test driver service validation."""
        mock_db = Mock(spec=Session)

        # Mock no existing driver
        mock_db.query.return_value.filter.return_value.first.return_value = None

        service = DriverService()

        driver_data = DriverCreate(
            driver_code="VER",
            driver_name="Max Verstappen",
            current_elo_rating=2100
        )

        # This would normally create a driver, but we'll test the validation part
        # by mocking the database interactions
        with patch.object(service, 'create') as mock_create:
            mock_create.return_value = Mock()
            result = service.create_driver(mock_db, driver_data)
            mock_create.assert_called_once()

    def test_prediction_service_validation(self):
        """Test prediction service validation."""
        mock_db = Mock(spec=Session)
        service = PredictionService()

        # Mock race exists and is not completed
        mock_race = Mock(spec=Race)
        mock_race.status = RaceStatus.SCHEDULED
        mock_db.query.return_value.filter.return_value.first.return_value = mock_race

        # Mock driver exists
        mock_driver = Mock(spec=Driver)

        # Mock no existing prediction
        def query_side_effect(model):
            if model == Race:
                return mock_db.query.return_value
            elif model == Driver:
                mock_query = Mock()
                mock_query.filter.return_value.first.return_value = mock_driver
                return mock_query
            elif model == Prediction:
                mock_query = Mock()
                mock_query.filter.return_value.first.return_value = None
                return mock_query
            return Mock()

        mock_db.query.side_effect = query_side_effect

        prediction_data = PredictionCreate(
            race_id=1,
            driver_id=1,
            predicted_win_probability=Decimal("25.0"),
            model_version="v1.0"
        )

        with patch.object(service, 'create') as mock_create:
            mock_create.return_value = Mock()
            result = service.create_prediction(mock_db, prediction_data)
            mock_create.assert_called_once()


class TestBusinessRuleValidators:
    """Test business rule validators."""

    def test_validate_race_not_completed(self):
        """Test race completion validation."""
        mock_db = Mock(spec=Session)

        # Mock completed race
        mock_race = Mock(spec=Race)
        mock_race.status = RaceStatus.COMPLETED
        mock_db.query.return_value.filter.return_value.first.return_value = mock_race

        with pytest.raises(ValidationError, match="Cannot modify data for completed races"):
            validate_race_not_completed(mock_db, 1)

        # Mock scheduled race (should pass)
        mock_race.status = RaceStatus.SCHEDULED
        # Should not raise
        validate_race_not_completed(mock_db, 1)

    def test_validate_race_not_found(self):
        """Test validation when race doesn't exist."""
        mock_db = Mock(spec=Session)
        mock_db.query.return_value.filter.return_value.first.return_value = None

        with pytest.raises(ValidationError, match="Race with ID 1 not found"):
            validate_race_not_completed(mock_db, 1)


class TestIntegrationScenarios:
    """Test integration scenarios combining multiple components."""

    def test_complete_prediction_workflow(self):
        """Test complete prediction creation and validation workflow."""
        # This would be a more complex integration test combining
        # schema validation, service logic, and database operations
        pass

    def test_race_result_processing_workflow(self):
        """Test complete race result processing with validation."""
        # This would test the full workflow of race result processing
        # including validation, transformation, and storage
        pass

    def test_error_handling_chain(self):
        """Test error propagation through the validation chain."""
        # This would test how errors are handled and propagated
        # from validators through services to API responses
        pass


if __name__ == "__main__":
    pytest.main([__file__, "-v"])