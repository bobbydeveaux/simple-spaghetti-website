"""
Configuration for F1 data ingestion services.

This module provides specific configuration settings for data ingestion,
including API endpoints, retry policies, and data validation rules.
"""

from typing import Dict, List, Any
from app.config import settings


class IngestionConfig:
    """Configuration settings for data ingestion services."""

    # Ergast API configuration
    ERGAST_BASE_URL = settings.external_apis.ergast_base_url
    ERGAST_TIMEOUT = settings.external_apis.ergast_timeout
    ERGAST_RETRY_ATTEMPTS = settings.external_apis.ergast_retry_attempts

    # Rate limiting and throttling
    REQUEST_DELAY = 0.1  # Delay between API requests in seconds
    BATCH_SIZE = 10      # Number of records to process in each batch
    MAX_CONCURRENT_REQUESTS = 3  # Maximum concurrent API requests

    # Data validation settings
    VALIDATE_LAP_TIMES = True
    VALIDATE_GRID_POSITIONS = True
    VALIDATE_POINTS_ALLOCATION = True

    # Retry policy for failed requests
    RETRY_BACKOFF_FACTOR = 2
    MAX_RETRY_DELAY = 60  # Maximum delay between retries (seconds)

    # Data quality thresholds
    MIN_RACE_DURATION_MINUTES = 30   # Minimum expected race duration
    MAX_RACE_DURATION_MINUTES = 300  # Maximum expected race duration
    MIN_QUALIFYING_TIME_SECONDS = 60 # Minimum reasonable qualifying time
    MAX_QUALIFYING_TIME_SECONDS = 150 # Maximum reasonable qualifying time

    @classmethod
    def get_api_headers(cls) -> Dict[str, str]:
        """Get standard headers for API requests."""
        return {
            "User-Agent": f"F1-Analytics/{settings.app.app_version} (+https://github.com/your-org/f1-analytics)",
            "Accept": "application/json",
            "Content-Type": "application/json"
        }

    @classmethod
    def get_season_config(cls, season: int) -> Dict[str, Any]:
        """
        Get season-specific configuration.

        Args:
            season: F1 season year

        Returns:
            dict: Season-specific configuration
        """
        # Default configuration
        config = {
            'max_rounds': 24,
            'points_system': 'current',  # current, legacy
            'sprint_races': False,
            'expected_drivers': 20,
            'expected_teams': 10
        }

        # Season-specific overrides
        if season >= 2019:
            config['max_rounds'] = 24
        elif season >= 2016:
            config['max_rounds'] = 21
        else:
            config['max_rounds'] = 20

        if season >= 2021:
            config['sprint_races'] = True

        if season <= 2009:
            config['points_system'] = 'legacy'

        return config


# Validation rules for different data types
VALIDATION_RULES = {
    'race': {
        'required_fields': ['round', 'raceName', 'date', 'Circuit'],
        'optional_fields': ['time', 'url', 'FirstPractice', 'SecondPractice', 'ThirdPractice', 'Qualifying']
    },
    'race_result': {
        'required_fields': ['position', 'Driver', 'Constructor', 'grid', 'points', 'status'],
        'optional_fields': ['laps', 'Time', 'FastestLap']
    },
    'qualifying_result': {
        'required_fields': ['position', 'Driver'],
        'optional_fields': ['Q1', 'Q2', 'Q3']
    },
    'driver': {
        'required_fields': ['driverId', 'familyName'],
        'optional_fields': ['givenName', 'dateOfBirth', 'nationality', 'url', 'code']
    },
    'team': {
        'required_fields': ['constructorId', 'name'],
        'optional_fields': ['nationality', 'url']
    },
    'circuit': {
        'required_fields': ['circuitId', 'circuitName', 'Location'],
        'optional_fields': ['url']
    }
}

# Error handling configuration
ERROR_HANDLING = {
    'continue_on_error': True,
    'max_errors_per_batch': 5,
    'log_all_errors': True,
    'retry_failed_requests': True
}

# Logging configuration for ingestion
LOGGING_CONFIG = {
    'level': 'INFO',
    'format': '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    'log_api_requests': False,  # Set to True for debugging
    'log_data_validation': True
}