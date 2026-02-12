"""
Unit tests for F1 Analytics database models.

Tests model creation, relationships, validation, and properties
for all SQLAlchemy models in the F1 analytics system.
"""

import pytest
from datetime import date, datetime, timedelta
from decimal import Decimal

from app.models import (
    Driver, Team, Circuit, Race, RaceResult, QualifyingResult,
    WeatherData, Prediction, PredictionAccuracy, User
)


class TestTeam:
    """Test cases for Team model."""

    def test_team_creation(self, db_session):
        """Test creating a team with basic attributes."""
        team = Team(
            team_name="Red Bull Racing",
            nationality="Austria",
            current_elo_rating=1800
        )
        db_session.add(team)
        db_session.commit()

        assert team.team_id is not None
        assert team.team_name == "Red Bull Racing"
        assert team.nationality == "Austria"
        assert team.current_elo_rating == 1800
        assert team.created_at is not None

    def test_team_string_representation(self, db_session):
        """Test team string representation."""
        team = Team(team_name="Mercedes")
        db_session.add(team)
        db_session.commit()

        assert str(team) == "Mercedes"
        assert "Mercedes" in repr(team)


class TestDriver:
    """Test cases for Driver model."""

    def test_driver_creation(self, db_session):
        """Test creating a driver with all attributes."""
        # Create team first
        team = Team(team_name="Red Bull Racing")
        db_session.add(team)
        db_session.commit()

        driver = Driver(
            driver_code="VER",
            driver_name="Max Verstappen",
            nationality="Dutch",
            date_of_birth=date(1997, 9, 30),
            current_team_id=team.team_id,
            current_elo_rating=2100
        )
        db_session.add(driver)
        db_session.commit()

        assert driver.driver_id is not None
        assert driver.driver_code == "VER"
        assert driver.driver_name == "Max Verstappen"
        assert driver.nationality == "Dutch"
        assert driver.current_elo_rating == 2100
        assert driver.current_team_id == team.team_id

    def test_driver_team_relationship(self, db_session):
        """Test driver-team relationship."""
        team = Team(team_name="Red Bull Racing")
        driver = Driver(driver_code="VER", driver_name="Max Verstappen")
        driver.team = team

        db_session.add(driver)
        db_session.commit()

        assert driver.team.team_name == "Red Bull Racing"
        assert driver in team.drivers

    def test_driver_string_representation(self, db_session):
        """Test driver string representation."""
        driver = Driver(driver_code="VER", driver_name="Max Verstappen")
        db_session.add(driver)
        db_session.commit()

        assert str(driver) == "Max Verstappen (VER)"


class TestCircuit:
    """Test cases for Circuit model."""

    def test_circuit_creation(self, db_session):
        """Test creating a circuit with all attributes."""
        circuit = Circuit(
            circuit_name="Circuit de Monaco",
            location="Monte Carlo",
            country="Monaco",
            track_length_km=Decimal("3.337"),
            track_type="street"
        )
        db_session.add(circuit)
        db_session.commit()

        assert circuit.circuit_id is not None
        assert circuit.circuit_name == "Circuit de Monaco"
        assert circuit.location == "Monte Carlo"
        assert circuit.country == "Monaco"
        assert circuit.track_length_km == Decimal("3.337")
        assert circuit.track_type == "street"

    def test_circuit_full_name_property(self, db_session):
        """Test circuit full_name property."""
        circuit = Circuit(
            circuit_name="Silverstone Circuit",
            location="Silverstone",
            country="United Kingdom"
        )
        db_session.add(circuit)
        db_session.commit()

        expected = "Silverstone Circuit, Silverstone, United Kingdom"
        assert circuit.full_name == expected


