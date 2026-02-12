# 🏎️ F1 Prediction Analytics Platform

A comprehensive Formula One prediction analytics platform with Docker containerization for seamless development and deployment, combined with advanced ML-powered race predictions and database infrastructure.

## 🚀 Quick Start

### Prerequisites

- Docker (>= 20.10)
- Docker Compose (>= 2.0)
- Git
- 8GB+ RAM recommended

### One-Command Setup

```bash
./scripts/init_dev.sh
```

This will:
- Build all Docker containers
- Start the complete development environment
- Initialize the database with sample data
- Verify all services are running

### Access Points

Once setup is complete, access the application at:

- **Frontend Dashboard**: http://localhost:3000
- **Backend API**: http://localhost:8000
- **API Documentation**: http://localhost:8000/docs
- **Task Monitor (Flower)**: http://localhost:5555
- **Database**: localhost:5432
- **Redis**: localhost:6379

## 📊 Architecture Overview

### System Architecture

```mermaid
graph TB
    subgraph "Frontend Layer"
        F[React Dashboard<br/>Port: 3000]
    end

    subgraph "API Gateway"
        B[FastAPI Backend<br/>Port: 8000]
    end

    subgraph "Background Processing"
        CW[Celery Worker]
        CB[Celery Beat]
        FL[Flower Monitor<br/>Port: 5555]
    end

    subgraph "Data Layer"
        P[PostgreSQL<br/>Port: 5432]
        R[Redis<br/>Port: 6379]
    end

    subgraph "External APIs"
        E1[Ergast F1 API]
        E2[Weather API]
    end

    F --> B
    B --> P
    B --> R
    CW --> P
    CW --> R
    CB --> CW
    CW --> E1
    CW --> E2
    FL --> R
```

### Database Schema

The system uses PostgreSQL with comprehensive F1 data modeling:

#### Core Entities
- **Teams**: F1 constructors with Elo ratings and performance tracking
- **Drivers**: F1 drivers with team associations and detailed statistics
- **Circuits**: Race tracks with characteristics (length, type, location)
- **Races**: Race events with season/round information and status

#### Results & Performance
- **RaceResults**: Final race positions, points, and performance data (partitioned by race_id)
- **QualifyingResults**: Qualifying session times and grid positions
- **WeatherData**: Race weather conditions affecting performance

#### Predictions & Analysis
- **Predictions**: ML-generated win probabilities by model version (partitioned by race_id)
- **PredictionAccuracy**: Post-race accuracy metrics (Brier score, log loss)
- **Users**: Authentication and role-based access control

### Key Database Features

- **Comprehensive Constraints**: Check constraints for data validation
- **Performance Indexes**: Optimized queries for race data and predictions
- **Materialized Views**: Driver rankings for fast leaderboard queries
- **Table Partitioning**: Ready for partitioning race_results and predictions by race_id
- **Foreign Key Relationships**: Proper referential integrity across entities

## 🔧 Data Transformation & Validation Layer

The F1 Analytics platform features a sophisticated data transformation and validation layer that ensures data quality, consistency, and proper format conversion across the entire application.

### 📊 Pydantic Schema Validation

Comprehensive request/response validation using Pydantic schemas with F1-specific business rules:

```python
from app.schemas import DriverCreate, RaceCreate, PredictionCreate

# Driver validation with business rules
driver_data = DriverCreate(
    driver_code="VER",           # Must be 3 uppercase letters
    driver_name="Max Verstappen", # Normalized automatically
    nationality="Dutch",
    date_of_birth="1997-09-30",  # Must be in past
    current_elo_rating=2100      # Range: 800-3000
)

# Race validation with season consistency
race_data = RaceCreate(
    season_year=2024,
    round_number=1,              # Unique per season
    race_name="Bahrain Grand Prix",
    race_date="2024-03-01",     # Must match season year
    circuit_id=1
)

# Prediction validation with probability checks
prediction_data = PredictionCreate(
    race_id=1,
    driver_id=1,
    predicted_win_probability=25.5,  # Range: 0-100
    model_version="v1.2.3"
)
```

### 🛠️ Service Layer with Business Logic

Advanced service classes handle complex business operations with automatic validation:

