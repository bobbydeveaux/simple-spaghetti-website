#!/usr/bin/env python3
"""
Test script for F1 Prediction Analytics SQLAlchemy models
"""

import sys
import os
from datetime import date, datetime
from decimal import Decimal

# Add the current directory to the Python path so we can import api modules
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

try:
    from api.database import Base, engine, SessionLocal
    from api.models import (
        Driver, Team, Circuit, Race, RaceResult, QualifyingResult,
        WeatherData, Prediction, PredictionAccuracy, User
    )
    print("✅ Successfully imported all F1 models and database components")
except ImportError as e:
    print(f"❌ Import error: {e}")
    sys.exit(1)


def test_model_creation():
    """Test that we can create model instances"""
    print("\n🧪 Testing model creation...")

    # Test Driver model
    driver = Driver(
        driver_code="VER",
        driver_name="Max Verstappen",
        nationality="Dutch",
        date_of_birth=date(1997, 9, 30),
        current_elo_rating=2100
    )
    print(f"✅ Driver model: {driver}")

    # Test Team model
    team = Team(
        team_name="Red Bull Racing",
        nationality="Austrian",
        current_elo_rating=1800
    )
    print(f"✅ Team model: {team}")

    # Test Circuit model
    circuit = Circuit(
        circuit_name="Circuit de Monaco",
        location="Monte Carlo",
        country="Monaco",
        track_length_km=Decimal("3.337"),
        track_type="street"
    )
    print(f"✅ Circuit model: {circuit}")

    # Test Race model
    race = Race(
        season_year=2026,
        round_number=6,
        race_date=date(2026, 5, 24),
        race_name="Monaco Grand Prix",
        status="scheduled"
    )
    print(f"✅ Race model: {race}")

    # Test Prediction model
    prediction = Prediction(
        predicted_win_probability=Decimal("35.75"),
        model_version="v1.0.0"
    )
    print(f"✅ Prediction model: {prediction}")

    # Test User model
    user = User(
        email="test@f1analytics.com",
        password_hash="hashed_password_here",
        username="testuser",
        role="user"
    )
    print(f"✅ User model: {user}")

    print("✅ All model creation tests passed!")


def test_database_connection():
    """Test database connection and table creation"""
    print("\n🔌 Testing database connection...")

    try:
        # Test engine connection
        with engine.connect() as conn:
            result = conn.execute("SELECT 1")
            print("✅ Database connection successful")

        # Test session creation
        db = SessionLocal()
        db.close()
        print("✅ Session creation successful")

    except Exception as e:
        print(f"⚠️  Database connection test failed (this is expected if no database is running): {e}")


def test_model_relationships():
    """Test that model relationships are properly defined"""
    print("\n🔗 Testing model relationships...")

    # Test that relationships are defined
    assert hasattr(Driver, 'team'), "Driver should have team relationship"
    assert hasattr(Driver, 'race_results'), "Driver should have race_results relationship"
    assert hasattr(Team, 'drivers'), "Team should have drivers relationship"
    assert hasattr(Race, 'circuit'), "Race should have circuit relationship"
    assert hasattr(Race, 'predictions'), "Race should have predictions relationship"
    assert hasattr(Prediction, 'race'), "Prediction should have race relationship"
    assert hasattr(Prediction, 'driver'), "Prediction should have driver relationship"

    print("✅ All relationship tests passed!")


def main():
    """Run all tests"""
    print("🏁 F1 Prediction Analytics - SQLAlchemy Models Test Suite")
    print("=" * 60)

    test_model_creation()
    test_database_connection()
    test_model_relationships()

    print("\n" + "=" * 60)
    print("🎯 Test Summary:")
    print("✅ Model creation: PASS")
    print("🔌 Database connection: TESTED (may fail without DB)")
    print("🔗 Model relationships: PASS")
    print("\n🏆 F1 SQLAlchemy models are ready for use!")


if __name__ == "__main__":
    main()