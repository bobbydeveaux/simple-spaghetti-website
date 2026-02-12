# Low-Level Design: simple-spaghetti-repo

**Created:** 2026-02-12T22:45:01Z
**Status:** Draft

## 1. Implementation Overview

The F1 Prediction Analytics system will be implemented as a Python/Flask backend API with a React frontend dashboard. The implementation extends the existing `f1-analytics/` directory structure with new modules for:

1. **Data Ingestion Pipeline**: Celery-based async jobs fetching from Ergast API and OpenWeatherMap, storing normalized data in PostgreSQL
2. **ML Prediction Engine**: Modular scikit-learn/XGBoost models with ensemble logic, serialized as pickle files
3. **REST API Layer**: Flask endpoints serving predictions, standings, and analytics with Redis caching
4. **Dashboard SPA**: React components consuming API data with Chart.js visualizations

The implementation leverages existing SQLAlchemy models in `f1-analytics/backend/app/models/` and extends them with new tables for ELO ratings and model accuracy tracking. Alembic migrations will create the schema incrementally. The modular architecture allows independent development of data ingestion, model training, and API/frontend components.

---

## 2. File Structure

### New Files

**Backend - Data Ingestion**
- `f1-analytics/backend/app/services/ergast_client.py` - Ergast API client with retry logic
- `f1-analytics/backend/app/services/weather_client.py` - OpenWeatherMap API client
- `f1-analytics/backend/app/services/data_importer.py` - Orchestrates data imports, populates database
- `f1-analytics/backend/app/tasks/celery_app.py` - Celery application configuration
- `f1-analytics/backend/app/tasks/import_tasks.py` - Celery tasks for scheduled imports
- `f1-analytics/backend/app/tasks/training_tasks.py` - Celery tasks for model training

**Backend - ML Models**
- `f1-analytics/backend/app/ml/__init__.py` - ML module initialization
- `f1-analytics/backend/app/ml/base_model.py` - Abstract base class for prediction models
- `f1-analytics/backend/app/ml/regression_model.py` - Linear regression implementation
- `f1-analytics/backend/app/ml/random_forest_model.py` - Random Forest implementation
- `f1-analytics/backend/app/ml/xgboost_model.py` - XGBoost implementation
- `f1-analytics/backend/app/ml/elo_model.py` - ELO rating calculation
- `f1-analytics/backend/app/ml/ensemble.py` - Ensemble prediction logic
- `f1-analytics/backend/app/ml/feature_engineering.py` - Feature extraction from raw data
- `f1-analytics/backend/app/ml/model_manager.py` - Load/save trained models, version management

**Backend - API Routes**
- `f1-analytics/backend/app/routes/predictions.py` - Prediction endpoints
- `f1-analytics/backend/app/routes/standings.py` - Standings endpoints
- `f1-analytics/backend/app/routes/calendar.py` - Calendar endpoints
- `f1-analytics/backend/app/routes/analytics.py` - Analytics endpoints

**Backend - Schemas**
- `f1-analytics/backend/app/schemas/prediction_schema.py` - Marshmallow schemas for predictions
- `f1-analytics/backend/app/schemas/standings_schema.py` - Marshmallow schemas for standings
- `f1-analytics/backend/app/schemas/calendar_schema.py` - Marshmallow schemas for calendar

**Backend - Repositories**
- `f1-analytics/backend/app/repositories/prediction_repository.py` - Prediction data access
- `f1-analytics/backend/app/repositories/standings_repository.py` - Standings data access
- `f1-analytics/backend/app/repositories/race_repository.py` - Race data access

**Backend - Models (Extensions)**
- `f1-analytics/backend/app/models/elo_rating.py` - ELO rating model
- `f1-analytics/backend/app/models/model.py` - Model metadata model
- `f1-analytics/backend/app/models/constructor_standing.py` - Constructor standings model
- `f1-analytics/backend/app/models/driver_standing.py` - Driver standings model

**Backend - Utilities**
- `f1-analytics/backend/app/utils/cache.py` - Redis cache wrapper with decorators
- `f1-analytics/backend/app/utils/retry.py` - Retry decorator for API calls
- `f1-analytics/backend/app/utils/validators.py` - Input validation helpers

**Backend - Configuration**
- `f1-analytics/backend/app/core/celery_config.py` - Celery broker/backend configuration
- `f1-analytics/backend/requirements-ml.txt` - ML-specific dependencies (scikit-learn, xgboost)

**Backend - Migrations**
- `f1-analytics/backend/alembic/versions/002_add_elo_and_model_tables.py` - New tables migration
- `f1-analytics/backend/alembic/versions/003_add_standing_tables.py` - Standings tables migration

**Frontend - Components**
- `f1-analytics/frontend/src/components/PredictionTable.tsx` - Display prediction results
- `f1-analytics/frontend/src/components/ModelComparison.tsx` - Compare model predictions
- `f1-analytics/frontend/src/components/StandingsTable.tsx` - Display driver/constructor standings
- `f1-analytics/frontend/src/components/RaceCalendar.tsx` - Display race calendar
- `f1-analytics/frontend/src/components/PerformanceChart.tsx` - Chart.js wrapper for performance graphs
- `f1-analytics/frontend/src/components/AccuracyMetrics.tsx` - Display model accuracy metrics

**Frontend - Services**
- `f1-analytics/frontend/src/services/api.ts` - Axios client with interceptors
- `f1-analytics/frontend/src/services/predictions.ts` - Prediction API calls
- `f1-analytics/frontend/src/services/standings.ts` - Standings API calls
- `f1-analytics/frontend/src/services/calendar.ts` - Calendar API calls
- `f1-analytics/frontend/src/services/analytics.ts` - Analytics API calls

**Frontend - Types**
- `f1-analytics/frontend/src/types/prediction.ts` - TypeScript interfaces for predictions
- `f1-analytics/frontend/src/types/standings.ts` - TypeScript interfaces for standings
- `f1-analytics/frontend/src/types/race.ts` - TypeScript interfaces for races

**Frontend - Contexts**
- `f1-analytics/frontend/src/contexts/DashboardContext.tsx` - Global dashboard state

**Frontend - Pages**
- `f1-analytics/frontend/src/pages/Dashboard.tsx` - Main dashboard page
- `f1-analytics/frontend/src/pages/PredictionsPage.tsx` - Predictions detail page
- `f1-analytics/frontend/src/pages/AnalyticsPage.tsx` - Analytics page

**Infrastructure**
- `f1-analytics/infrastructure/docker-compose.dev.yml` - Development with Celery workers
- `f1-analytics/backend/Dockerfile.worker` - Celery worker Dockerfile
- `f1-analytics/infrastructure/kubernetes/celery-deployment.yaml` - Celery worker K8s deployment

**Scripts**
- `f1-analytics/scripts/train_models.py` - Manual model training script
- `f1-analytics/scripts/import_historical_data.py` - Backfill historical data
- `f1-analytics/scripts/generate_predictions.py` - Generate predictions for upcoming race

### Modified Files

- `f1-analytics/backend/app/main.py` - Register new routes, initialize cache, add health checks
- `f1-analytics/backend/app/config.py` - Add Ergast/Weather API keys, Redis config, Celery config
- `f1-analytics/backend/requirements.txt` - Add celery, redis, requests, scikit-learn, xgboost
- `f1-analytics/frontend/src/App.tsx` - Add routing for new pages
- `f1-analytics/frontend/package.json` - Add chart.js, axios, react-router-dom
- `f1-analytics/infrastructure/docker-compose.yml` - Add Redis and Celery worker services

---

## 3. Detailed Component Designs

### 3.1 Data Ingestion Service

**Module:** `f1-analytics/backend/app/services/ergast_client.py`

**Purpose:** Fetch F1 data from Ergast API with rate limiting and error handling.

**Key Classes:**
```python
class ErgastClient:
    def __init__(self, base_url: str, rate_limit_per_hour: int = 200)
    def get_race_schedule(self, season: int) -> List[Dict]
    def get_race_results(self, season: int, round: int) -> List[Dict]
    def get_qualifying_results(self, season: int, round: int) -> List[Dict]
    def get_driver_standings(self, season: int, round: int = None) -> List[Dict]
    def get_constructor_standings(self, season: int, round: int = None) -> List[Dict]
    def _make_request(self, endpoint: str, params: Dict) -> Dict
    def _handle_rate_limit(self) -> None
```

