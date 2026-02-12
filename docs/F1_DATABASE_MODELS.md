# F1 Prediction Analytics - Database Models Documentation

## Overview

This document describes the SQLAlchemy database models for the F1 Prediction Analytics system, implementing a comprehensive schema for Formula One data storage, predictions, and user management.

## Database Architecture

The database follows a normalized relational design with the following principles:
- **Data Integrity**: Foreign key constraints ensure referential integrity
- **Performance**: Strategic indexing for common query patterns
- **Scalability**: Designed for horizontal scaling with proper partitioning
- **Extensibility**: Clear relationships allow easy feature additions

## Core F1 Data Models

### Driver Model (`drivers` table)

Represents Formula One drivers with performance metrics and team associations.

```python
class Driver(Base):
    __tablename__ = "drivers"

    driver_id = Column(Integer, primary_key=True, index=True)
    driver_code = Column(String(3), unique=True, nullable=False, index=True)  # e.g., "VER", "HAM"
    driver_name = Column(String(100), nullable=False)                          # e.g., "Max Verstappen"
    nationality = Column(String(50))                                           # e.g., "Dutch"
    date_of_birth = Column(Date)
    current_team_id = Column(Integer, ForeignKey("teams.team_id"))
    current_elo_rating = Column(Integer, default=1500, index=True)            # Performance rating
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
```

**Key Features**:
- Unique driver codes for efficient lookups
- ELO rating system for performance tracking
- Team association for current team membership
- Timestamps for audit trail

### Team Model (`teams` table)

Represents Formula One constructor teams.

```python
class Team(Base):
    __tablename__ = "teams"

    team_id = Column(Integer, primary_key=True, index=True)
    team_name = Column(String(100), unique=True, nullable=False)               # e.g., "Red Bull Racing"
    nationality = Column(String(50))                                          # e.g., "Austrian"
    current_elo_rating = Column(Integer, default=1500, index=True)           # Team performance rating
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
```

**Relationships**:
- One-to-many with drivers (team has multiple drivers)
- One-to-many with race results

### Circuit Model (`circuits` table)

Represents racing circuits with technical specifications.

```python
class Circuit(Base):
    __tablename__ = "circuits"

    circuit_id = Column(Integer, primary_key=True, index=True)
    circuit_name = Column(String(100), unique=True, nullable=False)           # e.g., "Circuit de Monaco"
    location = Column(String(100))                                           # e.g., "Monte Carlo"
    country = Column(String(50))                                             # e.g., "Monaco"
    track_length_km = Column(Numeric(5, 2))                                  # e.g., 3.337
    track_type = Column(String(20), CheckConstraint("track_type IN ('street', 'permanent')"))
    created_at = Column(DateTime, default=datetime.utcnow)
```

**Key Features**:
- Technical specifications (length, type)
- Location information for geographical analysis
- Check constraints for data validation

### Race Model (`races` table)

Represents individual Formula One races within seasons.

```python
class Race(Base):
    __tablename__ = "races"

    race_id = Column(Integer, primary_key=True, index=True)
    season_year = Column(Integer, nullable=False, index=True)                 # e.g., 2026
    round_number = Column(Integer, nullable=False)                            # e.g., 6
    circuit_id = Column(Integer, ForeignKey("circuits.circuit_id"), nullable=False)
    race_date = Column(Date, nullable=False, index=True)
    race_name = Column(String(100), nullable=False)                           # e.g., "Monaco Grand Prix"
    status = Column(String(20), default="scheduled",                          # scheduled/completed/cancelled
                   CheckConstraint("status IN ('scheduled', 'completed', 'cancelled')"),
                   index=True)
    created_at = Column(DateTime, default=datetime.utcnow)
```

**Key Features**:
- Unique constraint on (season_year, round_number)
- Status tracking for race lifecycle
- Optimized indexes for date and status queries

## Result and Performance Models

### RaceResult Model (`race_results` table)

