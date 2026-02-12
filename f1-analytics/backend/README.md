# F1 Analytics Backend

Formula One prediction analytics API built with FastAPI, SQLAlchemy, and PostgreSQL.

## Overview

This backend provides the data layer and API endpoints for the F1 prediction analytics platform. It includes:

- **Database Models**: 10 core entities for F1 data (drivers, teams, races, predictions, etc.)
- **REST API**: FastAPI endpoints for data access and analytics
- **ML Integration**: Model prediction storage and accuracy tracking
- **Authentication**: JWT-based user authentication and authorization

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

## Features

### Database Design
- **Partitioning**: `race_results` and `predictions` tables partitioned by race_id for performance
- **Indexes**: Strategic indexing on foreign keys and frequently queried columns
- **Constraints**: Check constraints for data validation and integrity
- **Materialized Views**: Pre-aggregated driver rankings for fast queries

### Migration System
- **Alembic**: Database migration management with upgrade/downgrade support
- **Version Control**: Migration scripts tracked in `alembic/versions/`
- **Environment**: Support for development and production database configurations

### Configuration
- **Environment Variables**: Flexible configuration via .env files
- **Connection Pooling**: SQLAlchemy connection pooling for scalability
- **Multi-Environment**: Support for development, staging, and production

## Setup

### Prerequisites
- Python 3.8+
- PostgreSQL 12+
- Redis (for caching)

### Installation

1. **Install Dependencies**
   ```bash
   pip install -r requirements.txt
   ```

2. **Environment Configuration**
   ```bash
   cp .env.example .env
   # Edit .env with your database credentials
   ```

3. **Database Migration**
   ```bash
   alembic upgrade head
   ```

4. **Run Application**
   ```bash
   python app/main.py
   ```

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
│   ├── versions/
│   │   └── 001_initial_schema.py
│   ├── env.py
│   └── script.py.mako
├── app/                        # Application code
│   ├── models/                 # SQLAlchemy ORM models
│   │   ├── driver.py
│   │   ├── team.py
│   │   ├── race.py
│   │   └── ...
│   ├── schemas/                # Pydantic schemas
│   ├── repositories/           # Data access layer
│   ├── services/               # Business logic
│   ├── routes/                 # API endpoints
│   ├── middleware/             # Custom middleware
│   ├── config.py               # Configuration management
│   ├── database.py             # Database connection
│   ├── dependencies.py         # Dependency injection
│   └── main.py                 # FastAPI application
├── requirements.txt            # Python dependencies
├── alembic.ini                 # Alembic configuration
├── .env.example                # Environment variables template
└── README.md                   # This file
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

### Schema Validation
```bash
python verify_schema.py
```

## Environment Variables

Key configuration options:

| Variable | Description | Default |
|----------|-------------|---------|
| `DB_HOST` | PostgreSQL host | `localhost` |
| `DB_PORT` | PostgreSQL port | `5432` |
| `DB_NAME` | Database name | `f1_analytics` |
| `DB_USER` | Database user | `postgres` |
| `DB_PASSWORD` | Database password | `password` |
| `ENVIRONMENT` | Runtime environment | `development` |
| `DEBUG` | Enable debug mode | `true` |
| `JWT_SECRET_KEY` | JWT signing key | (required) |

## Performance Features

- **Connection Pooling**: SQLAlchemy QueuePool with configurable size
- **Table Partitioning**: Large tables partitioned by race_id for faster queries
- **Materialized Views**: Pre-computed aggregations for analytics queries
- **Strategic Indexing**: Indexes optimized for common query patterns

## Security

- **JWT Authentication**: Secure token-based authentication
- **Password Hashing**: bcrypt for secure password storage
- **Input Validation**: Pydantic schemas for request validation
- **SQL Injection Protection**: SQLAlchemy ORM prevents injection attacks

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

## Support

For issues or questions regarding the F1 Analytics backend, please refer to the project documentation or create an issue in the repository.