**Implementation Details:**
- Uses `requests` library with custom retry strategy (exponential backoff: 1s, 2s, 4s, 8s)
- Rate limiter tracks request timestamps in Redis (key: `ergast:rate_limit`, sliding window)
- Converts XML responses to JSON if necessary
- Raises `ErgastAPIError` on failures, logged with structured logging

**Module:** `f1-analytics/backend/app/services/weather_client.py`

**Purpose:** Fetch weather data from OpenWeatherMap API.

**Key Classes:**
```python
class WeatherClient:
    def __init__(self, api_key: str, base_url: str = "https://api.openweathermap.org/data/2.5")
    def get_historical_weather(self, lat: float, lon: float, date: datetime) -> Dict
    def get_forecast(self, lat: float, lon: float) -> Dict
    def _make_request(self, endpoint: str, params: Dict) -> Dict
```

**Implementation Details:**
- Converts circuit locations to lat/lon (stored in `circuits` table)
- Gracefully degrades if API fails (logs warning, continues without weather data)
- Caches weather data in Redis (TTL: 24 hours for historical, 1 hour for forecasts)

**Module:** `f1-analytics/backend/app/services/data_importer.py`

**Purpose:** Orchestrates importing data from external APIs into database.

**Key Classes:**
```python
class DataImporter:
    def __init__(self, db_session: Session, ergast_client: ErgastClient, weather_client: WeatherClient)
    def import_season_schedule(self, season: int) -> None
    def import_race_results(self, race_id: int) -> None
    def import_qualifying_results(self, race_id: int) -> None
    def import_standings(self, season: int, round: int = None) -> None
    def import_weather_data(self, race_id: int) -> None
    def backfill_historical_data(self, start_season: int, end_season: int) -> None
```

**Implementation Details:**
- Wrapped in database transactions (rollback on failure)
- Checks for duplicate data before insertion (upsert logic based on unique constraints)
- Emits Celery events: `data.imported` triggers model retraining

### 3.2 ML Prediction Engine

**Module:** `f1-analytics/backend/app/ml/base_model.py`

**Purpose:** Abstract interface for all prediction models.

**Key Classes:**
```python
class BaseModel(ABC):
    def __init__(self, model_id: str, version: str)
    
    @abstractmethod
    def train(self, features: pd.DataFrame, labels: pd.Series) -> None
    
    @abstractmethod
    def predict(self, features: pd.DataFrame) -> np.ndarray
    
    def save(self, path: str) -> None
    def load(self, path: str) -> None
    def get_feature_names(self) -> List[str]
```

**Module:** `f1-analytics/backend/app/ml/feature_engineering.py`

**Purpose:** Extract features from raw database tables.

**Key Functions:**
```python
def extract_driver_features(driver_id: int, race_id: int, db_session: Session) -> Dict:
    """
    Returns:
    {
        'recent_avg_finish': float,  # Avg finish position last 5 races
        'recent_points': int,  # Points in last 5 races
        'current_elo': float,  # Current ELO rating
        'wins_this_season': int,
        'podiums_this_season': int,
        'avg_grid_position': float,  # Avg starting position last 5 races
        'dnf_rate': float  # DNF percentage last 10 races
    }
```

```python
def extract_constructor_features(constructor_id: int, race_id: int, db_session: Session) -> Dict:
    """
    Returns:
    {
        'current_elo': float,
        'wins_this_season': int,
        'avg_points_per_race': float,
        'reliability_score': float  # 1 - DNF_rate
    }
```

```python
def extract_circuit_features(circuit_id: int, driver_id: int, db_session: Session) -> Dict:
    """
    Returns:
    {
        'driver_wins_at_circuit': int,
        'driver_avg_finish_at_circuit': float,
        'track_length_km': float,
        'turn_count': int,
        'elevation_variance': float  # Parsed from elevation_profile_json
    }
```

```python
def extract_weather_features(race_id: int, db_session: Session) -> Dict:
    """
    Returns:
    {
        'temperature_c': float,
        'precipitation_mm': float,
        'wind_speed_kmh': float,
        'is_wet': bool
    }
```

```python
def build_feature_matrix(race_id: int, db_session: Session) -> pd.DataFrame:
    """
    Combines all features for all drivers in a race.
    Rows: one per driver
    Columns: all features concatenated
    """
```

**Module:** `f1-analytics/backend/app/ml/elo_model.py`

**Purpose:** Calculate and update ELO ratings for drivers and constructors.

**Key Classes:**
```python
class EloModel(BaseModel):
    K_FACTOR = 32  # Adjustment rate
    
    def calculate_expected_score(self, rating_a: float, rating_b: float) -> float:
        """Expected win probability using logistic function"""
        return 1 / (1 + 10 ** ((rating_b - rating_a) / 400))
    
    def update_ratings(self, race_results: List[RaceResult]) -> Dict[int, float]:
        """
        Updates driver ELO ratings based on race results.
        Returns: {driver_id: new_rating}
        """
        # Pairwise comparisons: each driver vs every other driver
        # Winner gets positive adjustment, loser gets negative
        
    def predict(self, features: pd.DataFrame) -> np.ndarray:
        """
        Returns win probability based on ELO ratings.
        Probability = current_elo / sum(all_elos_in_race)
        """
```

**Module:** `f1-analytics/backend/app/ml/regression_model.py`

**Purpose:** Linear regression baseline model.

**Key Classes:**
```python
class RegressionModel(BaseModel):
    def __init__(self):
        self.model = LinearRegression()
    
    def train(self, features: pd.DataFrame, labels: pd.Series) -> None:
        """
        Labels: 1 if driver won, 0 otherwise
        Learns weights for each feature
        """
        self.model.fit(features, labels)
    
    def predict(self, features: pd.DataFrame) -> np.ndarray:
        """Returns raw predicted probabilities (may need normalization)"""
        raw_probs = self.model.predict(features)
        return self._normalize_probabilities(raw_probs)
    
    def _normalize_probabilities(self, probs: np.ndarray) -> np.ndarray:
        """Ensure probabilities sum to 1"""
        return probs / probs.sum()
```

**Module:** `f1-analytics/backend/app/ml/random_forest_model.py`

**Key Classes:**
```python
class RandomForestModel(BaseModel):
    def __init__(self, n_estimators: int = 100, max_depth: int = 10):
        self.model = RandomForestClassifier(
            n_estimators=n_estimators,
            max_depth=max_depth,
            random_state=42
        )
    
    def train(self, features: pd.DataFrame, labels: pd.Series) -> None:
        self.model.fit(features, labels)
    
    def predict(self, features: pd.DataFrame) -> np.ndarray:
        """Returns probability of winning (predict_proba[:, 1])"""
        return self.model.predict_proba(features)[:, 1]
```

**Module:** `f1-analytics/backend/app/ml/xgboost_model.py`

**Key Classes:**
```python
class XGBoostModel(BaseModel):
    def __init__(self, n_estimators: int = 100, learning_rate: float = 0.1):
        self.model = XGBClassifier(
            n_estimators=n_estimators,
            learning_rate=learning_rate,
            max_depth=6,
            random_state=42
        )
    
    def train(self, features: pd.DataFrame, labels: pd.Series) -> None:
        self.model.fit(features, labels)
    
    def predict(self, features: pd.DataFrame) -> np.ndarray:
        return self.model.predict_proba(features)[:, 1]
```

**Module:** `f1-analytics/backend/app/ml/ensemble.py`

**Purpose:** Combine predictions from multiple models.

**Key Classes:**
```python
class EnsembleModel:
    def __init__(self, models: List[BaseModel], weights: List[float] = None):
        """
        If weights not provided, use equal weighting.
        """
        self.models = models
        self.weights = weights or [1.0 / len(models)] * len(models)
    
    def predict(self, features: pd.DataFrame) -> np.ndarray:
        """Weighted average of model predictions"""
        predictions = [model.predict(features) for model in self.models]
        weighted_avg = np.average(predictions, axis=0, weights=self.weights)
        return weighted_avg
    
    def calculate_confidence_interval(self, predictions: np.ndarray) -> Tuple[np.ndarray, np.ndarray]:
        """
        95% confidence interval based on prediction variance across models.
        Returns: (lower_bound, upper_bound)
        """
        std_dev = np.std(predictions, axis=0)
        lower = predictions.mean(axis=0) - 1.96 * std_dev
        upper = predictions.mean(axis=0) + 1.96 * std_dev
        return np.clip(lower, 0, 1), np.clip(upper, 0, 1)
```