Stores race finish positions and performance data.

```python
class RaceResult(Base):
    __tablename__ = "race_results"

    result_id = Column(Integer, primary_key=True, index=True)
    race_id = Column(Integer, ForeignKey("races.race_id"), nullable=False, index=True)
    driver_id = Column(Integer, ForeignKey("drivers.driver_id"), nullable=False, index=True)
    team_id = Column(Integer, ForeignKey("teams.team_id"), nullable=False)
    grid_position = Column(Integer)                                           # Starting position
    final_position = Column(Integer)                                          # Finish position
    points = Column(Numeric(4, 1))                                           # Championship points
    fastest_lap_time = Column(Interval)                                       # Best lap time
    status = Column(String(20), default="finished",                          # finished/retired/dnf/disqualified
                   CheckConstraint("status IN ('finished', 'retired', 'dnf', 'disqualified')"))
    created_at = Column(DateTime, default=datetime.utcnow)
```

**Key Features**:
- Unique constraint on (race_id, driver_id) - one result per driver per race
- Performance metrics (positions, points, times)
- Status tracking for race outcomes

### QualifyingResult Model (`qualifying_results` table)

Stores qualifying session results and grid positions.

```python
class QualifyingResult(Base):
    __tablename__ = "qualifying_results"

    qualifying_id = Column(Integer, primary_key=True, index=True)
    race_id = Column(Integer, ForeignKey("races.race_id"), nullable=False, index=True)
    driver_id = Column(Integer, ForeignKey("drivers.driver_id"), nullable=False)
    q1_time = Column(Interval)                                               # Q1 session time
    q2_time = Column(Interval)                                               # Q2 session time
    q3_time = Column(Interval)                                               # Q3 session time
    final_grid_position = Column(Integer)                                    # Starting grid position
    created_at = Column(DateTime, default=datetime.utcnow)
```

## Prediction and Analytics Models

### Prediction Model (`predictions` table)

Stores ML-generated race winner predictions.

```python
class Prediction(Base):
    __tablename__ = "predictions"

    prediction_id = Column(Integer, primary_key=True, index=True)
    race_id = Column(Integer, ForeignKey("races.race_id"), nullable=False, index=True)
    driver_id = Column(Integer, ForeignKey("drivers.driver_id"), nullable=False)
    predicted_win_probability = Column(Numeric(5, 2), nullable=False,        # e.g., 35.75
                                     CheckConstraint("predicted_win_probability >= 0 AND predicted_win_probability <= 100"))
    model_version = Column(String(50), nullable=False)                       # e.g., "v1.0.0"
    prediction_timestamp = Column(DateTime, default=datetime.utcnow, index=True)
    created_at = Column(DateTime, default=datetime.utcnow)
```

**Key Features**:
- Unique constraint on (race_id, driver_id, model_version)
- Probability validation (0-100%)
- Model versioning for tracking improvements
- Timestamp indexing for performance queries

### PredictionAccuracy Model (`prediction_accuracy` table)

Tracks ML model performance and accuracy metrics.

```python
class PredictionAccuracy(Base):
    __tablename__ = "prediction_accuracy"

    accuracy_id = Column(Integer, primary_key=True, index=True)
    race_id = Column(Integer, ForeignKey("races.race_id"), unique=True, nullable=False)
    brier_score = Column(Numeric(6, 4))                                      # Calibration metric (lower is better)
    log_loss = Column(Numeric(6, 4))                                         # Prediction quality (lower is better)
    correct_winner = Column(Boolean)                                          # Did we predict the winner correctly?
    top_3_accuracy = Column(Boolean)                                          # Was actual winner in our top 3?
    created_at = Column(DateTime, default=datetime.utcnow)
```

**Key Features**:
- One accuracy record per race
- Multiple performance metrics
- Boolean flags for easy querying

### WeatherData Model (`weather_data` table)

Stores weather conditions affecting race performance.