class TestRace:
    """Test cases for Race model."""

    def test_race_creation(self, db_session):
        """Test creating a race with all attributes."""
        circuit = Circuit(circuit_name="Silverstone Circuit")
        db_session.add(circuit)
        db_session.commit()

        race = Race(
            season_year=2024,
            round_number=10,
            circuit_id=circuit.circuit_id,
            race_date=date(2024, 7, 14),
            race_name="British Grand Prix",
            status="completed"
        )
        db_session.add(race)
        db_session.commit()

        assert race.race_id is not None
        assert race.season_year == 2024
        assert race.round_number == 10
        assert race.race_name == "British Grand Prix"
        assert race.status == "completed"

    def test_race_status_properties(self, db_session):
        """Test race status boolean properties."""
        circuit = Circuit(circuit_name="Test Circuit")
        db_session.add(circuit)
        db_session.commit()

        scheduled_race = Race(
            season_year=2024,
            round_number=1,
            circuit_id=circuit.circuit_id,
            race_date=date(2024, 3, 10),
            race_name="Test GP",
            status="scheduled"
        )

        completed_race = Race(
            season_year=2024,
            round_number=2,
            circuit_id=circuit.circuit_id,
            race_date=date(2024, 3, 17),
            race_name="Test GP 2",
            status="completed"
        )

        assert scheduled_race.is_scheduled is True
        assert scheduled_race.is_completed is False
        assert completed_race.is_scheduled is False
        assert completed_race.is_completed is True

    def test_race_season_round_key_property(self, db_session):
        """Test race season_round_key property."""
        circuit = Circuit(circuit_name="Test Circuit")
        db_session.add(circuit)
        db_session.commit()

        race = Race(
            season_year=2024,
            round_number=5,
            circuit_id=circuit.circuit_id,
            race_date=date(2024, 5, 10),
            race_name="Test GP"
        )
        db_session.add(race)
        db_session.commit()

        assert race.season_round_key == "2024-R05"


class TestRaceResult:
    """Test cases for RaceResult model."""

    def test_race_result_creation(self, db_session):
        """Test creating a race result with all attributes."""
        # Setup dependencies
        team = Team(team_name="Red Bull Racing")
        circuit = Circuit(circuit_name="Silverstone Circuit")
        driver = Driver(driver_code="VER", driver_name="Max Verstappen")
        race = Race(
            season_year=2024, round_number=1, race_date=date(2024, 3, 10),
            race_name="Test GP", circuit=circuit
        )

        db_session.add_all([team, circuit, driver, race])
        db_session.commit()

        result = RaceResult(
            race_id=race.race_id,
            driver_id=driver.driver_id,
            team_id=team.team_id,
            grid_position=2,
            final_position=1,
            points=Decimal("25.0"),
            status="finished"
        )
        db_session.add(result)
        db_session.commit()

        assert result.result_id is not None
        assert result.grid_position == 2
        assert result.final_position == 1
        assert result.points == Decimal("25.0")
        assert result.status == "finished"

    def test_race_result_properties(self, db_session):
        """Test race result boolean properties."""
        # Setup minimal dependencies
        team = Team(team_name="Test Team")
        circuit = Circuit(circuit_name="Test Circuit")
        driver = Driver(driver_code="TST", driver_name="Test Driver")
        race = Race(
            season_year=2024, round_number=1, race_date=date(2024, 3, 10),
            race_name="Test GP", circuit=circuit
        )

        db_session.add_all([team, circuit, driver, race])
        db_session.commit()

        # Test winner result
        winner_result = RaceResult(
            race_id=race.race_id,
            driver_id=driver.driver_id,
            team_id=team.team_id,
            final_position=1,
            points=Decimal("25.0"),
            status="finished"
        )

        assert winner_result.race_winner is True
        assert winner_result.podium_finish is True
        assert winner_result.points_scoring_position is True
        assert winner_result.finished_race is True

        # Test DNF result
        dnf_result = RaceResult(
            race_id=race.race_id,
            driver_id=driver.driver_id,
            team_id=team.team_id,
            final_position=None,
            points=Decimal("0.0"),
            status="dnf"
        )

        assert dnf_result.race_winner is False
        assert dnf_result.finished_race is False