**Module:** `f1-analytics/backend/app/ml/model_manager.py`

**Purpose:** Load, save, version models.

**Key Classes:**
```python
class ModelManager:
    def __init__(self, storage_path: str = "/app/models"):
        self.storage_path = storage_path
    
    def save_model(self, model: BaseModel, metadata: Dict) -> str:
        """
        Saves model to disk as pickle file.
        Metadata stored in database (models table).
        Returns: model_id
        """
        filename = f"{model.__class__.__name__}_{metadata['version']}.pkl"
        filepath = os.path.join(self.storage_path, filename)
        model.save(filepath)
        
        # Insert into database
        db_model = Model(
            name=model.__class__.__name__,
            type=metadata['type'],
            version=metadata['version'],
            trained_at=datetime.utcnow(),
            hyperparameters_json=json.dumps(metadata.get('hyperparameters', {}))
        )
        db.session.add(db_model)
        db.session.commit()
        return db_model.model_id
    
    def load_model(self, model_id: int) -> BaseModel:
        """Load model from disk and return instance"""
        db_model = db.session.query(Model).get(model_id)
        filepath = os.path.join(self.storage_path, f"{db_model.name}_{db_model.version}.pkl")
        
        # Instantiate correct class based on type
        model_class = self._get_model_class(db_model.type)
        model = model_class()
        model.load(filepath)
        return model
    
    def get_latest_model(self, model_type: str) -> BaseModel:
        """Get most recently trained model of given type"""
        db_model = db.session.query(Model).filter_by(type=model_type).order_by(Model.trained_at.desc()).first()
        return self.load_model(db_model.model_id)
```

### 3.3 Web API Service

**Module:** `f1-analytics/backend/app/routes/predictions.py`

**Endpoints:**

```python
@predictions_bp.route('/api/v1/predictions/next-race', methods=['GET'])
@cache_response(ttl=3600)  # Cache for 1 hour
def get_next_race_predictions():
    """
    Returns predictions for the next upcoming race.
    
    Logic:
    1. Query races table for next race after today
    2. Query predictions table for that race_id (ensemble model)
    3. Join with drivers, constructors tables
    4. Format response per API contract
    """
    next_race = db.session.query(Race).filter(Race.date > datetime.now()).order_by(Race.date).first()
    if not next_race:
        return jsonify({'error': 'No upcoming races'}), 404
    
    predictions = db.session.query(Prediction).filter(
        Prediction.race_id == next_race.race_id,
        Prediction.model_id == get_ensemble_model_id()
    ).all()
    
    schema = PredictionResponseSchema(many=True)
    return jsonify({
        'race': RaceSchema().dump(next_race),
        'predictions': schema.dump(predictions),
        'generated_at': datetime.utcnow().isoformat()
    })
```

```python
@predictions_bp.route('/api/v1/predictions/race/<int:race_id>', methods=['GET'])
@cache_response(ttl=3600)
def get_race_predictions(race_id: int):
    """
    Returns predictions for a specific race.
    Query param: model_id (optional) - filter by specific model
    """
    model_id = request.args.get('model_id', type=int)
    
    query = db.session.query(Prediction).filter(Prediction.race_id == race_id)
    if model_id:
        query = query.filter(Prediction.model_id == model_id)
    
    predictions = query.all()
    schema = PredictionResponseSchema(many=True)
    return jsonify(schema.dump(predictions))
```

```python
@predictions_bp.route('/api/v1/predictions/compare/<int:race_id>', methods=['GET'])
@cache_response(ttl=3600)
def compare_models(race_id: int):
    """
    Returns predictions from all models for comparison.
    
    Response format:
    {
        'race_id': 123,
        'models': [
            {'model_name': 'regression', 'predictions': [...]},
            {'model_name': 'random_forest', 'predictions': [...]},
            ...
        ]
    }
    """
    models = db.session.query(Model).all()
    comparison = []
    
    for model in models:
        predictions = db.session.query(Prediction).filter(
            Prediction.race_id == race_id,
            Prediction.model_id == model.model_id
        ).all()
        comparison.append({
            'model_name': model.name,
            'predictions': PredictionResponseSchema(many=True).dump(predictions)
        })
    
    return jsonify({'race_id': race_id, 'models': comparison})
```

**Module:** `f1-analytics/backend/app/routes/standings.py`

**Endpoints:**

```python
@standings_bp.route('/api/v1/standings/drivers', methods=['GET'])
@cache_response(ttl=86400)  # Cache for 24 hours
def get_driver_standings():
    """
    Returns current season driver standings.
    Query param: season (optional, defaults to current year)
    """
    season = request.args.get('season', type=int, default=datetime.now().year)
    
    # Get latest race in season
    latest_race = db.session.query(Race).filter(
        Race.season_id == get_season_id(season),
        Race.date <= datetime.now()
    ).order_by(Race.date.desc()).first()
    
    if not latest_race:
        return jsonify({'error': 'No completed races in season'}), 404
    
    standings = db.session.query(DriverStanding).filter(
        DriverStanding.race_id == latest_race.race_id
    ).order_by(DriverStanding.position).all()
    
    schema = DriverStandingSchema(many=True)
    return jsonify({
        'season': season,
        'standings': schema.dump(standings)
    })
```

```python
@standings_bp.route('/api/v1/standings/constructors', methods=['GET'])
@cache_response(ttl=86400)
def get_constructor_standings():
    """Similar logic to driver standings"""
    # Implementation follows same pattern as get_driver_standings
```

**Module:** `f1-analytics/backend/app/routes/calendar.py`

**Endpoints:**

```python
@calendar_bp.route('/api/v1/calendar/<int:year>', methods=['GET'])
@cache_response(ttl=86400)
def get_calendar(year: int):
    """
    Returns race calendar for a season.
    Includes prediction_available flag (true if predictions exist for race).
    """
    races = db.session.query(Race).join(Season).filter(Season.year == year).order_by(Race.date).all()
    
    calendar = []
    for race in races:
        prediction_exists = db.session.query(Prediction).filter(Prediction.race_id == race.race_id).first() is not None
        calendar.append({
            'round': race.round_number,
            'name': race.name,
            'date': race.date.isoformat(),
            'circuit': race.circuit.name,
            'prediction_available': prediction_exists
        })
    
    return jsonify({'season': year, 'races': calendar})
```

**Module:** `f1-analytics/backend/app/routes/analytics.py`

**Endpoints:**

```python
@analytics_bp.route('/api/v1/analytics/model-accuracy', methods=['GET'])
@cache_response(ttl=3600)
def get_model_accuracy():
    """
    Returns accuracy metrics for models.
    Query params: model_id, season
    """
    model_id = request.args.get('model_id', type=int)
    season = request.args.get('season', type=int)
    
    query = db.session.query(ModelAccuracy)
    if model_id:
        query = query.filter(ModelAccuracy.model_id == model_id)
    if season:
        query = query.join(Race).join(Season).filter(Season.year == season)
    
    accuracies = query.all()
    schema = ModelAccuracySchema(many=True)
    return jsonify(schema.dump(accuracies))
```

```python
@analytics_bp.route('/api/v1/analytics/driver-performance/<int:driver_id>', methods=['GET'])
@cache_response(ttl=3600)
def get_driver_performance(driver_id: int):
    """
    Returns historical performance metrics and ELO evolution.
    """
    # Get race results for driver
    results = db.session.query(RaceResult).filter(RaceResult.driver_id == driver_id).order_by(RaceResult.race_id).all()
    
    # Get ELO evolution
    elo_ratings = db.session.query(EloRating).filter(EloRating.driver_id == driver_id).order_by(EloRating.race_id).all()
    
    return jsonify({
        'driver_id': driver_id,
        'results': RaceResultSchema(many=True).dump(results),
        'elo_evolution': EloRatingSchema(many=True).dump(elo_ratings)
    })
```

**Module:** `f1-analytics/backend/app/utils/cache.py`

**Purpose:** Redis caching decorator.

