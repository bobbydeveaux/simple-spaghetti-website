# F1 Data Ingestion System

The F1 Prediction Analytics platform includes a comprehensive data ingestion system that automatically imports race and qualifying data from external sources, primarily the official Ergast API.

## Overview

The data ingestion system consists of:

- **Race Data Ingestion**: Imports race schedules, results, and metadata
- **Qualifying Data Ingestion**: Imports qualifying session results and grid positions
- **Data Validation**: Ensures data integrity and consistency
- **Error Handling**: Robust retry mechanisms and error reporting
- **CLI Interface**: Command-line tools for manual data management

## Architecture

### Base Ingestion Service

All ingestion services inherit from `BaseIngestionService`, which provides:

- HTTP client management with proper timeouts and retries
- Error handling and logging
- Data validation utilities
- Database session management
- API rate limiting and throttling

### Service Components

```
app/ingestion/
├── __init__.py              # Module exports
├── base.py                  # Base ingestion service
├── race_ingestion.py        # Race data ingestion
├── qualifying_ingestion.py  # Qualifying data ingestion
├── config.py               # Ingestion configuration
└── cli.py                  # Command-line interface
```

## Data Sources

### Ergast API

The primary data source is the [Ergast Motor Racing API](http://ergast.com/mrd/), which provides:

- Historical F1 data from 1950 onwards
- Race schedules and results
- Qualifying session results
- Driver and constructor information
- Circuit details

#### API Configuration

```python
# Default configuration in app/config.py
ERGAST_BASE_URL = "https://ergast.com/api/f1"
ERGAST_TIMEOUT = 30  # seconds
ERGAST_RETRY_ATTEMPTS = 3
```

## Usage

### Command Line Interface

The system provides a convenient CLI for data ingestion operations:

```bash
# From the project root
python scripts/ingest_f1_data.py [command] [options]
```

#### Available Commands

##### Race Data Ingestion

```bash
# Ingest complete 2024 season races
python scripts/ingest_f1_data.py race 2024

# Ingest specific race round
python scripts/ingest_f1_data.py race 2024 --round 5

# Ingest schedule only (no results)
python scripts/ingest_f1_data.py race 2024 --no-results
```

##### Qualifying Data Ingestion

```bash
# Ingest complete 2024 season qualifying
python scripts/ingest_f1_data.py qualifying 2024

# Ingest specific race qualifying
python scripts/ingest_f1_data.py qualifying 2024 --round 5
```

##### Full Season Ingestion

```bash
# Ingest complete season data (races + qualifying)
python scripts/ingest_f1_data.py season 2024

# Skip qualifying data
python scripts/ingest_f1_data.py season 2024 --no-qualifying
```

##### Data Validation

```bash
# Validate ingested data
python scripts/ingest_f1_data.py validate 2024

# Validate specific race
python scripts/ingest_f1_data.py validate 2024 --round 5
```

### Programmatic Usage

#### Race Data Ingestion

```python
from app.ingestion import RaceIngestionService
from app.database import db_manager

async def ingest_race_data():
    race_service = RaceIngestionService()

    with db_manager.get_session() as session:
        results = await race_service.ingest_data(
            session=session,
            season=2024,
            race_round=None,  # All races
            include_results=True
        )

    print(f"Processed {results['races_processed']} races")
    print(f"Created {results['races_created']} new races")
```

#### Qualifying Data Ingestion

```python
from app.ingestion import QualifyingIngestionService

async def ingest_qualifying_data():
    qualifying_service = QualifyingIngestionService()

    results = await qualifying_service.run_ingestion(
        season=2024,
        race_round=5
    )

    print(f"Processed {results['qualifying_results_processed']} results")
```

## Data Models

The ingestion system populates the following database models:

### Race Model

```python
class Race(Base):
    race_id: int              # Primary key
    season_year: int          # F1 season (e.g., 2024)
    round_number: int         # Race round (1-24)
    circuit_id: int           # Foreign key to circuit
    race_date: date           # Race date
    race_name: str            # Official race name
    status: str               # scheduled, completed, cancelled
```

### RaceResult Model

```python
class RaceResult(Base):
    result_id: int            # Primary key
    race_id: int              # Foreign key to race
    driver_id: int            # Foreign key to driver
    team_id: int              # Foreign key to team
    grid_position: int        # Starting position
    final_position: int       # Finishing position
    points: Decimal           # Championship points
    fastest_lap_time: Interval # Fastest lap time
    status: str               # finished, retired, dnf, etc.
```

### QualifyingResult Model

```python
class QualifyingResult(Base):
    qualifying_id: int        # Primary key
    race_id: int              # Foreign key to race
    driver_id: int            # Foreign key to driver
    q1_time: Interval         # Q1 session time
    q2_time: Interval         # Q2 session time (null if eliminated)
    q3_time: Interval         # Q3 session time (null if eliminated)
    final_grid_position: int  # Grid position for race start
```

## Configuration

### Environment Variables

```bash
# Ergast API settings
F1_ERGAST_BASE_URL=https://ergast.com/api/f1
F1_ERGAST_TIMEOUT=30
F1_ERGAST_RETRY_ATTEMPTS=3

# Database settings
F1_DB_HOST=localhost
F1_DB_PORT=5432
F1_DB_NAME=f1_analytics
F1_DB_USER=f1_user
F1_DB_PASSWORD=f1_password
```

### Ingestion Configuration

```python
# app/ingestion/config.py
class IngestionConfig:
    REQUEST_DELAY = 0.1           # Delay between requests
    BATCH_SIZE = 10               # Records per batch
    MAX_CONCURRENT_REQUESTS = 3   # Concurrent API calls
    VALIDATE_LAP_TIMES = True     # Enable validation
    RETRY_BACKOFF_FACTOR = 2      # Exponential backoff
    MAX_RETRY_DELAY = 60          # Max retry delay (seconds)
```

## Error Handling

The ingestion system includes comprehensive error handling:

### Retry Logic

- **Exponential backoff** for rate limiting (429 errors)
- **Automatic retries** for server errors (5xx)
- **No retries** for client errors (4xx, except 429)
- **Configurable retry attempts** and delays

### Error Types

```python
class IngestionError(Exception):
    """Base exception for ingestion errors"""

class APIError(IngestionError):
    """External API request failures"""

class DataValidationError(IngestionError):
    """Data integrity validation failures"""
```

### Error Reporting

```python
# Example error handling output
{
    "errors": [
        "Error processing race 5: Missing required field 'date'",
        "API request failed after 3 attempts: Server Error"
    ],
    "warnings": [
        "Driver VER in P5 missing Q2 time",
        "Race result points don't match expected allocation"
    ]
}
```

## Data Validation

### Validation Rules

#### Race Data
- Required fields: `round`, `raceName`, `date`, `Circuit`
- Date format validation
- Round number sequence validation
- Circuit data completeness

#### Qualifying Data
- Q1 times required for all drivers
- Q2 times expected for top 15 drivers
- Q3 times expected for top 10 drivers
- Grid position sequence validation (1-20)
- Lap time format validation

#### Results Data
- Points allocation validation
- Position sequence validation
- Status field validation
- Lap time format validation

### Validation Commands

```bash
# Run comprehensive validation
python scripts/ingest_f1_data.py validate 2024

# Output example:
Validation Results for 2024:
  Races validated: 24
  Issues found: 2
  Warnings: 5

Issues found:
  Race: Monaco Grand Prix
    - Grid positions not sequential: [1, 2, 4, 5]
    - Driver 123 missing Q1 time

Warnings:
  - Driver 456 in P8 missing Q2 time
  - Race duration exceeds expected maximum
```

## Performance Considerations

### Rate Limiting

The Ergast API has rate limiting. The ingestion system:
- Implements delays between requests
- Uses exponential backoff for rate limit responses
- Respects server rate limit headers
- Limits concurrent requests

### Batch Processing

Large data imports are processed in batches:
- Default batch size: 10 records
- Configurable batch sizes
- Progress reporting for long operations
- Memory-efficient processing

### Caching

- HTTP response caching for repeated requests
- Database query optimization
- Efficient upsert operations for existing data

## Monitoring and Logging

### Logging Levels

```python
# Configure logging level
F1_LOG_LEVEL=INFO  # DEBUG, INFO, WARNING, ERROR
```

### Log Output Example

```
2024-03-15 10:30:15 - app.ingestion.race - INFO - Starting race ingestion for season 2024
2024-03-15 10:30:16 - app.ingestion.race - DEBUG - API request: https://ergast.com/api/f1/2024.json
2024-03-15 10:30:17 - app.ingestion.race - INFO - Found 24 races to process
2024-03-15 10:30:18 - app.ingestion.race - DEBUG - Created circuit: Bahrain International Circuit
2024-03-15 10:30:19 - app.ingestion.race - DEBUG - Created race: Bahrain Grand Prix (Round 1)
2024-03-15 10:30:45 - app.ingestion.race - INFO - Race ingestion completed in 30.15 seconds
```

### Monitoring Metrics

The ingestion system provides metrics for monitoring:
- Records processed per minute
- Error rates and types
- API response times
- Database operation times
- Data quality scores

## Troubleshooting

### Common Issues

#### API Connection Errors
```bash
# Check API availability
curl https://ergast.com/api/f1/current.json

# Verify network connectivity
ping ergast.com
```

#### Database Connection Issues
```bash
# Test database connection
python -c "from app.database import db_manager; print(db_manager.test_connection())"
```

#### Data Validation Failures
```bash
# Run validation with debug logging
F1_LOG_LEVEL=DEBUG python scripts/ingest_f1_data.py validate 2024
```

#### Performance Issues
- Check database indexes on foreign keys
- Monitor API rate limiting
- Verify adequate system resources
- Consider batch size adjustments

### Debugging

Enable debug logging for detailed operation information:

```bash
# Debug mode
F1_LOG_LEVEL=DEBUG python scripts/ingest_f1_data.py race 2024
```

Debug output includes:
- Individual API requests and responses
- Database queries and operations
- Data transformation steps
- Validation checks and results

## Future Enhancements

Planned improvements to the ingestion system:

1. **Real-time Updates**: WebSocket or polling for live race data
2. **Multiple Data Sources**: Integration with additional F1 data providers
3. **Data Quality Scoring**: Automated data quality assessment
4. **Incremental Updates**: Delta processing for changed data only
5. **Parallel Processing**: Multi-threaded ingestion for improved performance
6. **Data Lineage**: Track data sources and transformation history

## Contributing

When contributing to the ingestion system:

1. Follow the existing patterns in `BaseIngestionService`
2. Add comprehensive tests for new functionality
3. Update configuration documentation
4. Include error handling and logging
5. Validate data integrity thoroughly

## License

This data ingestion system is part of the F1 Prediction Analytics platform and follows the same licensing terms as the main project.