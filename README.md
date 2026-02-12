# F1 Prediction Analytics System

A comprehensive Formula One prediction analytics platform with SQLAlchemy database models and machine learning capabilities.

## Features

- **F1 Data Models**: Complete SQLAlchemy ORM models for drivers, teams, circuits, races, and predictions
- **Authentication System**: JWT-based user authentication with role-based access
- **Prediction Engine**: ML-powered race winner predictions using ensemble models
- **Analytics Dashboard**: Track prediction accuracy and driver/team rankings
- **Data Ingestion**: Automated data collection from Ergast API and weather services

## Database Models

### Core F1 Models
- `Driver`: F1 drivers with ELO ratings and team associations
- `Team`: Constructor teams with performance metrics
- `Circuit`: Race circuits with technical specifications
- `Race`: Individual races with scheduling and status
- `RaceResult`: Race finish positions and points
- `QualifyingResult`: Qualifying session results
- `WeatherData`: Weather conditions for each race

### Prediction Models
- `Prediction`: ML-generated win probability predictions
- `PredictionAccuracy`: Model performance tracking and metrics

### Authentication
- `User`: User accounts with role-based permissions

## Quick Start

1. **Install Dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

2. **Set Environment Variables**:
   ```bash
   export DATABASE_URL="postgresql://user:pass@localhost:5432/f1_analytics"
   export JWT_SECRET_KEY="your-secret-key"
   ```

3. **Initialize Database**:
   ```python
   from api.migrations.001_initial_schema import create_initial_schema
   create_initial_schema()
   ```

4. **Run Tests**:
   ```bash
   python test_f1_models.py
   ```

## Architecture

The system follows a layered architecture:
- **Models Layer**: SQLAlchemy ORM models with relationships
- **Database Layer**: PostgreSQL with connection pooling
- **API Layer**: FastAPI REST endpoints
- **ML Layer**: Scikit-learn and XGBoost models
- **Cache Layer**: Redis for performance optimization

## Configuration

Key configuration settings in `api/config.py`:
- Database connection settings
- JWT authentication parameters
- External API endpoints (Ergast, Weather)
- ML model configuration
- Rate limiting settings

## Database Schema

The database includes:
- Normalized F1 data structure
- Optimized indexes for performance
- Materialized views for complex queries
- Foreign key constraints for data integrity
- Check constraints for data validation

## Development

The models are designed for:
- **Scalability**: Horizontal scaling with stateless design
- **Performance**: Optimized queries and caching
- **Maintainability**: Clear separation of concerns
- **Extensibility**: Easy addition of new features

## Testing

Comprehensive test suite includes:
- Model creation and validation
- Database connection testing
- Relationship verification
- Integration tests

For detailed technical specifications, see `docs/concepts/f1-prediction-analytics/`.