```python
def cache_response(ttl: int = 3600):
    """
    Decorator to cache API responses in Redis.
    Cache key format: "cache:{endpoint}:{query_params_hash}"
    """
    def decorator(f):
        @wraps(f)
        def wrapper(*args, **kwargs):
            # Generate cache key from request path and args
            cache_key = f"cache:{request.path}:{hash(frozenset(request.args.items()))}"
            
            # Check cache
            cached = redis_client.get(cache_key)
            if cached:
                return jsonify(json.loads(cached))
            
            # Execute function
            response = f(*args, **kwargs)
            
            # Store in cache
            redis_client.setex(cache_key, ttl, json.dumps(response.get_json()))
            return response
        return wrapper
    return decorator
```

### 3.4 Task Scheduler

**Module:** `f1-analytics/backend/app/tasks/celery_app.py`

**Purpose:** Configure Celery application.

```python
from celery import Celery
from celery.schedules import crontab

celery_app = Celery(
    'f1_analytics',
    broker='redis://redis:6379/0',
    backend='redis://redis:6379/0'
)

celery_app.conf.update(
    task_serializer='json',
    accept_content=['json'],
    result_serializer='json',
    timezone='UTC',
    enable_utc=True,
    beat_schedule={
        'import-race-results-daily': {
            'task': 'app.tasks.import_tasks.import_latest_race_results',
            'schedule': crontab(hour=12, minute=0),  # Daily at noon UTC
        },
        'update-standings-daily': {
            'task': 'app.tasks.import_tasks.import_current_standings',
            'schedule': crontab(hour=13, minute=0),
        },
        'retrain-models-weekly': {
            'task': 'app.tasks.training_tasks.retrain_all_models',
            'schedule': crontab(day_of_week='monday', hour=2, minute=0),
        },
    }
)
```

**Module:** `f1-analytics/backend/app/tasks/import_tasks.py`

**Purpose:** Celery tasks for data import.

```python
@celery_app.task(bind=True, max_retries=3)
def import_latest_race_results(self):
    """
    Imports results for the most recent completed race.
    Triggered daily to catch newly available data.
    """
    try:
        db_session = get_db_session()
        ergast_client = ErgastClient(base_url=config.ERGAST_API_URL)
        weather_client = WeatherClient(api_key=config.WEATHER_API_KEY)
        importer = DataImporter(db_session, ergast_client, weather_client)
        
        # Find most recent race
        latest_race = db_session.query(Race).filter(
            Race.date <= datetime.now()
        ).order_by(Race.date.desc()).first()
        
        if not latest_race:
            return "No completed races found"
        
        # Check if results already imported
        existing_results = db_session.query(RaceResult).filter(RaceResult.race_id == latest_race.race_id).first()
        if existing_results:
            return f"Results already imported for race {latest_race.race_id}"
        
        # Import data
        importer.import_race_results(latest_race.race_id)
        importer.import_qualifying_results(latest_race.race_id)
        importer.import_weather_data(latest_race.race_id)
        
        # Trigger model retraining
        retrain_all_models.delay()
        
        return f"Successfully imported data for race {latest_race.race_id}"
        
    except Exception as e:
        logger.error(f"Failed to import race results: {e}")
        raise self.retry(exc=e, countdown=3600)  # Retry in 1 hour
```

```python
@celery_app.task(bind=True, max_retries=3)
def import_current_standings(self):
    """Imports current season standings"""
    # Similar pattern to import_latest_race_results
```

**Module:** `f1-analytics/backend/app/tasks/training_tasks.py`

**Purpose:** Celery tasks for model training.

```python
@celery_app.task(bind=True, max_retries=1)
def retrain_all_models(self):
    """
    Retrains all prediction models with latest data.
    Triggered after new race data imported.
    """
    try:
        db_session = get_db_session()
        model_manager = ModelManager()
        
        # Get all historical race data for training
        races = db_session.query(Race).filter(Race.date < datetime.now()).all()
        
        # Build feature matrix and labels
        X_train, y_train = [], []
        for race in races:
            features = build_feature_matrix(race.race_id, db_session)
            labels = get_race_winner_labels(race.race_id, db_session)
            X_train.append(features)
            y_train.append(labels)
        
        X_train = pd.concat(X_train)
        y_train = pd.concat(y_train)
        
        # Train each model
        models = [
            RegressionModel(),
            RandomForestModel(n_estimators=100, max_depth=10),
            XGBoostModel(n_estimators=100, learning_rate=0.1),
            EloModel()
        ]
        
        for model in models:
            model.train(X_train, y_train)
            model_manager.save_model(model, {
                'version': f'v{datetime.now().strftime("%Y%m%d_%H%M%S")}',
                'type': model.__class__.__name__,
                'hyperparameters': model.get_hyperparameters()
            })
        
        # Generate predictions for next race
        generate_next_race_predictions.delay()
        
        return "Successfully retrained all models"
        
    except Exception as e:
        logger.error(f"Failed to retrain models: {e}")
        raise self.retry(exc=e, countdown=7200)  # Retry in 2 hours
```

```python
@celery_app.task
def generate_next_race_predictions():
    """
    Generates predictions for the next upcoming race.
    Stores predictions in database and invalidates cache.
    """
    db_session = get_db_session()
    model_manager = ModelManager()
    
    # Get next race
    next_race = db_session.query(Race).filter(Race.date > datetime.now()).order_by(Race.date).first()
    if not next_race:
        return "No upcoming races"
    
    # Load models
    models = [
        model_manager.get_latest_model('RegressionModel'),
        model_manager.get_latest_model('RandomForestModel'),
        model_manager.get_latest_model('XGBoostModel'),
        model_manager.get_latest_model('EloModel')
    ]
    ensemble = EnsembleModel(models)
    
    # Build feature matrix for next race
    features = build_feature_matrix(next_race.race_id, db_session)
    
    # Generate predictions
    predictions = ensemble.predict(features)
    lower_ci, upper_ci = ensemble.calculate_confidence_interval(predictions)
    
    # Store in database
    for idx, driver_id in enumerate(features['driver_id']):
        prediction = Prediction(
            race_id=next_race.race_id,
            model_id=get_ensemble_model_id(),
            driver_id=driver_id,
            win_probability=predictions[idx],
            confidence_interval_lower=lower_ci[idx],
            confidence_interval_upper=upper_ci[idx],
            created_at=datetime.utcnow()
        )
        db_session.add(prediction)
    
    db_session.commit()
    
    # Invalidate cache
    redis_client.delete_pattern('cache:*')
    
    return f"Generated predictions for race {next_race.race_id}"
```

### 3.5 Dashboard Application

**Module:** `f1-analytics/frontend/src/services/api.ts`

**Purpose:** Axios client with error handling.

```typescript
import axios, { AxiosInstance, AxiosError } from 'axios';

const api: AxiosInstance = axios.create({
  baseURL: import.meta.env.VITE_API_URL || 'http://localhost:5000',
  timeout: 10000,
  headers: {
    'Content-Type': 'application/json',
  },
});

// Response interceptor for error handling
api.interceptors.response.use(
  (response) => response,
  (error: AxiosError) => {
    if (error.response?.status === 429) {
      // Rate limited
      console.error('Rate limit exceeded. Please try again later.');
    } else if (error.response?.status >= 500) {
      // Server error
      console.error('Server error. Please try again later.');
    }
    return Promise.reject(error);
  }
);

export default api;
```

**Module:** `f1-analytics/frontend/src/services/predictions.ts`

**Purpose:** API calls for predictions.

```typescript
import api from './api';
import { PredictionResponse, RacePrediction } from '../types/prediction';

export const getNextRacePredictions = async (): Promise<PredictionResponse> => {
  const response = await api.get('/api/v1/predictions/next-race');
  return response.data;
};

export const getRacePredictions = async (raceId: number, modelId?: number): Promise<RacePrediction[]> => {
  const params = modelId ? { model_id: modelId } : {};
  const response = await api.get(`/api/v1/predictions/race/${raceId}`, { params });
  return response.data;
};

export const compareModels = async (raceId: number): Promise<ModelComparisonResponse> => {
  const response = await api.get(`/api/v1/predictions/compare/${raceId}`);
  return response.data;
};
```

**Module:** `f1-analytics/frontend/src/components/PredictionTable.tsx`

**Purpose:** Display prediction results in table format.

