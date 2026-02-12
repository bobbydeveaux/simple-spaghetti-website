#!/usr/bin/env python3
"""
Verify F1 Analytics database schema.

This script validates that all models can be imported and their
relationships are properly defined.
"""
import sys
from pathlib import Path

# Add app directory to path
sys.path.append(str(Path(__file__).parent / "app"))

def test_model_imports():
    """Test that all models can be imported successfully."""
    try:
        from app.models import (
            Driver, Team, Circuit, Race, RaceResult,
            QualifyingResult, WeatherData, Prediction,
            PredictionAccuracy, User
        )
        print("✓ All models imported successfully")
        return True
    except ImportError as e:
        print(f"✗ Model import error: {e}")
        return False

def test_model_relationships():
    """Test that model relationships are properly defined."""
    try:
        from app.models import Driver, Team, Race

        # Test that Driver has team relationship
        driver = Driver()
        assert hasattr(driver, 'team')
        assert hasattr(driver, 'race_results')
        assert hasattr(driver, 'qualifying_results')
        assert hasattr(driver, 'predictions')

        # Test that Team has drivers relationship
        team = Team()
        assert hasattr(team, 'drivers')
        assert hasattr(team, 'race_results')

        # Test that Race has multiple relationships
        race = Race()
        assert hasattr(race, 'circuit')
        assert hasattr(race, 'race_results')
        assert hasattr(race, 'qualifying_results')
        assert hasattr(race, 'weather_data')
        assert hasattr(race, 'predictions')
        assert hasattr(race, 'prediction_accuracy')

        print("✓ Model relationships defined correctly")
        return True
    except (ImportError, AssertionError) as e:
        print(f"✗ Model relationship error: {e}")
        return False

def test_database_config():
    """Test that database configuration loads properly."""
    try:
        from app.config import db_config, app_config

        # Test database URL generation
        db_url = db_config.database_url
        assert db_url.startswith("postgresql://")

        # Test async database URL
        async_url = db_config.async_database_url
        assert async_url.startswith("postgresql+asyncpg://")

        # Test app configuration
        assert app_config.API_V1_PREFIX == "/api/v1"
        assert isinstance(app_config.CORS_ORIGINS, list)

        print("✓ Database and app configuration loaded successfully")
        print(f"  Database URL: {db_url}")
        print(f"  Environment: {app_config.ENVIRONMENT}")
        return True
    except (ImportError, AssertionError) as e:
        print(f"✗ Configuration error: {e}")
        return False

def test_migration_script():
    """Test that migration script exists and has required functions."""
    try:
        migration_file = Path(__file__).parent / "alembic" / "versions" / "001_initial_schema.py"

        if not migration_file.exists():
            print("✗ Migration script not found")
            return False

        # Read migration file content
        content = migration_file.read_text()

        # Check for required functions
        required_elements = [
            "def upgrade()",
            "def downgrade()",
            "revision = '001'",
            "create_table",
            "teams",
            "drivers",
            "races",
        ]

        for element in required_elements:
            if element not in content:
                print(f"✗ Migration script missing required element: {element}")
                return False

        print("✓ Migration script structure is valid")
        return True
    except Exception as e:
        print(f"✗ Migration script validation error: {e}")
        return False

def main():
    """Run all schema verification tests."""
    print("F1 Analytics Schema Verification")
    print("=" * 40)

    tests = [
        test_model_imports,
        test_model_relationships,
        test_database_config,
        test_migration_script,
    ]

    passed = 0
    total = len(tests)

    for test in tests:
        try:
            if test():
                passed += 1
        except Exception as e:
            print(f"✗ Test {test.__name__} failed with exception: {e}")

    print("\n" + "=" * 40)
    print(f"Tests passed: {passed}/{total}")

    if passed == total:
        print("🎉 All schema verification tests passed!")
        return 0
    else:
        print("❌ Some tests failed. Please check the schema implementation.")
        return 1

if __name__ == "__main__":
    sys.exit(main())