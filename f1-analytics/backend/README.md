# F1 Prediction Analytics - Backend

A comprehensive backend system for Formula 1 race prediction analytics, built with FastAPI, PostgreSQL, and Redis.

## Features

### Database & Session Management
- **PostgreSQL Integration**: Full database support with connection pooling and health monitoring
- **Redis Sessions**: User session management with TTL and rate limiting
- **SQLAlchemy ORM**: Complete F1 data models with relationships and constraints
- **Alembic Migrations**: Database schema versioning and migration system

### Authentication & Security
- **JWT Authentication**: Access and refresh token support with configurable expiration
- **Rate Limiting**: Per-user rate limiting (100 requests/minute by default)
- **Session Management**: Redis-backed user sessions with automatic cleanup
- **Secure Defaults**: Bcrypt password hashing, secure JWT configuration

### Data Models
- **Drivers**: Driver profiles, ELO ratings, team associations
- **Teams**: Constructor information and performance ratings
- **Circuits**: Track details and race locations
- **Races**: Season calendar with race metadata
- **Results**: Race and qualifying results with detailed statistics
- **Predictions**: ML model predictions with accuracy tracking
- **Weather**: Race day conditions affecting predictions

### Repository Pattern
- **Base Repository**: Generic CRUD operations for all models
- **Specialized Repositories**: Domain-specific methods for F1 data
- **Async Support**: Both sync and async database operations
- **Bulk Operations**: Efficient batch processing for large datasets

## Quick Start

### Requirements
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

## Project Structure

```
f1-analytics/backend/
├── alembic/                    # Database migrations
│   ├── env.py                  # Alembic environment configuration
│   └── versions/               # Migration scripts
├── app/                        # Main application code
│   ├── config.py              # Configuration management
│   ├── database.py            # Database connection and session management
│   ├── dependencies.py        # FastAPI dependency injection
│   ├── models/                # SQLAlchemy ORM models
│   │   ├── user.py            # User authentication model
│   │   └── f1_models.py       # F1 domain models
│   ├── repositories/          # Data access layer
│   │   ├── base.py            # Base repository with CRUD operations
│   │   ├── user_repository.py # User-specific database operations
│   │   └── f1_repositories.py # F1-specific database operations
│   └── utils/                 # Utility modules
│       ├── jwt_manager.py     # JWT token management
│       └── session_manager.py # Redis session management
├── tests/                     # Test suite
│   ├── conftest.py           # Test configuration and fixtures
│   ├── test_database.py      # Database functionality tests
│   └── test_session_management.py # Session and JWT tests
├── alembic.ini               # Alembic configuration
├── requirements.txt          # Python dependencies
└── README.md                 # This file
```

## Database Models

### Core F1 Models
- **Driver**: F1 drivers with ELO ratings and team associations
- **Team**: Constructors with performance metrics
- **Circuit**: Race tracks with technical specifications
- **Race**: Season calendar with race scheduling
- **RaceResult**: Race finishing positions and points
- **QualifyingResult**: Grid positions from qualifying sessions
- **WeatherData**: Race day weather conditions
- **Prediction**: ML model predictions for race outcomes
- **PredictionAccuracy**: Model performance tracking

### Relationships
- Drivers belong to Teams
- Races occur at Circuits
- Results link Races, Drivers, and Teams
- Predictions connect Races and Drivers
- Weather data is associated with specific Races

## Configuration

The application uses environment-based configuration with sensible defaults:

### Database Configuration
- Connection pooling with configurable pool size
- Health check endpoints for monitoring
- Automatic connection retry with exponential backoff
- SSL support for production deployments

### Redis Configuration
- Separate cache TTLs for different data types
- Connection pooling for high concurrency
- Failover support with graceful degradation

### JWT Configuration
- Configurable token expiration times
- Support for additional custom claims
- Automatic token refresh mechanism
- Secure default algorithms and key sizes

## Testing

The project includes comprehensive tests covering:

### Database Tests
- Connection management and pooling
- CRUD operations and transactions
- Model relationships and constraints
- Performance and optimization

### Session Management Tests
- JWT token creation and validation
- Redis session storage and retrieval
- Rate limiting functionality
- Cache operations

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
```

## Health Checks

The application provides health check endpoints:

- **Database Health**: `/health/database` - PostgreSQL connection status
- **Redis Health**: `/health/redis` - Redis connectivity and memory usage
- **Overall Health**: `/health` - Combined system health status

## Performance Considerations

### Database Optimization
- Proper indexing on frequently queried columns
- Connection pooling with configurable limits
- Query optimization with eager loading for relationships
- Bulk operations for large data imports

### Caching Strategy
- Prediction results cached for 7 days
- Race calendar cached for 24 hours
- Driver rankings cached for 1 hour
- Automatic cache invalidation on data updates

### Rate Limiting
- Per-user request limits to prevent abuse
- Redis-backed counters with automatic expiration
- Graceful handling of rate limit exceeded scenarios

## Security Features

### Authentication
- JWT-based stateless authentication
- Secure password hashing with bcrypt
- Token expiration and refresh mechanisms
- Role-based access control support

### Data Protection
- Input validation and sanitization
- SQL injection prevention through ORM
- Secure session management with Redis
- Environment-based configuration for secrets

## Development Guidelines

### Code Style
- Black for code formatting
- isort for import organization
- flake8 for linting
- mypy for type checking

### Testing Standards
- Minimum 80% code coverage
- Unit tests for all business logic
- Integration tests for database operations
- Mocked external dependencies

### Documentation
- Comprehensive docstrings for all functions
- Type hints for all function parameters
- README files for each major module
- API documentation with FastAPI/OpenAPI

## Future Enhancements

### Planned Features
- ML model training integration
- External API data ingestion (Ergast F1 API)
- Real-time prediction updates
- Advanced analytics and reporting
- API rate limiting per endpoint
- Audit logging for all operations

### Scalability Improvements
- Read replica support for database queries
- Redis cluster configuration
- Horizontal scaling with load balancing
- Metrics and monitoring integration

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes with tests
4. Ensure all tests pass
5. Update documentation as needed
6. Submit a pull request

## License

This project is part of the F1 Prediction Analytics system and follows the main project's licensing terms.