```typescript
import React from 'react';
import { RacePrediction } from '../types/prediction';

interface PredictionTableProps {
  predictions: RacePrediction[];
}

export const PredictionTable: React.FC<PredictionTableProps> = ({ predictions }) => {
  // Sort by win probability descending
  const sortedPredictions = [...predictions].sort((a, b) => b.win_probability - a.win_probability);

  return (
    <div className="overflow-x-auto">
      <table className="min-w-full bg-white border border-gray-300">
        <thead className="bg-gray-100">
          <tr>
            <th className="px-4 py-2 border">Rank</th>
            <th className="px-4 py-2 border">Driver</th>
            <th className="px-4 py-2 border">Constructor</th>
            <th className="px-4 py-2 border">Win Probability</th>
            <th className="px-4 py-2 border">Confidence Interval</th>
          </tr>
        </thead>
        <tbody>
          {sortedPredictions.map((pred, idx) => (
            <tr key={pred.driver} className={idx % 2 === 0 ? 'bg-gray-50' : ''}>
              <td className="px-4 py-2 border text-center">{idx + 1}</td>
              <td className="px-4 py-2 border">{pred.driver}</td>
              <td className="px-4 py-2 border">{pred.constructor}</td>
              <td className="px-4 py-2 border text-center">
                {(pred.win_probability * 100).toFixed(1)}%
              </td>
              <td className="px-4 py-2 border text-center">
                [{(pred.confidence_interval[0] * 100).toFixed(1)}%, {(pred.confidence_interval[1] * 100).toFixed(1)}%]
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
};
```

**Module:** `f1-analytics/frontend/src/components/PerformanceChart.tsx`

**Purpose:** Chart.js wrapper for performance visualizations.

```typescript
import React from 'react';
import { Line } from 'react-chartjs-2';
import { Chart as ChartJS, CategoryScale, LinearScale, PointElement, LineElement, Title, Tooltip, Legend } from 'chart.js';

ChartJS.register(CategoryScale, LinearScale, PointElement, LineElement, Title, Tooltip, Legend);

interface PerformanceChartProps {
  data: {
    labels: string[];
    datasets: {
      label: string;
      data: number[];
      borderColor: string;
      backgroundColor: string;
    }[];
  };
  title: string;
}

export const PerformanceChart: React.FC<PerformanceChartProps> = ({ data, title }) => {
  const options = {
    responsive: true,
    plugins: {
      legend: { position: 'top' as const },
      title: { display: true, text: title },
    },
    scales: {
      y: { beginAtZero: true },
    },
  };

  return <Line options={options} data={data} />;
};
```

**Module:** `f1-analytics/frontend/src/pages/Dashboard.tsx`

**Purpose:** Main dashboard page layout.

```typescript
import React, { useEffect, useState } from 'react';
import { getNextRacePredictions } from '../services/predictions';
import { PredictionTable } from '../components/PredictionTable';
import { PredictionResponse } from '../types/prediction';

export const Dashboard: React.FC = () => {
  const [data, setData] = useState<PredictionResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const fetchData = async () => {
      try {
        const result = await getNextRacePredictions();
        setData(result);
      } catch (err) {
        setError('Failed to load predictions');
      } finally {
        setLoading(false);
      }
    };

    fetchData();
  }, []);

  if (loading) return <div className="text-center py-8">Loading...</div>;
  if (error) return <div className="text-red-600 text-center py-8">{error}</div>;
  if (!data) return null;

  return (
    <div className="container mx-auto px-4 py-8">
      <h1 className="text-3xl font-bold mb-4">F1 Prediction Analytics</h1>
      <div className="bg-white rounded-lg shadow-md p-6 mb-6">
        <h2 className="text-2xl font-semibold mb-2">{data.race.name}</h2>
        <p className="text-gray-600 mb-1">{data.race.circuit}</p>
        <p className="text-gray-600 mb-4">{new Date(data.race.date).toLocaleDateString()}</p>
        <PredictionTable predictions={data.predictions} />
        <p className="text-sm text-gray-500 mt-4">
          Generated: {new Date(data.generated_at).toLocaleString()}
        </p>
      </div>
    </div>
  );
};
```

---

## 4. Database Schema Changes

### Migration: `002_add_elo_and_model_tables.py`

```python
"""Add ELO ratings and model metadata tables"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

def upgrade():
    # Models table
    op.create_table(
        'models',
        sa.Column('model_id', sa.Integer(), nullable=False),
        sa.Column('name', sa.String(100), nullable=False),
        sa.Column('type', sa.String(50), nullable=False),
        sa.Column('version', sa.String(50), nullable=False),
        sa.Column('trained_at', sa.DateTime(), nullable=False),
        sa.Column('hyperparameters_json', postgresql.JSON(), nullable=True),
        sa.PrimaryKeyConstraint('model_id')
    )
    op.create_index('idx_models_type_version', 'models', ['type', 'version'])

    # ELO ratings table
    op.create_table(
        'elo_ratings',
        sa.Column('rating_id', sa.Integer(), nullable=False),
        sa.Column('driver_id', sa.Integer(), nullable=True),
        sa.Column('constructor_id', sa.Integer(), nullable=True),
        sa.Column('race_id', sa.Integer(), nullable=False),
        sa.Column('rating_value', sa.Float(), nullable=False),
        sa.Column('calculated_at', sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint('rating_id'),
        sa.ForeignKeyConstraint(['driver_id'], ['drivers.driver_id']),
        sa.ForeignKeyConstraint(['constructor_id'], ['constructors.constructor_id']),
        sa.ForeignKeyConstraint(['race_id'], ['races.race_id'])
    )
    op.create_index('idx_elo_driver_race', 'elo_ratings', ['driver_id', 'race_id'])
    op.create_index('idx_elo_constructor_race', 'elo_ratings', ['constructor_id', 'race_id'])

    # Model accuracy table
    op.create_table(
        'model_accuracy',
        sa.Column('accuracy_id', sa.Integer(), nullable=False),
        sa.Column('model_id', sa.Integer(), nullable=False),
        sa.Column('race_id', sa.Integer(), nullable=False),
        sa.Column('brier_score', sa.Float(), nullable=True),
        sa.Column('top3_accuracy', sa.Float(), nullable=True),
        sa.Column('predicted_winner_id', sa.Integer(), nullable=True),
        sa.Column('actual_winner_id', sa.Integer(), nullable=True),
        sa.PrimaryKeyConstraint('accuracy_id'),
        sa.ForeignKeyConstraint(['model_id'], ['models.model_id']),
        sa.ForeignKeyConstraint(['race_id'], ['races.race_id']),
        sa.ForeignKeyConstraint(['predicted_winner_id'], ['drivers.driver_id']),
        sa.ForeignKeyConstraint(['actual_winner_id'], ['drivers.driver_id'])
    )
    op.create_index('idx_accuracy_model_race', 'model_accuracy', ['model_id', 'race_id'])

def downgrade():
    op.drop_table('model_accuracy')
    op.drop_table('elo_ratings')
    op.drop_table('models')
```

### Migration: `003_add_standing_tables.py`

```python
"""Add driver and constructor standings tables"""

from alembic import op
import sqlalchemy as sa

def upgrade():
    # Driver standings table
    op.create_table(
        'driver_standings',
        sa.Column('standing_id', sa.Integer(), nullable=False),
        sa.Column('race_id', sa.Integer(), nullable=False),
        sa.Column('driver_id', sa.Integer(), nullable=False),
        sa.Column('position', sa.Integer(), nullable=False),
        sa.Column('points', sa.Float(), nullable=False),
        sa.Column('wins', sa.Integer(), nullable=False, server_default='0'),
        sa.PrimaryKeyConstraint('standing_id'),
        sa.ForeignKeyConstraint(['race_id'], ['races.race_id']),
        sa.ForeignKeyConstraint(['driver_id'], ['drivers.driver_id']),
        sa.UniqueConstraint('race_id', 'driver_id', name='uq_driver_standing_race')
    )
    op.create_index('idx_driver_standings_race', 'driver_standings', ['race_id'])

    # Constructor standings table
    op.create_table(
        'constructor_standings',
        sa.Column('standing_id', sa.Integer(), nullable=False),
        sa.Column('race_id', sa.Integer(), nullable=False),
        sa.Column('constructor_id', sa.Integer(), nullable=False),
        sa.Column('position', sa.Integer(), nullable=False),
        sa.Column('points', sa.Float(), nullable=False),
        sa.Column('wins', sa.Integer(), nullable=False, server_default='0'),
        sa.PrimaryKeyConstraint('standing_id'),
        sa.ForeignKeyConstraint(['race_id'], ['races.race_id']),
        sa.ForeignKeyConstraint(['constructor_id'], ['constructors.constructor_id']),
        sa.UniqueConstraint('race_id', 'constructor_id', name='uq_constructor_standing_race')
    )
    op.create_index('idx_constructor_standings_race', 'constructor_standings', ['race_id'])

def downgrade():
    op.drop_table('constructor_standings')
    op.drop_table('driver_standings')
```

