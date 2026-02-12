# F1 Analytics Database Schema Documentation

**Created:** 2026-02-12
**Status:** Implemented
**Sprint 1 Task:** `f1-prediction-analytics-feat-database-schema-1`

## Overview

The F1 Prediction Analytics database schema has been successfully implemented with SQLAlchemy ORM models and Alembic migrations. This document describes the implemented database structure for the Formula 1 prediction analytics system.

## Schema Summary

The database consists of **10 core tables** organized into three logical groups:

### Core F1 Entities (4 tables)
- **drivers** - Formula 1 drivers with ELO ratings
- **teams** - Constructor teams with ELO ratings
- **circuits** - Racing circuits and track information
- **races** - Grand Prix races and calendar

### Race Data (3 tables)
- **race_results** - Race finishing positions and performance
- **qualifying_results** - Qualifying session results and grid positions
- **weather_data** - Weather conditions during races

### Predictions & Analytics (3 tables)
- **predictions** - ML model predictions for race winners
- **prediction_accuracy** - Accuracy metrics and performance tracking
- **users** - User authentication for dashboard access

## Implemented Models

### 1. Driver Model (`drivers` table)

```python
class Driver(Base):
    __tablename__ = "drivers"

    driver_id = Column(Integer, primary_key=True, index=True)
    driver_code = Column(String(3), unique=True, nullable=False, index=True)  # e.g., 'VER', 'HAM'
    driver_name = Column(String(100), nullable=False)
    nationality = Column(String(50))
    date_of_birth = Column(Date)
    current_team_id = Column(Integer, ForeignKey("teams.team_id"), nullable=True)
    current_elo_rating = Column(Integer, default=1500, index=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
```

**Key Features:**
- Three-letter driver codes (VER, HAM, LEC)
- ELO rating system for performance ranking (default 1500)
- Current team association (nullable for retired drivers)
- Automatic timestamp tracking

### 2. Team Model (`teams` table)

```python
class Team(Base):
    __tablename__ = "teams"

    team_id = Column(Integer, primary_key=True, index=True)
    team_name = Column(String(100), unique=True, nullable=False)
    nationality = Column(String(50))
    current_elo_rating = Column(Integer, default=1500, index=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
```

**Key Features:**
- Unique team names (Red Bull Racing, Mercedes, etc.)
- Team ELO ratings for constructor performance
- Nationality tracking

### 3. Circuit Model (`circuits` table)

```python
class Circuit(Base):
    __tablename__ = "circuits"

    circuit_id = Column(Integer, primary_key=True, index=True)
    circuit_name = Column(String(100), unique=True, nullable=False)
    location = Column(String(100))
    country = Column(String(50))
    track_length_km = Column(Numeric(5, 2))  # e.g., 5.891 km
    track_type = Column(String(20))  # 'street', 'permanent'
    created_at = Column(DateTime, default=datetime.utcnow)
```

**Key Features:**
- Track characteristics (length, type)
- Location and country information
- Check constraint for track_type ('street', 'permanent')

### 4. Race Model (`races` table)

```python
class Race(Base):
    __tablename__ = "races"

    race_id = Column(Integer, primary_key=True, index=True)
    season_year = Column(Integer, nullable=False, index=True)
    round_number = Column(Integer, nullable=False)
    circuit_id = Column(Integer, ForeignKey("circuits.circuit_id"), nullable=False)
    race_date = Column(Date, nullable=False, index=True)
    race_name = Column(String(100), nullable=False)
    status = Column(String(20), default="scheduled", index=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
```

**Key Features:**
- Season and round tracking (2024-R01, 2024-R02, etc.)
- Race status tracking (scheduled, completed, cancelled)
- Unique constraint on (season_year, round_number)

### 5. RaceResult Model (`race_results` table)

```python
class RaceResult(Base):
    __tablename__ = "race_results"

    result_id = Column(Integer, primary_key=True, index=True)
    race_id = Column(Integer, ForeignKey("races.race_id"), nullable=False, index=True)
    driver_id = Column(Integer, ForeignKey("drivers.driver_id"), nullable=False, index=True)
    team_id = Column(Integer, ForeignKey("teams.team_id"), nullable=False)
    grid_position = Column(Integer)  # Starting position
    final_position = Column(Integer)  # Finishing position (null if DNF)
    points = Column(Numeric(4, 1), default=0.0)  # Championship points
    fastest_lap_time = Column(Interval)  # PostgreSQL interval for lap times
    status = Column(String(20), default="finished")
    created_at = Column(DateTime, default=datetime.utcnow)
```

**Key Features:**
- Grid and finishing position tracking
- Championship points calculation
- Fastest lap time storage (PostgreSQL INTERVAL type)
- Result status (finished, retired, dnf, disqualified)
- Unique constraint per (race_id, driver_id)

