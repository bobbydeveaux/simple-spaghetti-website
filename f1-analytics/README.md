# F1 Prediction Analytics Backend

## Overview

This is the backend system for Formula 1 prediction analytics, providing SQLAlchemy ORM models, database migrations, and data management infrastructure for F1 racing data analysis and machine learning predictions.

## Architecture

### Database Schema

The system uses PostgreSQL with the following main entities:

#### Core Entities
- **Teams**: F1 constructors with Elo ratings
- **Drivers**: F1 drivers with team associations and Elo ratings
- **Circuits**: Race tracks with characteristics (length, type)
- **Races**: Race events with season/round information

#### Results & Performance
- **RaceResults**: Final race positions, points, and performance data
- **QualifyingResults**: Qualifying session times and grid positions
- **WeatherData**: Race weather conditions affecting performance

#### Predictions & Analysis
- **Predictions**: ML-generated win probabilities by model version
- **PredictionAccuracy**: Post-race accuracy metrics (Brier score, log loss)
- **Users**: Authentication for system access

### Key Features

- **Comprehensive Constraints**: Check constraints for data validation
- **Performance Indexes**: Optimized queries for race data and predictions
- **Materialized Views**: Driver rankings for fast leaderboard queries
- **Table Partitioning**: Ready for partitioning race_results and predictions by race_id
- **Foreign Key Relationships**: Proper referential integrity across entities

## Project Structure

```
f1-analytics/backend/
├── app/
│   ├── models/           # SQLAlchemy ORM models
│   │   ├── __init__.py   # Model exports
│   │   ├── driver.py     # Driver model
│   │   ├── team.py       # Team/constructor model
│   │   ├── circuit.py    # Circuit/track model
│   │   ├── race.py       # Race event model
│   │   ├── race_result.py     # Race results
│   │   ├── qualifying_result.py # Qualifying results
│   │   ├── weather_data.py    # Weather conditions
│   │   ├── prediction.py      # ML predictions
│   │   ├── prediction_accuracy.py # Accuracy metrics
│   │   └── user.py       # User authentication
│   ├── config.py         # Configuration settings
│   ├── database.py       # Database connection & session
│   └── dependencies.py   # FastAPI dependencies
├── alembic/             # Database migrations
│   ├── env.py           # Alembic environment
│   └── versions/        # Migration scripts
├── alembic.ini          # Alembic configuration
├── requirements.txt     # Python dependencies
└── test_models.py       # Model validation tests
```

## Database Schema Details

### Core Tables

**teams**
- `team_id` (PK), `team_name` (unique), `nationality`
- `current_elo_rating` (performance tracking)
- Created/updated timestamps

**drivers**
- `driver_id` (PK), `driver_code` (3-char unique), `driver_name`
- `current_team_id` (FK to teams), `current_elo_rating`
- `date_of_birth`, nationality

**circuits**
- `circuit_id` (PK), `circuit_name` (unique), location, country
- `track_length_km`, `track_type` (street/permanent)

**races**
- `race_id` (PK), `season_year`, `round_number`, `race_date`
- `circuit_id` (FK), race_name, status
- Unique constraint on (season_year, round_number)

### Results Tables

**race_results** (partitioned by race_id)
- Result data: grid_position, final_position, points
- Performance: fastest_lap_time, status
- Foreign keys: race_id, driver_id, team_id

**qualifying_results**
- Session times: q1_time, q2_time, q3_time
- final_grid_position

**weather_data** (1:1 with races)
- `temperature_celsius`, `precipitation_mm`, `wind_speed_kph`
- `conditions` (dry/wet/mixed/overcast/sunny)

### Prediction Tables

**predictions** (partitioned by race_id)
- `predicted_win_probability` (0-100%), `model_version`
- `prediction_timestamp` for temporal analysis
- Unique per (race_id, driver_id, model_version)

**prediction_accuracy** (1:1 with completed races)
- `brier_score`, `log_loss` (probabilistic accuracy)
- `correct_winner`, `top_3_accuracy` (classification accuracy)