### Schema Indexes (Performance Optimization)

```sql
-- Add indexes for common query patterns
CREATE INDEX idx_predictions_race_model ON predictions(race_id, model_id);
CREATE INDEX idx_race_results_driver ON race_results(driver_id, race_id);
CREATE INDEX idx_races_date ON races(date);
CREATE INDEX idx_races_season ON races(season_id);
```

---

## 5. API Implementation Details

### 5.1 Request/Response Validation

**Module:** `f1-analytics/backend/app/schemas/prediction_schema.py`

```python
from marshmallow import Schema, fields, validate

class PredictionResponseSchema(Schema):
    driver = fields.String(required=True)
    constructor = fields.String(required=True)
    win_probability = fields.Float(required=True, validate=validate.Range(min=0, max=1))
    confidence_interval = fields.List(fields.Float(), validate=validate.Length(equal=2))
    model = fields.String(required=True)

class RaceSchema(Schema):
    race_id = fields.Integer(required=True)
    name = fields.String(required=True)
    date = fields.DateTime(required=True)
    circuit = fields.String(required=True)
```

### 5.2 Error Response Format

All API errors follow consistent format:

```json
{
  "error": "Human-readable error message",
  "code": "ERROR_CODE",
  "details": {
    "field": "specific error details"
  }
}
```

**Error Codes:**
- `RACE_NOT_FOUND` - Requested race does not exist
- `NO_PREDICTIONS_AVAILABLE` - Predictions not yet generated for race
- `INVALID_PARAMETER` - Query parameter validation failed
- `RATE_LIMIT_EXCEEDED` - Too many requests
- `INTERNAL_ERROR` - Server error

### 5.3 Rate Limiting

Implemented via `flask-limiter`:

```python
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address

limiter = Limiter(
    app,
    key_func=get_remote_address,
    default_limits=["100 per minute"],
    storage_uri="redis://redis:6379/1"
)

@predictions_bp.route('/api/v1/predictions/next-race')
@limiter.limit("20 per minute")  # Stricter limit for expensive endpoint
def get_next_race_predictions():
    # ...
```

### 5.4 CORS Configuration

```python
from flask_cors import CORS

CORS(app, resources={
    r"/api/*": {
        "origins": ["http://localhost:3000", "https://dashboard.f1analytics.com"],
        "methods": ["GET", "OPTIONS"],
        "allow_headers": ["Content-Type"]
    }
})
```

---

## 6. Function Signatures

### 6.1 Data Ingestion

```python
# ergast_client.py
class ErgastClient:
    def get_race_schedule(self, season: int) -> List[Dict[str, Any]]
    def get_race_results(self, season: int, round: int) -> List[Dict[str, Any]]
    def get_qualifying_results(self, season: int, round: int) -> List[Dict[str, Any]]
    def get_driver_standings(self, season: int, round: int = None) -> List[Dict[str, Any]]

# weather_client.py
class WeatherClient:
    def get_historical_weather(self, lat: float, lon: float, date: datetime) -> Dict[str, Any]
    def get_forecast(self, lat: float, lon: float) -> Dict[str, Any]

# data_importer.py
class DataImporter:
    def import_season_schedule(self, season: int) -> None
    def import_race_results(self, race_id: int) -> None
    def import_qualifying_results(self, race_id: int) -> None
    def import_standings(self, season: int, round: int = None) -> None
    def backfill_historical_data(self, start_season: int, end_season: int) -> None
```

### 6.2 ML Models

```python
# base_model.py
class BaseModel(ABC):
    @abstractmethod
    def train(self, features: pd.DataFrame, labels: pd.Series) -> None
    @abstractmethod
    def predict(self, features: pd.DataFrame) -> np.ndarray
    def save(self, path: str) -> None
    def load(self, path: str) -> None
    def get_feature_names(self) -> List[str]

# feature_engineering.py
def extract_driver_features(driver_id: int, race_id: int, db_session: Session) -> Dict[str, float]
def extract_constructor_features(constructor_id: int, race_id: int, db_session: Session) -> Dict[str, float]
def extract_circuit_features(circuit_id: int, driver_id: int, db_session: Session) -> Dict[str, float]
def extract_weather_features(race_id: int, db_session: Session) -> Dict[str, float]
def build_feature_matrix(race_id: int, db_session: Session) -> pd.DataFrame

# ensemble.py
class EnsembleModel:
    def predict(self, features: pd.DataFrame) -> np.ndarray
    def calculate_confidence_interval(self, predictions: np.ndarray) -> Tuple[np.ndarray, np.ndarray]

# model_manager.py
class ModelManager:
    def save_model(self, model: BaseModel, metadata: Dict[str, Any]) -> str
    def load_model(self, model_id: int) -> BaseModel
    def get_latest_model(self, model_type: str) -> BaseModel
```

### 6.3 API Routes

```python
# predictions.py
def get_next_race_predictions() -> Response
def get_race_predictions(race_id: int) -> Response
def compare_models(race_id: int) -> Response

# standings.py
def get_driver_standings() -> Response
def get_constructor_standings() -> Response

# calendar.py
def get_calendar(year: int) -> Response

# analytics.py
def get_model_accuracy() -> Response
def get_driver_performance(driver_id: int) -> Response
def get_track_coefficients(circuit_id: int) -> Response
```

### 6.4 Celery Tasks

```python
# import_tasks.py
@celery_app.task(bind=True, max_retries=3)
def import_latest_race_results(self) -> str

@celery_app.task(bind=True, max_retries=3)
def import_current_standings(self) -> str

# training_tasks.py
@celery_app.task(bind=True, max_retries=1)
def retrain_all_models(self) -> str

@celery_app.task
def generate_next_race_predictions() -> str
```

---

## 7. State Management

### 7.1 Backend State

**Database as Source of Truth:**
- All persistent state stored in PostgreSQL
- No in-memory session state (API is stateless)
- Redis used only for caching and Celery message broker

**Cache State:**
- Redis TTL-based expiration
- Cache keys prefixed by endpoint: `cache:/api/v1/predictions/next-race:{hash}`
- Invalidation via pattern matching: `redis_client.delete_pattern('cache:*')`

### 7.2 Frontend State

**React Context API:**

```typescript
// DashboardContext.tsx
interface DashboardState {
  nextRacePredictions: PredictionResponse | null;
  selectedRaceId: number | null;
  loading: boolean;
  error: string | null;
}

const DashboardContext = createContext<DashboardState | undefined>(undefined);

export const DashboardProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const [state, setState] = useState<DashboardState>({
    nextRacePredictions: null,
    selectedRaceId: null,
    loading: false,
    error: null,
  });

  // Context methods to update state
  const loadNextRacePredictions = async () => {
    setState(prev => ({ ...prev, loading: true }));
    try {
      const data = await getNextRacePredictions();
      setState(prev => ({ ...prev, nextRacePredictions: data, loading: false }));
    } catch (error) {
      setState(prev => ({ ...prev, error: 'Failed to load predictions', loading: false }));
    }
  };

  return (
    <DashboardContext.Provider value={{ state, loadNextRacePredictions }}>
      {children}
    </DashboardContext.Provider>
  );
};
```

**Local Component State:**
- Chart zoom/pan state
- Table sorting preferences
- UI toggles (expanded sections, etc.)

---

## 8. Error Handling Strategy

### 8.1 Backend Error Handling

**Exception Hierarchy:**

