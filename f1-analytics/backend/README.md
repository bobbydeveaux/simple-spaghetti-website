# F1 Analytics Backend

A comprehensive Formula One prediction analytics API built with FastAPI, SQLAlchemy, and PostgreSQL.

## Overview

This backend provides the data layer and API endpoints for the F1 prediction analytics platform, featuring:

- **Database Models**: 10 core entities for F1 data (drivers, teams, races, predictions, etc.)
- **REST API**: FastAPI endpoints for data access and analytics
- **Data Ingestion**: Automated F1 data collection from Ergast API
- **ML Integration**: Model prediction storage and accuracy tracking
- **Authentication**: JWT-based user authentication and authorization

## Features

### Database & Session Management
- **PostgreSQL Integration**: Full database support with connection pooling and health monitoring
- **Redis Sessions**: User session management with TTL and rate limiting
- **SQLAlchemy ORM**: Complete F1 data models with relationships and constraints
- **Alembic Migrations**: Database schema versioning and migration system

### Database Design
- **Partitioning**: `race_results` and `predictions` tables partitioned by race_id for performance
- **Indexes**: Strategic indexing on foreign keys and frequently queried columns
- **Constraints**: Check constraints for data validation and integrity
- **Materialized Views**: Pre-aggregated driver rankings for fast queries

### Authentication & Security
- **JWT Authentication**: Access and refresh token support with configurable expiration
- **Rate Limiting**: Per-user rate limiting (100 requests/minute by default)
- **Session Management**: Redis-backed user sessions with automatic cleanup
- **Secure Defaults**: Bcrypt password hashing, secure JWT configuration

### Repository Pattern
- **Base Repository**: Generic CRUD operations for all models
- **Specialized Repositories**: Domain-specific methods for F1 data
- **Async Support**: Both sync and async database operations
- **Bulk Operations**: Efficient batch processing for large datasets

## Database Schema

The system includes the following entities:

### Core F1 Entities
- **Driver**: F1 drivers with ELO ratings and team associations
- **Team**: Constructor teams with nationality and ELO ratings
- **Circuit**: Racing circuits with track characteristics
- **Race**: Grand Prix races with season/round information

### Results & Data
- **RaceResult**: Race finishing positions, points, and performance data
- **QualifyingResult**: Qualifying session times and grid positions
- **WeatherData**: Race weather conditions (temperature, precipitation, etc.)

### ML & Analytics
- **Prediction**: ML model predictions for race outcomes
- **PredictionAccuracy**: Model performance tracking and metrics
- **User**: Authentication and user management

## Quick Start

### Prerequisites
- Python 3.10+
- PostgreSQL 13+
- Redis 6+

### Installation

```bash
# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Set up environment variables
cp .env.example .env
# Edit .env with your database and Redis configuration
```

### Environment Configuration

Create a `.env` file with the following variables:

```env
# Database Configuration
F1_DB_HOST=localhost
F1_DB_PORT=5432
F1_DB_NAME=f1_analytics
F1_DB_USER=postgres
F1_DB_PASSWORD=your_password

# Redis Configuration
F1_REDIS_HOST=localhost
F1_REDIS_PORT=6379
F1_REDIS_PASSWORD=optional_password

# JWT Configuration
F1_JWT_SECRET_KEY=your_secret_key_here
F1_JWT_ACCESS_TOKEN_EXPIRE_MINUTES=15
F1_JWT_REFRESH_TOKEN_EXPIRE_DAYS=7

# Application Settings
F1_ENVIRONMENT=development
F1_DEBUG=true
F1_RATE_LIMIT_REQUESTS=100
F1_RATE_LIMIT_WINDOW=60
```

### Database Setup

```bash
# Run migrations to create tables
alembic upgrade head

# Optional: Seed with sample data (future feature)
python scripts/seed_sample_data.py
```

### Running the Application

```bash
# Start the development server
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

## Data Ingestion

The F1 analytics backend includes comprehensive data ingestion capabilities for importing race and qualifying data.

### Quick Start Data Ingestion

```bash
# Import complete 2024 season data (races + qualifying)
python ../scripts/ingest_f1_data.py season 2024