### Authentication

**users**
- `email` (unique), `password_hash` (bcrypt)
- `role` (user/admin), login tracking

## Configuration

### Environment Variables

```bash
# Database
F1_DATABASE_URL=postgresql://f1_user:f1_password@localhost:5432/f1_analytics
TEST_DATABASE_URL=postgresql://f1_user:f1_password@localhost:5432/f1_analytics_test

# Connection Pool
DATABASE_POOL_SIZE=10
DATABASE_MAX_OVERFLOW=20
DATABASE_POOL_TIMEOUT=30
DATABASE_POOL_RECYCLE=3600

# Application
ENVIRONMENT=development
DEBUG=true
```

## Setup Instructions

### 1. Install Dependencies

```bash
cd f1-analytics/backend
pip install -r requirements.txt
```

### 2. Database Setup

```bash
# Create PostgreSQL database
createdb f1_analytics

# Run migrations
alembic upgrade head
```

### 3. Verify Installation

```bash
# Run model validation tests
python test_models.py

# Check migration status
alembic current
```

## Model Usage Examples

### Creating Data

```python
from app.models import Team, Driver, Circuit, Race
from app.database import SessionLocal

db = SessionLocal()

# Create team
team = Team(team_name="Red Bull Racing", nationality="Austria")
db.add(team)

# Create driver
driver = Driver(
    driver_code="VER",
    driver_name="Max Verstappen",
    nationality="Netherlands",
    date_of_birth=date(1997, 9, 30),
    current_team=team
)
db.add(driver)

db.commit()
```

### Querying Data

```python
# Get driver with team
driver = db.query(Driver).filter(Driver.driver_code == "VER").first()
print(f"{driver.driver_name} drives for {driver.current_team.team_name}")

# Get race results with relationships
results = (db.query(RaceResult)
          .join(Race)
          .join(Driver)
          .filter(Race.season_year == 2024)
          .order_by(Race.race_date)
          .all())
```

### Model Properties

```python
# Driver properties
print(f"Age: {driver.age}")
print(f"Current team: {driver.current_team.team_name}")

# Race status checks
print(f"Completed: {race.is_completed}")
print(f"Future race: {race.is_future_race}")

# Weather analysis
print(f"Hot weather: {weather.is_hot_weather}")
print(f"Impact score: {weather.weather_impact_score}/10")

# Prediction confidence
print(f"Confidence: {prediction.confidence_category}")
print(f"Is favorite: {prediction.is_favorite}")
```

## Performance Features

### Indexes
- Composite indexes on common query patterns
- BRIN indexes for time-series data (predictions)
- Covering indexes for leaderboard queries

### Materialized Views
- `driver_rankings`: Pre-computed driver statistics
- Refreshed daily via scheduled jobs

### Constraints
- Check constraints for data validation
- Unique constraints for business rules
- Foreign key constraints for referential integrity

## Migration Management

### Create New Migration
```bash
alembic revision --autogenerate -m "Description"
```

### Apply Migrations
```bash
alembic upgrade head
```

### Rollback Migration
```bash
alembic downgrade -1
```

## Next Steps (Sprint 2+)

1. **FastAPI Routes**: REST API endpoints for data access
2. **Authentication**: JWT token management and role-based access
3. **Data Import**: Scripts to populate from F1 data sources
4. **ML Pipeline**: Prediction model training and evaluation
5. **Performance Optimization**: Query optimization and caching

## Dependencies

- **SQLAlchemy 2.0+**: ORM and database toolkit
- **Alembic**: Database migration management
- **psycopg2**: PostgreSQL database adapter
- **FastAPI**: Modern Python web framework (future)
- **Pydantic**: Data validation and serialization (future)

## Contributing

This is Sprint 1 of the F1 prediction analytics system, focusing on database schema and models. Future sprints will add API endpoints, ML pipelines, and web interfaces.