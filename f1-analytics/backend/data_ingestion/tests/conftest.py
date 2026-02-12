"""
Pytest configuration for weather ingestion tests.
"""

import pytest
import sys
from pathlib import Path

# Add the parent directories to Python path for imports
test_dir = Path(__file__).parent
backend_dir = test_dir.parent.parent
project_root = backend_dir.parent.parent.parent

sys.path.insert(0, str(backend_dir))
sys.path.insert(0, str(project_root))

# Configure test environment
pytest_plugins = []


@pytest.fixture(scope="session")
def test_config():
    """Provide test configuration."""
    return {
        'database_url': 'sqlite:///:memory:',
        'weather_api_key': 'test_key_12345',
        'weather_base_url': 'https://api.openweathermap.org/data/2.5'
    }


@pytest.fixture(autouse=True)
def setup_test_environment(monkeypatch):
    """Set up test environment variables."""
    monkeypatch.setenv("F1_WEATHER_API_KEY", "test_key_12345")
    monkeypatch.setenv("F1_WEATHER_BASE_URL", "https://api.openweathermap.org/data/2.5")