# Import specific race data
python ../scripts/ingest_f1_data.py race 2024 --round 5

# Import qualifying data for a specific race
python ../scripts/ingest_f1_data.py qualifying 2024 --round 5

# Validate data integrity
python ../scripts/ingest_f1_data.py validate 2024
```

### Programmatic Usage

```python
from app.ingestion import RaceIngestionService, QualifyingIngestionService
from app.database import db_manager
import asyncio

async def ingest_season_data():
    """Example of programmatic data ingestion."""
    race_service = RaceIngestionService()
    qualifying_service = QualifyingIngestionService()

    # Import race data
    race_results = await race_service.run_ingestion(season=2024)
    print(f"Imported {race_results['races_created']} races")

    # Import qualifying data
    qualifying_results = await qualifying_service.run_ingestion(season=2024)
    print(f"Imported {qualifying_results['qualifying_results_created']} qualifying results")

# Run the ingestion
asyncio.run(ingest_season_data())
```

### Configuration

Data ingestion settings can be configured via environment variables:

```bash
# Ergast API settings
F1_ERGAST_BASE_URL=https://ergast.com/api/f1
F1_ERGAST_TIMEOUT=30
F1_ERGAST_RETRY_ATTEMPTS=3

# Weather API (optional)
F1_WEATHER_API_KEY=your_openweather_api_key
F1_WEATHER_BASE_URL=https://api.openweathermap.org/data/2.5
```

See [F1 Data Ingestion Documentation](../../docs/F1_DATA_INGESTION.md) for detailed usage information.

## Database Migration

### Create Migration
```bash
alembic revision --autogenerate -m "Description of changes"
```

### Apply Migrations
```bash
alembic upgrade head
```

### Rollback Migration
```bash
alembic downgrade -1
```

### Check Migration Status
```bash
alembic current
alembic history
```

## Schema Validation

Run the schema verification script to validate the implementation:

```bash
python verify_schema.py
```

This will test:
- Model imports and relationships
- Database configuration
- Migration script structure
- Syntax validation
## Project Structure

```
f1-analytics/backend/
├── alembic/                    # Database migrations
│   ├── versions/               # Migration scripts
│   │   └── 001_initial_schema.py
│   ├── env.py                  # Alembic environment configuration
│   └── script.py.mako
├── app/                        # Main application code
│   ├── models/                 # SQLAlchemy ORM models
│   │   ├── driver.py
│   │   ├── team.py
│   │   ├── race.py
│   │   ├── user.py            # User authentication model
│   │   └── ...
│   ├── ingestion/              # Data ingestion services
│   │   ├── base.py            # Base ingestion service
│   │   ├── race_ingestion.py  # Race data ingestion
│   │   ├── qualifying_ingestion.py # Qualifying data ingestion
│   │   ├── config.py          # Ingestion configuration
│   │   └── cli.py             # Command-line interface
│   ├── schemas/                # Pydantic schemas
│   ├── repositories/           # Data access layer
│   │   ├── base.py            # Base repository with CRUD operations
│   │   ├── user_repository.py # User-specific database operations
│   │   └── f1_repositories.py # F1-specific database operations
│   ├── services/               # Business logic
│   ├── routes/                 # API endpoints
│   ├── middleware/             # Custom middleware
│   ├── utils/                 # Utility modules
│   │   ├── jwt_manager.py     # JWT token management
│   │   └── session_manager.py # Redis session management
│   ├── config.py              # Configuration management
│   ├── database.py            # Database connection and session management
│   ├── dependencies.py        # FastAPI dependency injection
│   └── main.py                # FastAPI application
├── tests/                     # Test suite
│   ├── conftest.py           # Test configuration and fixtures
│   ├── unit/                 # Unit tests
│   │   └── test_models.py
│   ├── test_database.py      # Database functionality tests
│   ├── test_ingestion.py     # Data ingestion tests
│   └── test_session_management.py # Session and JWT tests
├── requirements.txt          # Python dependencies
├── alembic.ini              # Alembic configuration
├── .env.example             # Environment variables template
├── test_syntax.py           # Syntax validation
├── verify_schema.py         # Schema verification
└── README.md                # This file
```

## API Documentation

When running the application, API documentation is available at:
- Swagger UI: `http://localhost:8000/api/docs`
- ReDoc: `http://localhost:8000/api/redoc`