class TestUser:
    """Test cases for User model."""

    def test_user_creation(self, db_session):
        """Test creating a user with basic attributes."""
        user = User(
            email="test@example.com",
            role="user"
        )
        user.set_password("SecurePassword123")
        db_session.add(user)
        db_session.commit()

        assert user.user_id is not None
        assert user.email == "test@example.com"
        assert user.role == "user"
        assert user.password_hash is not None
        assert user.password_hash != "SecurePassword123"  # Should be hashed

    def test_user_password_hashing(self, db_session):
        """Test password hashing and verification."""
        user = User(email="test@example.com")
        user.set_password("MySecretPassword")

        # Password should be hashed
        assert user.password_hash != "MySecretPassword"

        # Should verify correct password
        assert user.check_password("MySecretPassword") is True

        # Should reject incorrect password
        assert user.check_password("WrongPassword") is False

    def test_user_email_validation(self, db_session):
        """Test email validation."""
        with pytest.raises(ValueError, match="Invalid email format"):
            user = User(email="invalid-email")

    def test_user_role_validation(self, db_session):
        """Test role validation."""
        with pytest.raises(ValueError, match="Role must be one of"):
            user = User(email="test@example.com", role="invalid_role")

    def test_user_properties(self, db_session):
        """Test user properties."""
        admin_user = User(email="admin@example.com", role="admin")
        regular_user = User(email="user@example.com", role="user")

        assert admin_user.is_admin is True
        assert regular_user.is_admin is False

        assert admin_user.display_name == "admin"
        assert regular_user.display_name == "user"

        assert admin_user.is_new_user is True  # No last_login set
        admin_user.update_last_login()
        assert admin_user.is_new_user is False


class TestPrediction:
    """Test cases for Prediction model."""

    def test_prediction_creation(self, db_session):
        """Test creating a prediction with all attributes."""
        # Setup dependencies
        circuit = Circuit(circuit_name="Test Circuit")
        driver = Driver(driver_code="VER", driver_name="Max Verstappen")
        race = Race(
            season_year=2024, round_number=1, race_date=date(2024, 3, 10),
            race_name="Test GP", circuit=circuit
        )

        db_session.add_all([circuit, driver, race])
        db_session.commit()

        prediction = Prediction(
            race_id=race.race_id,
            driver_id=driver.driver_id,
            predicted_win_probability=Decimal("35.50"),
            model_version="v1.0.0"
        )
        db_session.add(prediction)
        db_session.commit()

        assert prediction.prediction_id is not None
        assert prediction.predicted_win_probability == Decimal("35.50")
        assert prediction.model_version == "v1.0.0"
        assert prediction.prediction_timestamp is not None

    def test_prediction_properties(self, db_session):
        """Test prediction probability classification properties."""
        circuit = Circuit(circuit_name="Test Circuit")
        driver = Driver(driver_code="VER", driver_name="Max Verstappen")
        race = Race(
            season_year=2024, round_number=1, race_date=date(2024, 3, 10),
            race_name="Test GP", circuit=circuit
        )

        db_session.add_all([circuit, driver, race])
        db_session.commit()

        # Test favorite prediction (>40%)
        favorite = Prediction(
            race_id=race.race_id,
            driver_id=driver.driver_id,
            predicted_win_probability=Decimal("45.0"),
            model_version="v1.0.0"
        )

        assert favorite.favorite is True
        assert favorite.high_probability is True
        assert favorite.longshot is False

        # Test longshot prediction (<5%)
        longshot = Prediction(
            race_id=race.race_id,
            driver_id=driver.driver_id,
            predicted_win_probability=Decimal("2.5"),
            model_version="v1.0.0"
        )

        assert longshot.favorite is False
        assert longshot.high_probability is False
        assert longshot.longshot is True

    def test_prediction_probability_decimal(self, db_session):
        """Test probability_decimal property conversion."""
        circuit = Circuit(circuit_name="Test Circuit")
        driver = Driver(driver_code="VER", driver_name="Max Verstappen")
        race = Race(
            season_year=2024, round_number=1, race_date=date(2024, 3, 10),
            race_name="Test GP", circuit=circuit
        )

        db_session.add_all([circuit, driver, race])
        db_session.commit()

        prediction = Prediction(
            race_id=race.race_id,
            driver_id=driver.driver_id,
            predicted_win_probability=Decimal("25.0"),
            model_version="v1.0.0"
        )

        assert prediction.probability_decimal == 0.25