```python
# app/core/exceptions.py
class F1AnalyticsError(Exception):
    """Base exception for all application errors"""
    pass

class ExternalAPIError(F1AnalyticsError):
    """Raised when external API (Ergast, Weather) fails"""
    pass

class DataImportError(F1AnalyticsError):
    """Raised when data import fails"""
    pass

class ModelTrainingError(F1AnalyticsError):
    """Raised when model training fails"""
    pass

class ValidationError(F1AnalyticsError):
    """Raised when input validation fails"""
    pass
```

**Error Handler Registration:**

```python
# app/main.py
@app.errorhandler(ValidationError)
def handle_validation_error(e):
    return jsonify({'error': str(e), 'code': 'INVALID_PARAMETER'}), 400

@app.errorhandler(ExternalAPIError)
def handle_external_api_error(e):
    logger.error(f"External API error: {e}")
    return jsonify({'error': 'External service unavailable', 'code': 'EXTERNAL_SERVICE_ERROR'}), 503

@app.errorhandler(500)
def handle_internal_error(e):
    logger.exception("Internal server error")
    return jsonify({'error': 'Internal server error', 'code': 'INTERNAL_ERROR'}), 500
```

**Retry Logic:**

```python
# app/utils/retry.py
from functools import wraps
import time

def retry_on_failure(max_retries=3, backoff_base=2):
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            for attempt in range(max_retries):
                try:
                    return func(*args, **kwargs)
                except ExternalAPIError as e:
                    if attempt == max_retries - 1:
                        raise
                    wait_time = backoff_base ** attempt
                    logger.warning(f"Attempt {attempt + 1} failed, retrying in {wait_time}s")
                    time.sleep(wait_time)
        return wrapper
    return decorator
```

### 8.2 Frontend Error Handling

**Error Boundary Component:**

```typescript
// ErrorBoundary.tsx
class ErrorBoundary extends React.Component<{children: React.ReactNode}, {hasError: boolean}> {
  constructor(props) {
    super(props);
    this.state = { hasError: false };
  }

  static getDerivedStateFromError(error) {
    return { hasError: true };
  }

  componentDidCatch(error, errorInfo) {
    console.error('ErrorBoundary caught:', error, errorInfo);
  }

  render() {
    if (this.state.hasError) {
      return (
        <div className="text-center py-8">
          <h2 className="text-xl font-semibold text-red-600">Something went wrong</h2>
          <p className="text-gray-600">Please refresh the page</p>
        </div>
      );
    }
    return this.props.children;
  }
}
```

**User-Facing Error Messages:**

| Error Code | User Message |
|------------|--------------|
| RACE_NOT_FOUND | "Race not found. Please check the race ID." |
| NO_PREDICTIONS_AVAILABLE | "Predictions are not yet available for this race." |
| RATE_LIMIT_EXCEEDED | "Too many requests. Please wait a moment." |
| EXTERNAL_SERVICE_ERROR | "Data temporarily unavailable. Please try again later." |
| INTERNAL_ERROR | "An unexpected error occurred. Please try again." |

---

## 9. Test Plan

### Unit Tests

**Backend Unit Tests:**

```python
# tests/unit/test_feature_engineering.py
def test_extract_driver_features():
    """Test driver feature extraction calculates correct averages"""
    # Setup: Create 5 mock race results for driver
    # Assert: recent_avg_finish matches expected value

def test_extract_circuit_features():
    """Test circuit-specific features for driver"""
    # Setup: Create historical results at circuit
    # Assert: driver_wins_at_circuit is correct

def test_elo_calculation():
    """Test ELO rating update after race"""
    # Setup: Two drivers with known ratings
    # Assert: Winner rating increases, loser rating decreases

# tests/unit/test_models.py
def test_regression_model_train():
    """Test regression model training"""
    # Setup: Synthetic feature matrix and labels
    # Assert: Model learns weights, predict() returns probabilities

def test_ensemble_prediction():
    """Test ensemble combines model predictions correctly"""
    # Setup: Mock models with known predictions
    # Assert: Weighted average matches expected value

def test_confidence_interval_calculation():
    """Test confidence interval bounds"""
    # Setup: Predictions with known variance
    # Assert: Lower/upper bounds are within [0, 1]

# tests/unit/test_ergast_client.py
def test_get_race_results_success():
    """Test Ergast client parses race results correctly"""
    # Setup: Mock HTTP response with sample data
    # Assert: Returned list contains expected drivers

def test_rate_limiting():
    """Test rate limiter prevents excessive requests"""
    # Setup: Make 201 requests in rapid succession
    # Assert: Raises RateLimitError after 200 requests

# tests/unit/test_cache.py
def test_cache_hit():
    """Test cache decorator returns cached response"""
    # Setup: Populate cache with mock data
    # Assert: Function not called, cached data returned

def test_cache_expiration():
    """Test cache TTL expires correctly"""
    # Setup: Set cache with 1-second TTL
    # Assert: After 2 seconds, cache miss occurs
```

**Frontend Unit Tests:**

```typescript
// tests/PredictionTable.test.tsx
test('renders predictions sorted by win probability', () => {
  const predictions = [
    { driver: 'Driver A', win_probability: 0.2, ... },
    { driver: 'Driver B', win_probability: 0.5, ... },
  ];
  render(<PredictionTable predictions={predictions} />);
  const rows = screen.getAllByRole('row');
  expect(rows[1]).toHaveTextContent('Driver B'); // Higher probability first
});

// tests/api.test.ts
test('api client retries on 500 error', async () => {
  // Mock axios to return 500, then 200
  // Assert: Second request succeeds
});
```

### Integration Tests

**Backend Integration Tests:**

```python
# tests/integration/test_data_import_pipeline.py
def test_import_race_results_end_to_end(db_session, ergast_client):
    """Test full data import workflow"""
    # Setup: Mock Ergast API responses
    importer = DataImporter(db_session, ergast_client, weather_client)
    importer.import_race_results(race_id=123)
    
    # Assert: Database contains race results
    results = db_session.query(RaceResult).filter_by(race_id=123).all()
    assert len(results) == 20  # Full grid

# tests/integration/test_prediction_api.py
def test_get_next_race_predictions_api(client, db_session):
    """Test /api/v1/predictions/next-race endpoint"""
    # Setup: Populate database with upcoming race and predictions
    response = client.get('/api/v1/predictions/next-race')
    
    assert response.status_code == 200
    data = response.get_json()
    assert 'race' in data
    assert 'predictions' in data
    assert len(data['predictions']) > 0

# tests/integration/test_model_training.py
def test_model_training_with_real_data(db_session):
    """Test model training with realistic dataset"""
    # Setup: Import 2 seasons of historical data
    model = RandomForestModel()
    features, labels = build_training_data(db_session)
    
    model.train(features, labels)
    predictions = model.predict(features[:20])  # Predict on first race
    
    assert predictions.shape == (20,)  # One prediction per driver
    assert all(0 <= p <= 1 for p in predictions)  # Valid probabilities
```

**Frontend Integration Tests:**

```typescript
// tests/integration/Dashboard.integration.test.tsx
test('Dashboard loads and displays predictions from API', async () => {
  // Mock API response
  server.use(
    rest.get('/api/v1/predictions/next-race', (req, res, ctx) => {
      return res(ctx.json(mockPredictionData));
    })
  );

  render(<Dashboard />);
  
  // Wait for data to load
  await waitFor(() => {
    expect(screen.getByText('Monaco Grand Prix')).toBeInTheDocument();
  });
  
  // Verify table renders
  expect(screen.getByRole('table')).toBeInTheDocument();
});
```

### E2E Tests

**Playwright E2E Tests:**

```typescript
// e2e/dashboard.spec.ts
test('User can view predictions for next race', async ({ page }) => {
  await page.goto('http://localhost:3000');
  
  // Wait for predictions to load
  await page.waitForSelector('table');
  
  // Verify race name displayed
  await expect(page.locator('h2')).toContainText('Monaco Grand Prix');
  
  // Verify table contains drivers
  const rows = await page.locator('tbody tr').count();
  expect(rows).toBeGreaterThan(0);
  
  // Verify win probabilities displayed as percentages
  const firstProbability = await page.locator('tbody tr:first-child td:nth-child(4)').textContent();
  expect(firstProbability).toMatch(/\d+\.\d+%/);
});

test('User can compare models for a race', async ({ page }) => {
  await page.goto('http://localhost:3000/compare/123');
  
  // Verify multiple model tabs/sections
  await expect(page.locator('text=Regression')).toBeVisible();
  await expect(page.locator('text=Random Forest')).toBeVisible();
  await expect(page.locator('text=XGBoost')).toBeVisible();
  
  // Click on Random Forest tab
  await page.click('text=Random Forest');
  
  // Verify table updates
  await page.waitForSelector('table');
});

test('User can view historical accuracy metrics', async ({ page }) => {
  await page.goto('http://localhost:3000/analytics');
  
  // Verify chart renders
  await page.waitForSelector('canvas');
  
  // Verify accuracy metrics displayed
  await expect(page.locator('text=Brier Score')).toBeVisible();
  await expect(page.locator('text=Top 3 Accuracy')).toBeVisible();
});
```