## Testing

### Syntax Check
```bash
python test_syntax.py
```

### Running Tests

```bash
# Install test dependencies
pip install -r requirements.txt

# Run all tests
pytest

# Run with coverage
pytest --cov=app --cov-report=html

# Run specific test categories
pytest tests/test_database.py
pytest tests/test_session_management.py
pytest tests/test_ingestion.py
```

## Environment Variables

Key configuration options:

| Variable | Description | Default |
|----------|-------------|---------|
| `F1_DB_HOST` | PostgreSQL host | `localhost` |
| `F1_DB_PORT` | PostgreSQL port | `5432` |
| `F1_DB_NAME` | Database name | `f1_analytics` |
| `F1_DB_USER` | Database user | `postgres` |
| `F1_DB_PASSWORD` | Database password | `your_password` |
| `F1_ENVIRONMENT` | Runtime environment | `development` |
| `F1_DEBUG` | Enable debug mode | `true` |
| `F1_JWT_SECRET_KEY` | JWT signing key | (required) |

## Performance Features

- **Connection Pooling**: SQLAlchemy QueuePool with configurable size
- **Table Partitioning**: Large tables partitioned by race_id for faster queries
- **Materialized Views**: Pre-computed aggregations for analytics queries
- **Strategic Indexing**: Indexes optimized for common query patterns

### Caching Strategy
- Prediction results cached for 7 days
- Race calendar cached for 24 hours
- Driver rankings cached for 1 hour
- Automatic cache invalidation on data updates

## Security

- **JWT Authentication**: Secure token-based authentication
- **Password Hashing**: bcrypt for secure password storage
- **Input Validation**: Pydantic schemas for request validation
- **SQL Injection Protection**: SQLAlchemy ORM prevents injection attacks
- **Rate Limiting**: Per-user request limits to prevent abuse

## Health Checks

The application provides health check endpoints:

- **Database Health**: `/health/database` - PostgreSQL connection status
- **Redis Health**: `/health/redis` - Redis connectivity and memory usage
- **Overall Health**: `/health` - Combined system health status

## Production Deployment

For production deployment:

1. **Set Production Environment Variables**
2. **Use Connection Pooling** with appropriate pool sizes
3. **Enable SSL** for database connections
4. **Configure Logging** with appropriate levels
5. **Set up Monitoring** for database performance
6. **Backup Strategy** for critical race and prediction data

## Development

### Adding New Models

1. Create model file in `app/models/`
2. Add import to `app/models/__init__.py`
3. Generate migration: `alembic revision --autogenerate -m "Add new model"`
4. Apply migration: `alembic upgrade head`

### Database Schema Changes

Always use Alembic migrations for schema changes to maintain version control and enable rollbacks.

### Development Guidelines

#### Code Style
- Black for code formatting
- isort for import organization
- flake8 for linting
- mypy for type checking

#### Testing Standards
- Minimum 80% code coverage
- Unit tests for all business logic
- Integration tests for database operations
- Mocked external dependencies

## Future Enhancements

### Implemented Features
- ✅ **External API Data Ingestion**: Complete Ergast F1 API integration with race and qualifying data
- ✅ **Data Validation**: Comprehensive validation and error handling for ingested data
- ✅ **CLI Tools**: Command-line interface for data management operations

### Planned Features
- ML model training integration
- Real-time prediction updates
- Advanced analytics and reporting
- API rate limiting per endpoint
- Audit logging for all operations

### Scalability Improvements
- Read replica support for database queries
- Redis cluster configuration
- Horizontal scaling with load balancing
- Metrics and monitoring integration

## Support

For issues or questions regarding the F1 Analytics backend, please refer to the project documentation or create an issue in the repository.