```python
from app.services import driver_service, race_service, prediction_service

# Driver operations with validation
driver = driver_service.create_driver(db, driver_data)
rankings = driver_service.get_drivers_rankings(db, season=2024, limit=20)
stats = driver_service.get_driver_statistics(db, driver_id=1, season=2024)

# Race operations with result processing
race = race_service.create_race(db, race_data)
weekend_summary = race_service.get_race_weekend_summary(db, race_id=1)
calendar = race_service.get_race_calendar(db, season=2024)

# Prediction operations with ML model integration
predictions = prediction_service.create_prediction(db, prediction_data)
race_predictions = prediction_service.get_race_predictions(db, race_id=1)
accuracy = prediction_service.update_prediction_accuracy(db, race_id=1)
```

### 🔍 Advanced Validation Decorators

Sophisticated validation decorators for API endpoints and business logic:

```python
from app.utils.validators import (
    validate_request_data, validate_database_constraints,
    validate_business_rules, handle_service_errors
)

@validate_request_data(DriverCreate)
@validate_database_constraints(
    unique_fields=["driver_code"],
    foreign_keys={"current_team_id": Team}
)
@validate_business_rules(
    lambda db, data: validate_driver_team_consistency(db, data)
)
@handle_service_errors
def create_driver_endpoint(db: Session, data: dict):
    return driver_service.create_driver(db, data)
```

### 🔄 Data Transformation Utilities

Comprehensive data transformation with F1-specific calculations:

```python
from app.utils.transformers import F1DataTransformer, TransformationConfig

# Configure transformer behavior
config = TransformationConfig(
    include_metadata=True,
    include_relationships=True,
    include_calculated_fields=True,
    datetime_format="iso",
    decimal_places=2
)

transformer = F1DataTransformer(config)

# Transform driver data with enrichment
driver_api_data = transformer.transform_driver_for_api(
    driver,
    include_stats=True,
    season=2024
)
# Result includes: age, experience_level, elo_category, performance_metrics

# Transform predictions with analysis
prediction_summary = transformer.transform_prediction_summary(
    predictions, race
)
# Result includes: statistics, competitiveness_score, entropy, probability_distribution

# Transform race results with context
result_data = transformer.transform_race_result_with_context(
    race_result,
    include_performance_metrics=True
)
# Result includes: position_change_category, performance_rating, points_efficiency
```

### 📈 F1-Specific Validation Rules

Business rule validators designed specifically for Formula 1 data:

```python
from app.utils.validators import F1DataValidator

# Race season consistency
F1DataValidator.validate_race_season_consistency(db, {
    "race_date": date(2024, 3, 1),
    "season_year": 2024
})

# Driver-team relationship validation
F1DataValidator.validate_driver_team_consistency(db, {
    "driver_id": 1,
    "team_id": 1
})

# Prediction probability validation for entire race
F1DataValidator.validate_prediction_probabilities(db, race_id=1)

# Race result data consistency
F1DataValidator.validate_race_result_consistency(db, {
    "final_position": 1,
    "grid_position": 3,
    "points": 25.0
})

# Qualifying session progression
F1DataValidator.validate_qualifying_progression(db, {
    "q1_time": "1:23.456",
    "q2_time": "1:22.789",
    "q3_time": "1:21.123",
    "final_grid_position": 5
})
```

### 🧮 Advanced Data Calculations

Sophisticated F1-specific calculations and metrics:

```python
from app.services.base import DataTransformer

# Lap time format conversion
lap_time = DataTransformer.format_lap_time(83.456)  # "1:23.456"
seconds = DataTransformer.parse_lap_time("1:23.456")  # 83.456

# Points calculation based on F1 rules
points = DataTransformer.calculate_points_from_position(1)  # 25.0

# Driver name normalization
normalized = DataTransformer.normalize_driver_name("max verstappen")  # "Max Verstappen"

# Safe mathematical operations
rate = DataTransformer.safe_divide(wins, total_races, default=0.0)
percentage = DataTransformer.format_percentage(0.235, decimals=1)  # "23.5%"
```

### ⚡ Performance Optimizations

The validation layer includes several performance optimizations:

- **Lazy Loading**: Relationships loaded only when needed
- **Batch Operations**: Bulk validation for large datasets
- **Caching**: Validation results cached for repeated operations
- **Efficient Queries**: Optimized database queries with proper indexing
- **Pagination**: Built-in pagination support for large result sets