### Test Coverage Goals

- **Backend:** 80% code coverage
- **Frontend:** 70% code coverage
- **Critical paths:** 100% coverage (data import, prediction generation, API endpoints)

---

## 10. Migration Strategy

### 10.1 Database Migration

**Step 1: Run Alembic Migrations**

```bash
cd f1-analytics/backend
alembic upgrade head
```

This creates new tables: `models`, `elo_ratings`, `model_accuracy`, `driver_standings`, `constructor_standings`.

**Step 2: Backfill Historical Data**

```bash
python scripts/import_historical_data.py --start-season 2020 --end-season 2025
```

Script logic:
- Fetch race schedules for each season
- Import race results, qualifying results
- Import standings after each race
- Fetch weather data for each race (graceful degradation if unavailable)

**Step 3: Initial Model Training**

```bash
python scripts/train_models.py
```

Trains all models on historical data and saves to `f1-analytics/backend/models/`.

**Step 4: Generate Initial Predictions**

```bash
python scripts/generate_predictions.py --next-race
```

Generates predictions for next upcoming race.

### 10.2 Application Deployment

**Development Environment:**

```bash
cd f1-analytics
docker-compose -f infrastructure/docker-compose.dev.yml up -d
```

Starts:
- PostgreSQL
- Redis
- Flask API
- Celery workers (3 instances)
- Celery beat scheduler
- React dev server

**Production Environment:**

```bash
# Build images
docker build -t f1-api:latest -f backend/Dockerfile backend/
docker build -t f1-worker:latest -f backend/Dockerfile.worker backend/
docker build -t f1-frontend:latest -f frontend/Dockerfile frontend/

# Deploy with Kubernetes
kubectl apply -f infrastructure/kubernetes/namespace.yaml
kubectl apply -f infrastructure/kubernetes/postgres-statefulset.yaml
kubectl apply -f infrastructure/kubernetes/redis-deployment.yaml
kubectl apply -f infrastructure/kubernetes/api-gateway-deployment.yaml
kubectl apply -f infrastructure/kubernetes/celery-deployment.yaml
kubectl apply -f infrastructure/kubernetes/frontend-deployment.yaml
kubectl apply -f infrastructure/kubernetes/ingress.yaml
```

### 10.3 Data Migration

No existing data to migrate (new feature). Existing F1 database schema is extended, not replaced.

---

## 11. Rollback Plan

### 11.1 Database Rollback

**Alembic Downgrade:**

```bash
alembic downgrade -1  # Roll back one migration
alembic downgrade base  # Roll back all migrations
```

Removes new tables without affecting existing `circuits`, `drivers`, `races`, etc.

### 11.2 Application Rollback

**Kubernetes Rollback:**

```bash
kubectl rollout undo deployment/api-gateway
kubectl rollout undo deployment/prediction-service
kubectl rollout undo deployment/frontend
```

**Docker Compose Rollback:**

```bash
# Revert to previous image tags
docker-compose -f infrastructure/docker-compose.prod.yml up -d
```

### 11.3 Feature Flag

Introduce environment variable `ENABLE_PREDICTIONS=false` to disable prediction endpoints without full rollback.

```python
# app/routes/predictions.py
if not os.getenv('ENABLE_PREDICTIONS', 'true').lower() == 'true':
    abort(404)
```

### 11.4 Cache Invalidation

If bad predictions deployed, invalidate cache to prevent serving stale data:

```bash
redis-cli FLUSHDB
```

---

## 12. Performance Considerations

### 12.1 Database Optimizations

**Indexes:**
- `idx_predictions_race_model` on `predictions(race_id, model_id)` - Fast prediction lookups
- `idx_race_results_driver` on `race_results(driver_id, race_id)` - Feature extraction queries
- `idx_races_date` on `races(date)` - Next race queries
- `idx_elo_driver_race` on `elo_ratings(driver_id, race_id)` - ELO history queries

**Connection Pooling:**

```python
# app/database.py
engine = create_engine(
    DATABASE_URL,
    pool_size=20,  # Max 20 connections
    max_overflow=10,  # Allow 10 overflow connections
    pool_pre_ping=True  # Test connections before use
)
```

**Query Optimization:**

```python
# Use eager loading to avoid N+1 queries
predictions = db.session.query(Prediction).options(
    joinedload(Prediction.driver),
    joinedload(Prediction.constructor),
    joinedload(Prediction.race)
).filter(Prediction.race_id == race_id).all()
```

### 12.2 Caching Strategy

**Redis Cache Layers:**

| Data Type | TTL | Invalidation |
|-----------|-----|--------------|
| Next race predictions | 1 hour | On new prediction generation |
| Historical race predictions | 24 hours | Never (immutable) |
| Driver standings | 24 hours | On standings update |
| Race calendar | 7 days | Manual/weekly refresh |

**Preload Cache on Startup:**

```python
# app/main.py
@app.before_first_request
def warm_cache():
    """Preload frequently accessed data into cache"""
    get_next_race_predictions()  # Cache next race
    get_driver_standings()  # Cache current standings
```

### 12.3 Model Serving Optimization

**Preload Models into Memory:**

```python
# app/main.py
model_cache = {}

@app.before_first_request
def load_models():
    """Load trained models into memory to avoid disk I/O per request"""
    model_manager = ModelManager()
    model_cache['regression'] = model_manager.get_latest_model('RegressionModel')
    model_cache['random_forest'] = model_manager.get_latest_model('RandomForestModel')
    model_cache['xgboost'] = model_manager.get_latest_model('XGBoostModel')
    model_cache['elo'] = model_manager.get_latest_model('EloModel')
```

**Batch Predictions:**

Generate predictions for all drivers in single `model.predict()` call (vectorized operation).

```python
# Instead of:
for driver in drivers:
    prediction = model.predict(driver_features)  # Slow

# Do:
all_features = build_feature_matrix(race_id, db_session)
predictions = model.predict(all_features)  # Fast (vectorized)
```

### 12.4 Frontend Optimizations

**Code Splitting:**

```typescript
// Lazy load heavy components
const AnalyticsPage = React.lazy(() => import('./pages/AnalyticsPage'));

<Suspense fallback={<div>Loading...</div>}>
  <AnalyticsPage />
</Suspense>
```

**Chart.js Performance:**

```typescript
// Limit data points rendered in charts
const chartData = {
  labels: eloHistory.slice(-20).map(r => r.race_date),  // Last 20 races only
  datasets: [...]
};
```

**API Request Debouncing:**

```typescript
// Debounce search/filter inputs to reduce API calls
const debouncedSearch = debounce((query) => {
  fetchPredictions(query);
}, 500);
```

### 12.5 Celery Task Optimization

**Worker Concurrency:**

```yaml
# infrastructure/kubernetes/celery-deployment.yaml
spec:
  replicas: 3
  template:
    spec:
      containers:
      - name: celery-worker
        args: ["celery", "-A", "app.tasks.celery_app", "worker", "--concurrency=4"]
```

3 workers × 4 concurrent tasks = 12 parallel tasks.

**Task Prioritization:**

```python
# High priority for prediction generation
generate_next_race_predictions.apply_async(priority=9)

# Low priority for historical backfill
backfill_historical_data.apply_async(priority=1)
```

### 12.6 CDN for Static Assets

Serve React build artifacts via CDN (CloudFlare, AWS CloudFront):

```nginx
# nginx.conf
location /static/ {
    alias /app/frontend/dist/assets/;
    expires 1y;
    add_header Cache-Control "public, immutable";
}
```

---

## Appendix: Existing Repository Structure

[Repository structure already provided in prompt - omitted for brevity]