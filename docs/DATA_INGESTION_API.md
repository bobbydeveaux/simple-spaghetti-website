# F1 Analytics Data Ingestion API

This document describes the data ingestion system for the F1 Prediction Analytics platform, including API clients for external data sources and the ETL pipeline for processing F1 data.

## Overview

The data ingestion system provides comprehensive integration with external APIs to collect Formula 1 data and weather information:

- **Ergast F1 API**: Historical and current F1 race data, results, standings
- **OpenWeatherMap API**: Weather data for race circuits
- **Data Transformation**: Validation and normalization of external data
- **Database Integration**: Storing processed data in PostgreSQL

## Architecture

```
External APIs → API Clients → Data Transformer → Database
     ↓               ↓              ↓              ↓
  Ergast API    ErgastClient    DataTransformer  PostgreSQL
  Weather API   WeatherClient        ↓          F1 Models
                     ↓         Pydantic Schemas      ↓
              Data Ingestion                   Repositories
                 Service
```

## API Clients

### ErgastClient

Provides async access to the Ergast Developer API for F1 data.

**Configuration:**
```python
F1_ERGAST_BASE_URL=https://ergast.com/api/f1
F1_ERGAST_TIMEOUT=30
F1_ERGAST_RETRY_ATTEMPTS=3
```

**Key Methods:**
- `fetch_race_results(season, round)` - Get race results
- `fetch_qualifying_results(season, round)` - Get qualifying times
- `fetch_driver_standings(season)` - Get championship standings
- `fetch_constructor_standings(season)` - Get team standings
- `fetch_race_schedule(season)` - Get race calendar
- `fetch_circuits()` - Get circuit information
- `fetch_drivers()` - Get driver information
- `fetch_lap_times(season, round, lap)` - Get detailed lap times

**Usage Example:**
```python
async with ErgastClient() as client:
    # Get 2023 Bahrain GP results
    results = await client.fetch_race_results(2023, 1)

    # Get current season standings
    standings = await client.fetch_driver_standings(2023)

    # Health check
    health = await client.health_check()
```

**Error Handling:**
- Automatic retry with exponential backoff (3 attempts)
- Rate limiting compliance (1 request per minute for updates)
- Comprehensive error logging
- Raises `ErgastAPIError` on failures

### WeatherClient

Provides async access to OpenWeatherMap API for weather data.

**Configuration:**
```python
F1_WEATHER_API_KEY=your_openweathermap_api_key
F1_WEATHER_BASE_URL=https://api.openweathermap.org/data/2.5
```

**Key Methods:**
- `get_current_weather(lat, lon)` - Current weather at coordinates
- `get_forecast(lat, lon)` - 5-day weather forecast
- `get_historical_weather(lat, lon, date)` - Historical weather (paid tier)
- `get_weather_for_circuit(circuit_id, race_date)` - F1 circuit weather
- `get_weather_summary(circuit_id, race_date)` - Simplified weather data

**Circuit Coordinates:**
Built-in coordinate mapping for all F1 circuits:
```python
circuits = CircuitCoordinates.get_all_circuits()
coords = CircuitCoordinates.get_coordinates('monaco')  # (43.7347, 7.4197)
```

**Usage Example:**
```python
async with WeatherClient() as client:
    # Get weather for Monaco GP
    weather = await client.get_weather_for_circuit('monaco', date(2023, 5, 28))

    # Get simplified summary
    summary = await client.get_weather_summary('monaco', date(2023, 5, 28))
```

**Weather Data Types:**
- **Current**: Real-time weather for race day
- **Forecast**: Up to 5 days ahead for upcoming races
- **Historical**: Past weather data (requires paid subscription)

## Data Transformation

### DataTransformer

Converts external API data to validated database schemas.