class TestPredictionAccuracy:
    """Test cases for PredictionAccuracy model."""

    def test_prediction_accuracy_creation(self, db_session):
        """Test creating prediction accuracy with all metrics."""
        circuit = Circuit(circuit_name="Test Circuit")
        race = Race(
            season_year=2024, round_number=1, race_date=date(2024, 3, 10),
            race_name="Test GP", circuit=circuit, status="completed"
        )

        db_session.add_all([circuit, race])
        db_session.commit()

        accuracy = PredictionAccuracy(
            race_id=race.race_id,
            brier_score=Decimal("0.1250"),
            log_loss=Decimal("1.8500"),
            correct_winner=True,
            top_3_accuracy=True
        )
        db_session.add(accuracy)
        db_session.commit()

        assert accuracy.accuracy_id is not None
        assert accuracy.brier_score == Decimal("0.1250")
        assert accuracy.correct_winner is True
        assert accuracy.top_3_accuracy is True

    def test_prediction_accuracy_grading(self, db_session):
        """Test prediction accuracy grading system."""
        circuit = Circuit(circuit_name="Test Circuit")
        race = Race(
            season_year=2024, round_number=1, race_date=date(2024, 3, 10),
            race_name="Test GP", circuit=circuit
        )

        db_session.add_all([circuit, race])
        db_session.commit()

        # Test A grade (excellent)
        excellent = PredictionAccuracy(
            race_id=race.race_id,
            brier_score=Decimal("0.08"),
            correct_winner=True
        )
        assert excellent.accuracy_grade == "A"
        assert excellent.excellent_prediction is True

        # Test D grade (poor)
        poor = PredictionAccuracy(
            race_id=race.race_id,
            brier_score=Decimal("0.35"),
            correct_winner=False,
            top_3_accuracy=False
        )
        assert poor.accuracy_grade == "D"
        assert poor.poor_prediction is True

    def test_brier_score_calculation(self, db_session):
        """Test Brier score calculation method."""
        # Setup test data
        circuit = Circuit(circuit_name="Test Circuit")
        driver1 = Driver(driver_code="VER", driver_name="Max Verstappen")
        driver2 = Driver(driver_code="HAM", driver_name="Lewis Hamilton")
        race = Race(
            season_year=2024, round_number=1, race_date=date(2024, 3, 10),
            race_name="Test GP", circuit=circuit
        )

        db_session.add_all([circuit, driver1, driver2, race])
        db_session.commit()

        # Create predictions
        predictions = [
            Prediction(
                race_id=race.race_id,
                driver_id=driver1.driver_id,
                predicted_win_probability=Decimal("70.0"),  # 0.7 probability
                model_version="v1.0.0"
            ),
            Prediction(
                race_id=race.race_id,
                driver_id=driver2.driver_id,
                predicted_win_probability=Decimal("30.0"),  # 0.3 probability
                model_version="v1.0.0"
            )
        ]

        # Test Brier score calculation (driver1 wins)
        actual_winner_id = driver1.driver_id
        brier_score = PredictionAccuracy.calculate_brier_score(predictions, actual_winner_id)

        # Expected: ((0.7 - 1)^2 + (0.3 - 0)^2) / 2 = (0.09 + 0.09) / 2 = 0.09
        expected_brier = 0.09
        assert abs(brier_score - expected_brier) < 0.001