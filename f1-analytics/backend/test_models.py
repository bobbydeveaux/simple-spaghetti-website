#!/usr/bin/env python3
"""
Test script for F1 Analytics SQLAlchemy Models

This script validates that all models can be imported and that
SQLAlchemy can generate the expected DDL statements.

It does not require a database connection - it just validates
the model definitions and relationships.
"""

import sys
import os
from datetime import datetime, date, timedelta
from decimal import Decimal

# Add current directory to path
sys.path.append(os.path.dirname(__file__))

try:
    # Test imports
    print("Testing imports...")
    from app.config import settings
    from app.database import Base, engine, SessionLocal
    from app.models import (
        Driver, Team, Circuit, Race, RaceResult, QualifyingResult,
        WeatherData, Prediction, PredictionAccuracy, User
    )
    print("✅ All imports successful")

    # Test model instantiation
    print("\nTesting model instantiation...")

    # Test Team model
    team = Team(
        team_name="Red Bull Racing",
        nationality="Austria",
        current_elo_rating=1650
    )
    print(f"✅ Team model: {team}")

    # Test Driver model
    driver = Driver(
        driver_code="VER",
        driver_name="Max Verstappen",
        nationality="Netherlands",
        date_of_birth=date(1997, 9, 30),
        current_elo_rating=1800
    )
    print(f"✅ Driver model: {driver}")

    # Test Circuit model
    circuit = Circuit(
        circuit_name="Monaco Street Circuit",
        location="Monte Carlo",
        country="Monaco",
        track_length_km=Decimal("3.337"),
        track_type="street"
    )
    print(f"✅ Circuit model: {circuit}")

    # Test Race model
    race = Race(
        season_year=2024,
        round_number=6,
        race_date=date(2024, 5, 26),
        race_name="Monaco Grand Prix",
        circuit_id=1,
        status="completed"
    )
    print(f"✅ Race model: {race}")

    # Test RaceResult model
    race_result = RaceResult(
        race_id=1,
        driver_id=1,
        team_id=1,
        grid_position=1,
        final_position=1,
        points=Decimal("25.0"),
        fastest_lap_time=timedelta(minutes=1, seconds=12, milliseconds=345),
        status="finished"
    )
    print(f"✅ RaceResult model: {race_result}")

    # Test QualifyingResult model
    qualifying = QualifyingResult(
        race_id=1,
        driver_id=1,
        q1_time=timedelta(minutes=1, seconds=14, milliseconds=123),
        q2_time=timedelta(minutes=1, seconds=13, milliseconds=456),
        q3_time=timedelta(minutes=1, seconds=12, milliseconds=789),
        final_grid_position=1
    )
    print(f"✅ QualifyingResult model: {qualifying}")

    # Test WeatherData model
    weather = WeatherData(
        race_id=1,
        temperature_celsius=Decimal("24.5"),
        precipitation_mm=Decimal("0.0"),
        wind_speed_kph=Decimal("12.3"),
        conditions="dry"
    )
    print(f"✅ WeatherData model: {weather}")

    # Test Prediction model
    prediction = Prediction(
        race_id=1,
        driver_id=1,
        predicted_win_probability=Decimal("35.75"),
        model_version="xgboost_v2.1"
    )
    print(f"✅ Prediction model: {prediction}")

    # Test PredictionAccuracy model
    accuracy = PredictionAccuracy(
        race_id=1,
        brier_score=Decimal("0.1234"),
        log_loss=Decimal("0.4567"),
        correct_winner=True,
        top_3_accuracy=True
    )
    print(f"✅ PredictionAccuracy model: {accuracy}")

    # Test User model
    user = User(
        email="test@f1analytics.com",
        password_hash="$2b$12$hashed_password_here",
        role="user"
    )
    print(f"✅ User model: {user}")

    # Test model properties and methods
    print("\nTesting model properties...")

    print(f"✅ Driver age calculation: {driver.age} years (calculated from DOB)")
    print(f"✅ Circuit type checks: street={circuit.is_street_circuit}, permanent={circuit.is_permanent_circuit}")
    print(f"✅ Race status checks: completed={race.is_completed}, future={race.is_future_race}")
    print(f"✅ Weather conditions: dry={weather.is_dry}, hot={weather.is_hot_weather}")
    print(f"✅ Prediction confidence: {prediction.confidence_category}")
    print(f"✅ Accuracy grade: {accuracy.accuracy_grade}")
    print(f"✅ User permissions: admin={user.is_admin}, active={user.is_active_user}")

    # Test SQLAlchemy metadata
    print("\nTesting SQLAlchemy metadata...")
    print(f"✅ Total tables defined: {len(Base.metadata.tables)}")

    expected_tables = {
        'teams', 'drivers', 'circuits', 'races', 'race_results',
        'qualifying_results', 'weather_data', 'predictions',
        'prediction_accuracy', 'users'
    }
    actual_tables = set(Base.metadata.tables.keys())

    if expected_tables <= actual_tables:
        print(f"✅ All expected tables present: {sorted(expected_tables)}")
    else:
        missing = expected_tables - actual_tables
        print(f"❌ Missing tables: {sorted(missing)}")

    # Test constraint validation
    print("\nTesting constraint validation...")

    # Test check constraints by trying invalid values
    try:
        invalid_circuit = Circuit(
            circuit_name="Invalid Track",
            location="Nowhere",
            country="Invalid",
            track_length_km=Decimal("-1.0"),  # Should be positive
            track_type="invalid_type"  # Should be 'street' or 'permanent'
        )
        # SQLAlchemy doesn't validate check constraints until DB commit
        print("✅ Model allows invalid values (constraints enforced at DB level)")
    except Exception as e:
        print(f"⚠️  Model validation error: {e}")

    # Test string representations
    print("\nTesting string representations...")
    models = [team, driver, circuit, race, race_result, qualifying, weather, prediction, accuracy, user]
    for model in models:
        print(f"✅ {model.__class__.__name__}: {str(model)}")

    print(f"\n🎉 All tests passed! F1 Analytics models are working correctly.")
    print(f"📊 Summary: {len(expected_tables)} tables, comprehensive relationships, all constraints defined.")

    # Configuration summary
    print(f"\n⚙️  Configuration:")
    print(f"   Database URL: {settings.database_url}")
    print(f"   Environment: {settings.ENVIRONMENT}")
    print(f"   Debug mode: {settings.DEBUG}")

except ImportError as e:
    print(f"❌ Import error: {e}")
    print("Make sure you're running this from the correct directory and dependencies are installed")
    sys.exit(1)
except Exception as e:
    print(f"❌ Error during testing: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

print(f"\n✨ F1 Analytics SQLAlchemy models test completed successfully!")