**Transformation Methods:**
- `transform_driver_from_ergast()` - Driver data → DriverCreate
- `transform_constructor_from_ergast()` - Constructor → TeamCreate
- `transform_circuit_from_ergast()` - Circuit data → CircuitCreate
- `transform_race_from_ergast()` - Race data → RaceCreate
- `transform_race_result_from_ergast()` - Result → RaceResultCreate
- `transform_qualifying_result_from_ergast()` - Qualifying → QualifyingResultCreate
- `transform_weather_from_openweather()` - Weather → WeatherDataCreate

**Data Validation:**
- Pydantic schema validation for all transformed data
- Driver code generation and normalization
- Lap time format conversion (MM:SS.mmm → seconds)
- Weather condition classification (dry/wet/mixed)
- Team color mapping for known constructors

**Usage Example:**
```python
transformer = DataTransformer()

# Transform Ergast driver data
driver_data = {...}  # From Ergast API
driver_create = transformer.transform_driver_from_ergast(driver_data)

# Validate and normalize driver name
normalized_name = transformer.normalize_driver_name("Hamilton, Lewis")
# Result: "Lewis Hamilton"

# Convert lap time to seconds
lap_seconds = transformer.convert_lap_time("1:23.456")
# Result: 83.456
```

## Data Ingestion Service

### F1DataIngestionService

Orchestrates the complete ETL pipeline from external APIs to database.

**Main Methods:**
- `ingest_season_data(season)` - Complete season ingestion
- `ingest_race_results(season, round)` - Single race results
- `ingest_qualifying_results(season, round)` - Single qualifying session
- `ingest_weather_data(season, round, circuit_id)` - Weather for race

**Usage Example:**
```python
async with F1DataIngestionService() as ingestion:
    # Ingest complete 2023 season
    stats = await ingestion.ingest_season_data(2023, include_weather=True)

    # Ingest specific race
    race_stats = await ingestion.ingest_race_results(2023, 1)

    # Health check all components
    health = await ingestion.health_check()
```

**Ingestion Statistics:**
```python
{
    'season': 2023,
    'drivers_created': 20,
    'teams_created': 10,
    'circuits_created': 23,
    'races_created': 23,
    'race_results_created': 460,
    'qualifying_results_created': 460,
    'weather_records_created': 23,
    'duration_seconds': 125.5,
    'errors': []
}
```

## Database Schema Integration

### Supported Models

The ingestion system integrates with the following F1 database models:

- **Driver**: F1 drivers with codes, names, teams, ELO ratings
- **Team**: Constructor teams with nationalities, colors, ELO ratings
- **Circuit**: Race circuits with locations, track types, lengths
- **Race**: Grand Prix races with dates, circuits, status
- **RaceResult**: Finishing positions, points, lap times, status
- **QualifyingResult**: Q1/Q2/Q3 times, grid positions
- **WeatherData**: Temperature, precipitation, wind, conditions

### Repository Integration

Uses specialized repositories for database operations:
```python
repos = {
    'driver': DriverRepository(session),
    'team': TeamRepository(session),
    'circuit': CircuitRepository(session),
    'race': RaceRepository(session),
    'race_result': RaceResultRepository(session),
    'qualifying': QualifyingResultRepository(session),
    'weather': WeatherDataRepository(session)
}
```

## Error Handling & Reliability

### Retry Logic
- **Exponential backoff**: 1s, 2s, 4s delays between retries
- **Maximum attempts**: 3 retries for both APIs
- **Timeout handling**: 30-second request timeouts
- **Rate limit compliance**: Respects API rate limits

### Error Recovery
- **Graceful degradation**: Continues processing on partial failures
- **Detailed logging**: Comprehensive error tracking and context
- **Health checks**: Regular API availability monitoring
- **Fallback mechanisms**: Cached data when APIs unavailable

### Data Integrity
- **Transaction management**: Atomic database operations
- **Validation**: Pydantic schema validation for all data
- **Deduplication**: Prevents duplicate records
- **Consistency**: Foreign key relationships maintained

## Configuration