```python
class WeatherData(Base):
    __tablename__ = "weather_data"

    weather_id = Column(Integer, primary_key=True, index=True)
    race_id = Column(Integer, ForeignKey("races.race_id"), unique=True, nullable=False)
    temperature_celsius = Column(Numeric(4, 1))                              # e.g., 25.5
    precipitation_mm = Column(Numeric(5, 2))                                 # Rainfall amount
    wind_speed_kph = Column(Numeric(5, 2))                                   # Wind speed
    conditions = Column(String(20), CheckConstraint("conditions IN ('dry', 'wet', 'mixed')"))
    created_at = Column(DateTime, default=datetime.utcnow)
```

## Authentication Models

### User Model (`users` table)

Enhanced user model with role-based access control.

```python
class User(Base):
    __tablename__ = "users"

    user_id = Column(Integer, primary_key=True, index=True)
    email = Column(String(255), unique=True, nullable=False, index=True)
    password_hash = Column(String(255), nullable=False)                      # bcrypt hashed
    username = Column(String(100))
    role = Column(String(20), default="user",                                # user/admin
                 CheckConstraint("role IN ('user', 'admin')"))
    created_at = Column(DateTime, default=datetime.utcnow)
    last_login = Column(DateTime)
```

**Key Features**:
- Email-based authentication with unique constraints
- Role-based access control (user/admin)
- Login tracking for audit purposes

## Relationships and Constraints

### Primary Relationships

1. **Driver ↔ Team**: Many-to-one (driver belongs to one team)
2. **Race ↔ Circuit**: Many-to-one (race held at one circuit)
3. **RaceResult ↔ Race/Driver/Team**: Many-to-one relationships
4. **Prediction ↔ Race/Driver**: Many-to-one relationships

### Key Constraints

1. **Unique Constraints**:
   - (season_year, round_number) in races
   - (race_id, driver_id) in race_results and qualifying_results
   - (race_id, driver_id, model_version) in predictions

2. **Check Constraints**:
   - Track type validation (street/permanent)
   - Race status validation (scheduled/completed/cancelled)
   - Prediction probability range (0-100%)
   - User role validation (user/admin)

3. **Foreign Key Constraints**:
   - All relationships maintain referential integrity
   - Cascading deletes where appropriate

## Performance Optimizations

### Indexes

- Primary keys (automatic)
- Foreign keys for join performance
- Frequently queried columns (driver_code, race_date, status)
- ELO ratings for ranking queries
- Prediction timestamps for time-based queries

### Materialized Views

- `driver_rankings`: Pre-calculated driver statistics for performance

### Partitioning Strategy

- Future implementation: Partition race_results and predictions by season_year
- Archive old seasons to separate storage for cost optimization

## Usage Examples

### Creating a New Driver

```python
driver = Driver(
    driver_code="RUS",
    driver_name="George Russell",
    nationality="British",
    date_of_birth=date(1998, 2, 15),
    current_elo_rating=1750
)
db.add(driver)
db.commit()
```

### Creating a Prediction

```python
prediction = Prediction(
    race_id=123,
    driver_id=45,
    predicted_win_probability=Decimal("28.5"),
    model_version="v1.2.0"
)
db.add(prediction)
db.commit()
```

### Querying Driver Rankings

```python
top_drivers = db.query(Driver).order_by(
    Driver.current_elo_rating.desc()
).limit(10).all()
```

## Migration and Deployment

### Initial Schema Creation

Use the migration script to create the complete schema:

```python
from api.migrations.001_initial_schema import create_initial_schema
create_initial_schema()
```

### Schema Evolution

Future schema changes should:
1. Use Alembic for version-controlled migrations
2. Maintain backward compatibility where possible
3. Include data migration scripts for structural changes
4. Test thoroughly in staging environment

This database design provides a solid foundation for the F1 Prediction Analytics system, with room for future enhancements and optimizations.