### 6. QualifyingResult Model (`qualifying_results` table)

```python
class QualifyingResult(Base):
    __tablename__ = "qualifying_results"

    qualifying_id = Column(Integer, primary_key=True, index=True)
    race_id = Column(Integer, ForeignKey("races.race_id"), nullable=False, index=True)
    driver_id = Column(Integer, ForeignKey("drivers.driver_id"), nullable=False, index=True)
    q1_time = Column(Interval)  # Q1 lap time
    q2_time = Column(Interval)  # Q2 lap time (null if eliminated)
    q3_time = Column(Interval)  # Q3 lap time (null if not reached)
    final_grid_position = Column(Integer, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
```

**Key Features:**
- Three qualifying session times (Q1, Q2, Q3)
- Grid position determination
- Null handling for eliminated drivers

### 7. WeatherData Model (`weather_data` table)

```python
class WeatherData(Base):
    __tablename__ = "weather_data"

    weather_id = Column(Integer, primary_key=True, index=True)
    race_id = Column(Integer, ForeignKey("races.race_id"), unique=True, nullable=False)
    temperature_celsius = Column(Numeric(4, 1))  # e.g., 25.5°C
    precipitation_mm = Column(Numeric(5, 2))  # e.g., 12.50 mm
    wind_speed_kph = Column(Numeric(5, 2))  # e.g., 15.75 kph
    conditions = Column(String(20))  # dry, wet, mixed
    created_at = Column(DateTime, default=datetime.utcnow)
```

**Key Features:**
- One weather record per race (unique race_id)
- Comprehensive weather metrics
- Categorical conditions classification

### 8. Prediction Model (`predictions` table)

```python
class Prediction(Base):
    __tablename__ = "predictions"

    prediction_id = Column(Integer, primary_key=True, index=True)
    race_id = Column(Integer, ForeignKey("races.race_id"), nullable=False, index=True)
    driver_id = Column(Integer, ForeignKey("drivers.driver_id"), nullable=False, index=True)
    predicted_win_probability = Column(Numeric(5, 2), nullable=False)  # 0.00-100.00
    model_version = Column(String(50), nullable=False)
    prediction_timestamp = Column(DateTime, default=datetime.utcnow, index=True)
    created_at = Column(DateTime, default=datetime.utcnow)
```

**Key Features:**
- Win probability percentages (0.00-100.00%)
- Model versioning for tracking performance
- Check constraint ensuring probabilities are 0-100
- Unique constraint per (race_id, driver_id, model_version)

### 9. PredictionAccuracy Model (`prediction_accuracy` table)

```python
class PredictionAccuracy(Base):
    __tablename__ = "prediction_accuracy"

    accuracy_id = Column(Integer, primary_key=True, index=True)
    race_id = Column(Integer, ForeignKey("races.race_id"), unique=True, nullable=False)
    brier_score = Column(Numeric(6, 4))  # e.g., 0.1234 (range 0-1)
    log_loss = Column(Numeric(6, 4))  # e.g., 2.3456
    correct_winner = Column(Boolean)  # True if predicted winner was correct
    top_3_accuracy = Column(Boolean)  # True if actual winner was in predicted top 3
    created_at = Column(DateTime, default=datetime.utcnow)
```

**Key Features:**
- Brier score and log loss metrics
- Binary accuracy indicators
- One accuracy record per completed race

### 10. User Model (`users` table)

```python
class User(Base):
    __tablename__ = "users"

    user_id = Column(Integer, primary_key=True, index=True)
    email = Column(String(255), unique=True, nullable=False, index=True)
    password_hash = Column(String(255), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    last_login = Column(DateTime, nullable=True)
    role = Column(String(20), default="user")  # user, admin
```

**Key Features:**
- Bcrypt password hashing
- Email validation
- Role-based access control
- Login tracking

## Database Relationships

### Primary Relationships

```
drivers ←→ teams (many-to-one: drivers.current_team_id → teams.team_id)
races → circuits (many-to-one: races.circuit_id → circuits.circuit_id)
race_results → races, drivers, teams (many-to-one foreign keys)
qualifying_results → races, drivers (many-to-one foreign keys)
weather_data → races (one-to-one: weather_data.race_id → races.race_id)
predictions → races, drivers (many-to-one foreign keys)
prediction_accuracy → races (one-to-one: prediction_accuracy.race_id → races.race_id)
```

### Cascade Relationships

- **Race deletion cascades to**: race_results, qualifying_results, weather_data, predictions, prediction_accuracy
- **Driver/Team deletion**: Protected by foreign key constraints
- **Circuit deletion**: Protected by existing race references

## Performance Optimizations

### Indexes Implemented