### Environment Variables

```bash
# Ergast API Configuration
F1_ERGAST_BASE_URL=https://ergast.com/api/f1
F1_ERGAST_TIMEOUT=30
F1_ERGAST_RETRY_ATTEMPTS=3

# Weather API Configuration
F1_WEATHER_API_KEY=your_openweathermap_api_key
F1_WEATHER_BASE_URL=https://api.openweathermap.org/data/2.5

# Database Configuration
F1_DB_HOST=localhost
F1_DB_PORT=5432
F1_DB_NAME=f1_analytics
F1_DB_USER=f1_user
F1_DB_PASSWORD=f1_password
```

### Rate Limits
- **Ergast API**: No official limit, respectful use (1 req/minute for updates)
- **OpenWeatherMap**: 1,000 calls/day (free tier), paid tiers available
- **Historical Weather**: Requires paid OpenWeatherMap subscription

## Testing

### Unit Tests
Comprehensive test coverage for all components:
- `test_ergast_client.py`: 40+ test cases for ErgastClient
- `test_weather_client.py`: 35+ test cases for WeatherClient
- `test_data_transformer.py`: 30+ test cases for DataTransformer

### Test Features
- **Mock external APIs**: No real API calls in tests
- **Edge case coverage**: Invalid data, network errors, timeouts
- **Async testing**: Proper async/await test patterns
- **Realistic fixtures**: Sample data from actual API responses

### Running Tests
```bash
# Run all data ingestion tests
pytest tests/unit/test_*client.py tests/unit/test_data_transformer.py -v

# Run with coverage
pytest --cov=app.services tests/unit/ --cov-report=html
```

## Performance Considerations

### Batch Processing
- **Season ingestion**: Processes all races in sequence
- **Bulk operations**: Efficient database batch inserts
- **Memory management**: Streams large datasets without loading fully

### Optimization
- **Connection pooling**: Reuses HTTP connections for multiple requests
- **Database sessions**: Batched commits for efficiency
- **Async operations**: Non-blocking I/O for better throughput

### Monitoring
- **Ingestion metrics**: Track processing times and success rates
- **Error tracking**: Comprehensive logging for debugging
- **Health checks**: Regular system component validation

## Deployment

### Dependencies
```bash
# HTTP clients
httpx>=0.25.2
requests>=2.31.0

# Retry logic
tenacity>=8.2.3

# Data validation
pydantic>=2.4.0

# Database
sqlalchemy>=2.0.0
psycopg2-binary>=2.9.7
```

### Kubernetes Resources
The ingestion service integrates with the existing Kubernetes deployment:
- **Secrets**: API keys stored in Kubernetes secrets
- **ConfigMaps**: Non-sensitive configuration
- **CronJobs**: Scheduled data ingestion tasks
- **Monitoring**: Prometheus metrics and alerting

## API Reference

### ErgastClient Methods

| Method | Parameters | Returns | Description |
|--------|------------|---------|-------------|
| `fetch_race_results` | season, round | Dict | Race finishing positions and points |
| `fetch_qualifying_results` | season, round | Dict | Qualifying session times |
| `fetch_driver_standings` | season, round? | Dict | Driver championship standings |
| `fetch_constructor_standings` | season, round? | Dict | Constructor standings |
| `fetch_race_schedule` | season | Dict | Complete race calendar |
| `fetch_circuits` | season? | Dict | Circuit information |
| `fetch_drivers` | season? | Dict | Driver information |
| `fetch_constructors` | season? | Dict | Constructor information |
| `fetch_lap_times` | season, round, lap? | Dict | Detailed lap timing data |
| `health_check` | - | Dict | API availability status |

### WeatherClient Methods