### 🧪 Comprehensive Testing

The validation layer includes extensive test coverage:

```python
# Run validation layer tests
pytest tests/test_validation_layer.py -v

# Test categories:
# - Pydantic schema validation with edge cases
# - Data validator functions with invalid inputs
# - F1-specific business rule validation
# - Service layer validation and error handling
# - Integration scenarios and error propagation
# - Performance testing for large datasets
```

### 🛡️ Error Handling

Sophisticated error handling with detailed context:

```python
from app.services.base import ValidationError, DataTransformationError

try:
    driver = driver_service.create_driver(db, invalid_data)
except ValidationError as e:
    # Contains: message, field, value for precise error reporting
    return {
        "error": "Validation Error",
        "message": e.message,
        "field": e.field,
        "value": e.value
    }
except DataTransformationError as e:
    # Contains context for transformation failures
    return {
        "error": "Data Transformation Error",
        "message": e.message,
        "context": e.field
    }
```

# Application
ENVIRONMENT=development
DEBUG=true
LOG_LEVEL=INFO
```

**Frontend:**
```env
VITE_API_URL=http://localhost:8000
VITE_APP_NAME=F1 Analytics Dashboard
VITE_ENVIRONMENT=development
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

## 🚀 Production Deployment

### 🔒 Production Security Checklist

**⚠️ CRITICAL**: Read `PRODUCTION_SECURITY.md` before production deployment!

```bash
# 1. Generate secure credentials
./scripts/generate_secrets.sh

# 2. Create production environment
cp .env.production.template .env.production
# Edit with your secure values

# 3. Validate security configuration
python -c "from app.core.config import get_settings, validate_production_config; s = get_settings(); print(validate_production_config(s))"

# 4. Deploy with production compose
docker-compose -f infrastructure/docker-compose.prod.yml up -d
```

### Production Environment Variables

**🔐 Security Requirements:**
- JWT secret minimum 64 characters (use `openssl rand -base64 64`)
- Database passwords minimum 16 characters
- No localhost/development URLs in production
- HTTPS-only CORS origins
- Debug mode disabled (`DEBUG=false`)

```env
# Database (SECURE PASSWORDS REQUIRED)
POSTGRES_DB=f1_analytics_prod
POSTGRES_USER=f1user_prod
POSTGRES_PASSWORD=GENERATE_SECURE_PASSWORD_MIN_16_CHARS

# Redis (SECURE PASSWORDS REQUIRED)
REDIS_PASSWORD=GENERATE_SECURE_REDIS_PASSWORD_MIN_16_CHARS

# JWT (GENERATE WITH: openssl rand -base64 64)
JWT_SECRET_KEY=CRYPTOGRAPHICALLY_SECURE_64_CHARACTER_MINIMUM

# Security Configuration
CORS_ORIGINS=https://yourdomain.com,https://www.yourdomain.com
ALLOWED_HOSTS=yourdomain.com,www.yourdomain.com
ENVIRONMENT=production
DEBUG=false

# Rate Limiting
RATE_LIMIT_PER_MINUTE=30
RATE_LIMIT_BURST=60

# External APIs
WEATHER_API_KEY=your-production-weather-api-key

# Monitoring
GRAFANA_ADMIN_PASSWORD=SECURE_GRAFANA_PASSWORD
ENABLE_METRICS=true

# Connection Pool
DATABASE_POOL_SIZE=10
DATABASE_MAX_OVERFLOW=20
DATABASE_POOL_TIMEOUT=30
DATABASE_POOL_RECYCLE=3600
```

## Dependencies

- **SQLAlchemy 2.0+**: ORM and database toolkit
- **Alembic**: Database migration management
- **psycopg2**: PostgreSQL database adapter
- **FastAPI**: Modern Python web framework for API endpoints
- **Pydantic**: Data validation and serialization
- **Redis**: Caching and session management
- **Security**: JWT authentication, bcrypt password hashing
- **Testing**: Comprehensive test suite with >80% coverage requirement

## Contributing

This is a comprehensive F1 prediction analytics system combining advanced database modeling with Docker containerization and enterprise security practices. Future development will focus on ML pipeline enhancements and advanced analytics features.