```sql
-- Driver indexes
CREATE INDEX idx_drivers_code ON drivers(driver_code);
CREATE INDEX idx_drivers_elo ON drivers(current_elo_rating DESC);

-- Race indexes
CREATE INDEX idx_races_date ON races(race_date);
CREATE INDEX idx_races_season ON races(season_year, round_number);
CREATE INDEX idx_races_status ON races(status);

-- Prediction indexes
CREATE INDEX idx_predictions_race ON predictions(race_id);
CREATE INDEX idx_predictions_timestamp ON predictions(prediction_timestamp DESC);

-- Composite indexes for common queries
CREATE INDEX idx_race_results_race ON race_results(race_id);
CREATE INDEX idx_race_results_driver ON race_results(driver_id);
```

### Materialized View

```sql
CREATE MATERIALIZED VIEW driver_rankings AS
SELECT
    d.driver_id,
    d.driver_name,
    d.current_elo_rating,
    COUNT(CASE WHEN rr.final_position = 1 THEN 1 END) as wins,
    COALESCE(SUM(rr.points), 0) as total_points,
    MAX(r.season_year) as latest_season
FROM drivers d
LEFT JOIN race_results rr ON d.driver_id = rr.driver_id
LEFT JOIN races r ON rr.race_id = r.race_id
GROUP BY d.driver_id, d.driver_name, d.current_elo_rating
ORDER BY d.current_elo_rating DESC;
```

## Data Integrity Constraints

### Check Constraints

```sql
-- Circuit track type validation
ALTER TABLE circuits ADD CONSTRAINT ck_circuit_track_type
    CHECK (track_type IN ('street', 'permanent'));

-- Race status validation
ALTER TABLE races ADD CONSTRAINT ck_race_status
    CHECK (status IN ('scheduled', 'completed', 'cancelled'));

-- Race result status validation
ALTER TABLE race_results ADD CONSTRAINT ck_race_result_status
    CHECK (status IN ('finished', 'retired', 'dnf', 'disqualified'));

-- Weather conditions validation
ALTER TABLE weather_data ADD CONSTRAINT ck_weather_conditions
    CHECK (conditions IN ('dry', 'wet', 'mixed'));

-- Prediction probability range validation
ALTER TABLE predictions ADD CONSTRAINT ck_prediction_probability_range
    CHECK (predicted_win_probability >= 0 AND predicted_win_probability <= 100);

-- User role validation
ALTER TABLE users ADD CONSTRAINT ck_user_role
    CHECK (role IN ('user', 'admin'));
```

### Unique Constraints

```sql
-- Ensure unique season/round combinations
ALTER TABLE races ADD CONSTRAINT uq_race_season_round
    UNIQUE (season_year, round_number);

-- One result per driver per race
ALTER TABLE race_results ADD CONSTRAINT uq_race_result_race_driver
    UNIQUE (race_id, driver_id);

-- One prediction per driver per race per model
ALTER TABLE predictions ADD CONSTRAINT uq_prediction_race_driver_model
    UNIQUE (race_id, driver_id, model_version);
```

## Migration Status

✅ **Migration 001**: Initial F1 Analytics Schema
- **File**: `alembic/versions/001_initial_f1_analytics_schema.py`
- **Status**: Implemented and tested
- **Creates**: All 10 tables with indexes, constraints, and materialized view

## Testing Coverage

✅ **Unit Tests**: 30+ test cases covering:
- Model creation and validation
- Relationship integrity
- Property methods and calculations
- Constraint enforcement
- Password hashing and validation
- Brier score and log loss calculations

**Test File**: `tests/unit/test_models.py`

## Configuration

### Database Connection
- **Engine**: SQLAlchemy with connection pooling
- **Pool Size**: 20 connections
- **Max Overflow**: 10 connections
- **Pool Pre-ping**: Enabled for connection validation

### Environment Variables
```bash
DATABASE_URL=postgresql://f1_user:f1_password@localhost:5432/f1_analytics
DATABASE_POOL_SIZE=20
DATABASE_MAX_OVERFLOW=10
DEBUG=true  # Enables SQL query logging
```

## Next Steps (Future Sprints)

1. **Sprint 2**: Data ingestion pipelines (Ergast API integration)
2. **Sprint 3**: ELO rating calculation system
3. **Sprint 4**: ML feature engineering and model training
4. **Sprint 5**: Prediction inference service
5. **Sprint 6**: REST API endpoints
6. **Sprint 7**: Frontend dashboard

## Summary

The F1 Analytics database schema is now **fully implemented and tested** with:
- ✅ 10 SQLAlchemy models with full relationships
- ✅ Alembic migration system configured
- ✅ Performance indexes and materialized views
- ✅ Data integrity constraints and validation
- ✅ Comprehensive test coverage (30+ tests)
- ✅ Production-ready configuration

**Task Status**: ✅ **COMPLETED** - Ready for Sprint 2 data ingestion development.