| Method | Parameters | Returns | Description |
|--------|------------|---------|-------------|
| `get_current_weather` | lat, lon, lang? | Dict | Current weather conditions |
| `get_forecast` | lat, lon, lang? | Dict | 5-day weather forecast |
| `get_historical_weather` | lat, lon, date | Dict | Historical weather data |
| `get_weather_for_circuit` | circuit_id, race_date | Dict | Circuit-specific weather |
| `get_weather_summary` | circuit_id, race_date | Dict | Simplified weather data |
| `health_check` | - | Dict | API and key validation |

### DataTransformer Methods

| Method | Parameters | Returns | Description |
|--------|------------|---------|-------------|
| `transform_driver_from_ergast` | driver_data | DriverCreate | Driver transformation |
| `transform_constructor_from_ergast` | constructor_data | TeamCreate | Team transformation |
| `transform_circuit_from_ergast` | circuit_data | CircuitCreate | Circuit transformation |
| `transform_race_from_ergast` | race_data, season | RaceCreate | Race transformation |
| `transform_race_result_from_ergast` | result_data, race_id | RaceResultCreate | Result transformation |
| `transform_qualifying_result_from_ergast` | quali_data, race_id | QualifyingResultCreate | Qualifying transformation |
| `transform_weather_from_openweather` | weather_data, race_id | WeatherDataCreate | Weather transformation |
| `normalize_driver_name` | driver_name | str | Name standardization |
| `convert_lap_time` | lap_time_str | float? | Time format conversion |

## Security Considerations

### API Key Management
- **Environment variables**: Store API keys in environment variables
- **Kubernetes secrets**: Use secrets for production deployments
- **Key rotation**: Regularly rotate OpenWeatherMap API keys
- **Access logging**: Monitor API key usage and requests

### Network Security
- **HTTPS only**: All external API calls use HTTPS
- **Connection validation**: SSL certificate verification enabled
- **Rate limiting**: Respect API provider rate limits
- **Timeout handling**: Prevent hanging connections

### Data Security
- **Input validation**: All external data validated with Pydantic
- **SQL injection protection**: Use parameterized queries
- **Error handling**: Sanitize error messages in logs
- **Access control**: Database access through repository pattern

## Troubleshooting

### Common Issues

**Ergast API Timeouts**
```
ErgastAPIError: Request error: Timeout
```
- Solution: Increase `F1_ERGAST_TIMEOUT` value
- Check network connectivity to ergast.com

**Weather API Unauthorized**
```
WeatherAPIError: HTTP error 401: Invalid API key
```
- Solution: Verify `F1_WEATHER_API_KEY` is correct
- Check OpenWeatherMap account status

**Historical Weather Not Available**
```
WeatherAPIError: Historical weather data requires paid subscription
```
- Solution: Upgrade to paid OpenWeatherMap plan
- Use forecast/current data only for free tier

**Database Connection Errors**
```
DataIngestionError: Database connection failed
```
- Solution: Check database connectivity and credentials
- Verify database is running and accessible

### Health Check Endpoints

Use health checks to diagnose system status:
```python
# Check all components
health = await ingestion_service.health_check()

# Individual component checks
ergast_health = await ergast_client.health_check()
weather_health = await weather_client.health_check()
```

### Logging

Enable debug logging for detailed troubleshooting:
```python
import logging
logging.getLogger('app.services').setLevel(logging.DEBUG)
```

## Future Enhancements

### Planned Features
- **Real-time ingestion**: Live timing data during races
- **Additional APIs**: Integration with F1 official timing API
- **Caching layer**: Redis caching for frequently accessed data
- **Event streaming**: Kafka/RabbitMQ for real-time updates
- **ML integration**: Direct feature engineering for predictions

### Scalability
- **Horizontal scaling**: Multiple ingestion workers
- **Async processing**: Queue-based background jobs
- **Database sharding**: Partition data by season/circuit
- **CDN integration**: Cache static reference data

---

For more information, see the [F1 Analytics LLD](./concepts/f1-prediction-analytics/LLD.md) and [Database Schema Documentation](./f1-analytics-database-schema.md).