# Low-Level Design: simple-spaghetti-repo

**Created:** 2026-02-12T15:15:08Z
**Status:** Draft

## 1. Implementation Overview

This LLD implements a Formula One prediction analytics platform as a new microservices-based system. The implementation will be organized in a new `f1-analytics/` directory structure to avoid conflicts with existing voting/recipe systems in the repository.

The core implementation consists of:
- **Backend Services**: Python FastAPI services for data ingestion, ML model training, prediction generation, and REST API
- **Frontend Dashboard**: React/TypeScript SPA with Chart.js visualizations
- **Infrastructure**: Docker containerization, PostgreSQL database, Redis cache, Apache Airflow for orchestration
- **ML Pipeline**: scikit-learn Random Forest and XGBoost models with ELO rating calculation

All services follow a layered architecture with clear separation: data layer (models, repositories), business logic layer (services), and presentation layer (routes, controllers). The implementation prioritizes horizontal scalability through stateless services and distributed caching.

---

## 2. File Structure

### New Backend Structure
```
f1-analytics/
├── backend/
│   ├── Dockerfile
│   ├── requirements.txt
│   ├── pyproject.toml
│   ├── alembic/
│   │   ├── env.py
│   │   ├── script.py.mako
│   │   └── versions/
│   │       └── 001_initial_schema.py
│   ├── app/
│   │   ├── __init__.py
│   │   ├── main.py                    # FastAPI application entrypoint
│   │   ├── config.py                  # Environment and database configuration
│   │   ├── database.py                # SQLAlchemy engine and session management
│   │   ├── dependencies.py            # FastAPI dependency injection providers
│   │   ├── models/
│   │   │   ├── __init__.py
│   │   │   ├── driver.py              # Driver ORM model
│   │   │   ├── team.py                # Team/Constructor ORM model
│   │   │   ├── circuit.py             # Circuit ORM model
│   │   │   ├── race.py                # Race ORM model
│   │   │   ├── race_result.py         # RaceResult ORM model
│   │   │   ├── qualifying_result.py   # QualifyingResult ORM model
│   │   │   ├── weather_data.py        # WeatherData ORM model
│   │   │   ├── prediction.py          # Prediction ORM model
│   │   │   ├── prediction_accuracy.py # PredictionAccuracy ORM model
│   │   │   └── user.py                # User authentication model
│   │   ├── schemas/
│   │   │   ├── __init__.py
│   │   │   ├── driver.py              # Pydantic schemas for Driver
│   │   │   ├── race.py                # Pydantic schemas for Race
│   │   │   ├── prediction.py          # Pydantic schemas for Prediction
│   │   │   ├── auth.py                # Auth request/response schemas
│   │   │   └── analytics.py           # Analytics response schemas
│   │   ├── repositories/
│   │   │   ├── __init__.py
│   │   │   ├── base.py                # Base repository with CRUD operations
│   │   │   ├── driver_repository.py
│   │   │   ├── race_repository.py
│   │   │   ├── prediction_repository.py
│   │   │   └── user_repository.py
│   │   ├── services/
│   │   │   ├── __init__.py
│   │   │   ├── auth_service.py        # JWT authentication and user management
│   │   │   ├── prediction_service.py  # Prediction retrieval and caching
│   │   │   ├── analytics_service.py   # Accuracy metrics and rankings
│   │   │   ├── export_service.py      # CSV/JSON export functionality
│   │   │   └── cache_service.py       # Redis caching abstraction
│   │   ├── routes/
│   │   │   ├── __init__.py
│   │   │   ├── auth.py                # /api/v1/auth/* endpoints
│   │   │   ├── predictions.py         # /api/v1/predictions/* endpoints
│   │   │   ├── races.py               # /api/v1/races/* endpoints
│   │   │   ├── analytics.py           # /api/v1/analytics/* endpoints
│   │   │   └── export.py              # /api/v1/export/* endpoints
│   │   └── middleware/
│   │       ├── __init__.py
│   │       ├── auth_middleware.py     # JWT validation middleware
│   │       ├── rate_limiter.py        # Redis-backed rate limiting
│   │       └── error_handler.py       # Global exception handling
│   ├── data_ingestion/
│   │   ├── __init__.py
│   │   ├── ergast_client.py           # Ergast API HTTP client
│   │   ├── weather_client.py          # OpenWeatherMap API client
│   │   ├── ingest_races.py            # Race results ingestion script
│   │   ├── ingest_qualifying.py       # Qualifying data ingestion
│   │   ├── ingest_weather.py          # Weather data ingestion
│   │   └── transform.py               # Data validation and normalization
│   ├── ml/
│   │   ├── __init__.py
│   │   ├── feature_engineering.py     # Feature extraction from raw data
│   │   ├── elo_calculator.py          # ELO rating calculation algorithm
│   │   ├── models/
│   │   │   ├── __init__.py
│   │   │   ├── random_forest.py       # Random Forest classifier
│   │   │   ├── xgboost_model.py       # XGBoost classifier
│   │   │   └── ensemble.py            # Ensemble prediction averaging
│   │   ├── training.py                # Model training orchestration
│   │   ├── inference.py               # Real-time prediction generation
│   │   └── evaluation.py              # Accuracy metrics calculation
│   ├── airflow/
│   │   ├── dags/
│   │   │   ├── daily_ingestion.py     # Daily data ingestion DAG
│   │   │   └── model_training.py      # Post-race model retraining DAG
│   │   └── operators/
│   │       └── custom_operators.py    # Custom Airflow operators
│   └── tests/
│       ├── __init__.py
│       ├── conftest.py                # Pytest fixtures
│       ├── unit/
│       │   ├── test_models.py
│       │   ├── test_services.py
│       │   ├── test_elo_calculator.py
│       │   └── test_feature_engineering.py
│       ├── integration/
│       │   ├── test_api_endpoints.py
│       │   ├── test_ingestion_pipeline.py
│       │   └── test_ml_training.py
│       └── e2e/
│           └── test_prediction_workflow.py
├── frontend/
│   ├── Dockerfile
│   ├── package.json
│   ├── tsconfig.json
│   ├── vite.config.ts
│   ├── tailwind.config.js
│   ├── public/
│   │   └── f1-logo.svg
│   ├── src/
│   │   ├── main.tsx
│   │   ├── App.tsx
│   │   ├── vite-env.d.ts
│   │   ├── api/
│   │   │   ├── client.ts              # Axios instance with interceptors
│   │   │   ├── authApi.ts             # Authentication API calls
│   │   │   ├── predictionsApi.ts      # Predictions API calls
│   │   │   ├── racesApi.ts            # Race data API calls
│   │   │   └── analyticsApi.ts        # Analytics API calls
│   │   ├── components/
│   │   │   ├── common/
│   │   │   │   ├── Header.tsx
│   │   │   │   ├── Footer.tsx
│   │   │   │   ├── Spinner.tsx
│   │   │   │   └── ErrorBoundary.tsx
│   │   │   ├── auth/
│   │   │   │   ├── LoginForm.tsx
│   │   │   │   └── RegisterForm.tsx
│   │   │   ├── predictions/
│   │   │   │   ├── PredictionCard.tsx
│   │   │   │   ├── DriverProbabilityBar.tsx
│   │   │   │   └── NextRaceHeader.tsx
│   │   │   ├── calendar/
│   │   │   │   ├── RaceCalendar.tsx
│   │   │   │   └── RaceCard.tsx
│   │   │   ├── analytics/
│   │   │   │   ├── AccuracyChart.tsx
│   │   │   │   ├── DriverRankingsTable.tsx
│   │   │   │   └── TeamRankingsTable.tsx
│   │   │   └── charts/
│   │   │       ├── BarChart.tsx
│   │   │       ├── LineChart.tsx
│   │   │       └── PieChart.tsx
│   │   ├── pages/
│   │   │   ├── HomePage.tsx           # Next race predictions
│   │   │   ├── CalendarPage.tsx       # Race calendar
│   │   │   ├── AnalyticsPage.tsx      # Historical accuracy
│   │   │   ├── RankingsPage.tsx       # Driver/team rankings
│   │   │   ├── LoginPage.tsx
│   │   │   └── RegisterPage.tsx
│   │   ├── context/
│   │   │   ├── AuthContext.tsx        # Authentication state management
│   │   │   └── ThemeContext.tsx       # Theme preferences
│   │   ├── hooks/
│   │   │   ├── useAuth.ts
│   │   │   ├── usePredictions.ts      # React Query hook for predictions
│   │   │   ├── useRaces.ts            # React Query hook for races
│   │   │   └── useAnalytics.ts        # React Query hook for analytics
│   │   ├── types/
│   │   │   ├── driver.ts
│   │   │   ├── race.ts
│   │   │   ├── prediction.ts
│   │   │   └── auth.ts
│   │   ├── utils/
│   │   │   ├── formatDate.ts
│   │   │   ├── exportData.ts
│   │   │   └── constants.ts
│   │   └── styles/
│   │       └── globals.css
│   └── tests/
│       ├── unit/
│       │   └── components.test.tsx
│       └── e2e/
│           └── prediction-flow.spec.ts
├── infrastructure/
│   ├── docker-compose.yml             # Local development setup
│   ├── docker-compose.prod.yml        # Production configuration
│   ├── kubernetes/
│   │   ├── namespace.yaml
│   │   ├── api-gateway-deployment.yaml
│   │   ├── prediction-service-deployment.yaml
│   │   ├── frontend-deployment.yaml
│   │   ├── postgres-statefulset.yaml
│   │   ├── redis-deployment.yaml
│   │   ├── airflow-deployment.yaml
│   │   ├── ingress.yaml
│   │   └── secrets.yaml
│   ├── terraform/
│   │   ├── main.tf
│   │   ├── variables.tf
│   │   ├── outputs.tf
│   │   └── modules/
│   │       ├── eks/
│   │       ├── rds/
│   │       └── elasticache/
│   └── monitoring/
│       ├── prometheus-config.yaml
│       ├── grafana-dashboards/
│       │   ├── system-health.json
│       │   └── ml-pipeline.json
│       └── alertmanager-config.yaml
└── scripts/
    ├── init_db.sh                     # Database initialization
    ├── seed_data.py                   # Load historical F1 data
    ├── generate_predictions.py        # Manual prediction generation
    └── deploy.sh                      # Deployment automation
```

### Modified Files
- `requirements.txt` - Add f1-analytics dependencies (isolated in comments)
- `package.json` - Add frontend dependencies for f1-analytics (scoped)
- `.gitignore` - Add f1-analytics/backend/.env, model artifacts, __pycache__

---

## 3. Detailed Component Designs

### 3.1 Data Ingestion Service

**Purpose**: Fetch, validate, and store race data from external APIs

**Components**:
- `ErgastClient`: HTTP client for Ergast API with retry logic
- `WeatherClient`: HTTP client for OpenWeatherMap API
- `DataTransformer`: Validates and normalizes raw API responses
- `IngestionOrchestrator`: Coordinates ingestion tasks

**Key Classes**:

```python
# data_ingestion/ergast_client.py
class ErgastClient:
    def __init__(self, base_url: str, session: httpx.AsyncClient):
        self.base_url = base_url
        self.session = session
    
    async def fetch_race_results(self, season: int, round: int) -> dict:
        """Fetch race results for given season and round"""
        
    async def fetch_qualifying_results(self, season: int, round: int) -> dict:
        """Fetch qualifying results"""
        
    async def fetch_driver_standings(self, season: int) -> dict:
        """Fetch driver championship standings"""
        
    async def fetch_constructor_standings(self, season: int) -> dict:
        """Fetch constructor standings"""

# data_ingestion/transform.py
class DataTransformer:
    def validate_race_result(self, raw_data: dict) -> RaceResultCreate:
        """Validate and transform race result to Pydantic schema"""
        
    def normalize_driver_name(self, driver_name: str) -> str:
        """Standardize driver name format"""
        
    def convert_lap_time(self, lap_time_str: str) -> float:
        """Convert lap time string to seconds"""
```

**Workflow**:
1. Airflow triggers daily ingestion DAG at 2am UTC
2. `ErgastClient` fetches latest race results with exponential backoff retry (3 attempts)
3. `DataTransformer` validates data against Pydantic schemas
4. Repositories persist validated data to PostgreSQL
5. On success, publish message to RabbitMQ to trigger model retraining
6. On failure, log error and alert via Alertmanager

### 3.2 ML Model Training Service

**Purpose**: Train and persist ML models for race winner prediction

**Components**:
- `FeatureEngineering`: Extract features from historical data
- `ELOCalculator`: Calculate and update ELO ratings
- `ModelTrainer`: Train Random Forest and XGBoost models
- `ModelEvaluator`: Calculate accuracy metrics on validation set

**Key Classes**:

```python
# ml/feature_engineering.py
class FeatureEngineering:
    def extract_driver_features(self, driver_id: int, race_id: int) -> pd.DataFrame:
        """
        Extract features:
        - Current ELO rating
        - Recent form (avg position last 5 races)
        - Track-specific win rate at this circuit
        - Team performance (avg team position last 5 races)
        """
        
    def extract_weather_features(self, race_id: int) -> pd.DataFrame:
        """Extract weather impact features"""
        
    def build_feature_matrix(self, race_id: int) -> pd.DataFrame:
        """Combine all features for all drivers in race"""

# ml/elo_calculator.py
class ELOCalculator:
    def __init__(self, k_factor: int = 32, base_rating: int = 1500):
        self.k_factor = k_factor
        self.base_rating = base_rating
    
    def calculate_expected_score(self, rating_a: int, rating_b: int) -> float:
        """ELO expected score formula"""
        
    def update_ratings(self, race_result: RaceResult) -> dict[int, int]:
        """Update all driver ELO ratings based on race finish positions"""

# ml/models/ensemble.py
class EnsemblePredictor:
    def __init__(self, random_forest_path: str, xgboost_path: str):
        self.rf_model = joblib.load(random_forest_path)
        self.xgb_model = joblib.load(xgboost_path)
    
    def predict_probabilities(self, features: pd.DataFrame) -> np.ndarray:
        """Average RF and XGBoost probabilities"""
        rf_probs = self.rf_model.predict_proba(features)[:, 1]
        xgb_probs = self.xgb_model.predict_proba(features)[:, 1]
        return (rf_probs + xgb_probs) / 2
```

**Training Pipeline**:
1. Celery task triggered by RabbitMQ message after race completion
2. Load historical race data (2010-present) from PostgreSQL
3. Calculate/update ELO ratings for all drivers and teams
4. Engineer features for each race (driver form, weather, track stats)
5. Split data: 80% train, 20% validation (stratified by season)
6. Train Random Forest (100 estimators, max_depth=10)
7. Train XGBoost (learning_rate=0.1, n_estimators=200)
8. Evaluate on validation set (Brier score, log loss, accuracy)
9. Save models to S3 with versioning (model_v{timestamp}.pkl)
10. Update `model_version` metadata in database

### 3.3 Prediction Service

**Purpose**: Generate race winner predictions using trained models

**Components**:
- `ModelLoader`: Load latest models from S3
- `InferenceEngine`: Generate predictions for upcoming race
- `CacheManager`: Cache predictions in Redis

**Key Classes**:

```python
# ml/inference.py
class InferenceEngine:
    def __init__(self, ensemble_model: EnsemblePredictor, db_session: Session):
        self.model = ensemble_model
        self.db = db_session
    
    def predict_next_race(self) -> list[PredictionCreate]:
        """
        Generate predictions for next scheduled race:
        1. Find next race from calendar
        2. Get active drivers and teams
        3. Extract features for each driver
        4. Run ensemble model inference
        5. Normalize probabilities to sum to 100%
        6. Return predictions sorted by probability descending
        """
        
    def predict_race_by_id(self, race_id: int) -> list[PredictionCreate]:
        """Generate predictions for specific historical/future race"""

# services/cache_service.py
class CacheService:
    def __init__(self, redis_client: redis.Redis):
        self.redis = redis_client
    
    def get_predictions(self, race_id: int) -> Optional[list[dict]]:
        """Retrieve cached predictions for race"""
        
    def set_predictions(self, race_id: int, predictions: list[dict], ttl: int = 604800):
        """Cache predictions with 7-day TTL"""
        
    def invalidate_race(self, race_id: int):
        """Clear cache for race when new predictions generated"""
```

**Prediction Flow**:
1. API receives request for next race predictions
2. Check Redis cache for race_id
3. If cached, return from Redis (sub-10ms)
4. If cache miss, load latest model from S3
5. Extract features for all active drivers
6. Run inference (Random Forest + XGBoost ensemble)
7. Normalize probabilities, persist to database
8. Cache in Redis with 7-day TTL
9. Return JSON response (<5 seconds total)

### 3.4 API Gateway (FastAPI)

**Purpose**: Expose REST endpoints for frontend and external consumers

**Components**:
- `AuthMiddleware`: JWT validation on protected routes
- `RateLimiter`: Redis-backed rate limiting (100 req/min per user)
- `ErrorHandler`: Global exception handling with user-friendly messages
- Route handlers for auth, predictions, races, analytics, export

**Key Route Handlers**:

```python
# routes/predictions.py
@router.get("/api/v1/predictions/next-race", response_model=NextRacePredictionResponse)
async def get_next_race_predictions(
    current_user: User = Depends(get_current_user),
    prediction_service: PredictionService = Depends(get_prediction_service)
):
    """
    1. Validate JWT token from Authorization header
    2. Call prediction_service.get_next_race_predictions()
    3. Check cache first, generate if needed
    4. Return predictions with race metadata
    """

# routes/analytics.py
@router.get("/api/v1/analytics/accuracy", response_model=AccuracyMetricsResponse)
async def get_accuracy_metrics(
    season: int = Query(..., ge=2010, le=2030),
    analytics_service: AnalyticsService = Depends(get_analytics_service)
):
    """
    1. Retrieve all completed races for season
    2. Calculate Brier score, log loss, correct winner %
    3. Aggregate by race for detailed breakdown
    4. Return metrics with confidence intervals
    """

# routes/export.py
@router.get("/api/v1/export/predictions")
async def export_predictions(
    race_id: int = Query(...),
    format: ExportFormat = Query(ExportFormat.JSON),
    export_service: ExportService = Depends(get_export_service)
):
    """
    1. Fetch predictions for race_id
    2. Format as CSV or JSON based on query param
    3. Return StreamingResponse with file download
    """
```

**Middleware Stack**:
```python
# middleware/auth_middleware.py
class JWTAuthMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        if request.url.path.startswith("/api/v1/auth"):
            return await call_next(request)
        
        token = request.headers.get("Authorization", "").replace("Bearer ", "")
        if not token:
            return JSONResponse({"error": "Missing token"}, status_code=401)
        
        try:
            payload = jwt.decode(token, SECRET_KEY, algorithms=["HS256"])
            request.state.user_id = payload["sub"]
        except jwt.ExpiredSignatureError:
            return JSONResponse({"error": "Token expired"}, status_code=401)
        except jwt.JWTError:
            return JSONResponse({"error": "Invalid token"}, status_code=401)
        
        return await call_next(request)

# middleware/rate_limiter.py
class RateLimitMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        user_id = request.state.user_id
        key = f"rate_limit:{user_id}"
        
        current = await redis_client.incr(key)
        if current == 1:
            await redis_client.expire(key, 60)
        
        if current > 100:
            return JSONResponse({"error": "Rate limit exceeded"}, status_code=429)
        
        response = await call_next(request)
        response.headers["X-RateLimit-Remaining"] = str(100 - current)
        return response
```

### 3.5 Web Dashboard (React/TypeScript)

**Purpose**: Interactive UI for viewing predictions and analytics

**Components**:
- `AuthContext`: Manages JWT tokens and user state
- `usePredictions` hook: React Query data fetching for predictions
- `PredictionCard`: Displays next race predictions with bar charts
- `AccuracyChart`: Line chart of historical prediction accuracy

**Key Components**:

```typescript
// pages/HomePage.tsx
export const HomePage: React.FC = () => {
  const { data: predictions, isLoading } = usePredictions();
  
  return (
    <div className="container mx-auto px-4 py-8">
      <NextRaceHeader race={predictions?.race} />
      <div className="grid grid-cols-1 gap-4">
        {predictions?.predictions.map(p => (
          <DriverProbabilityBar 
            key={p.driver_id}
            driverName={p.driver_name}
            probability={p.win_probability}
            teamColor={p.team_color}
          />
        ))}
      </div>
    </div>
  );
};

// components/predictions/DriverProbabilityBar.tsx
interface DriverProbabilityBarProps {
  driverName: string;
  probability: number;
  teamColor: string;
}

export const DriverProbabilityBar: React.FC<DriverProbabilityBarProps> = ({
  driverName, probability, teamColor
}) => {
  return (
    <div className="flex items-center gap-4 p-4 bg-white rounded-lg shadow">
      <span className="w-40 font-semibold">{driverName}</span>
      <div className="flex-1 bg-gray-200 rounded-full h-8">
        <div 
          className="h-8 rounded-full flex items-center justify-end px-2"
          style={{ width: `${probability}%`, backgroundColor: teamColor }}
        >
          <span className="text-white font-bold">{probability.toFixed(1)}%</span>
        </div>
      </div>
    </div>
  );
};

// hooks/usePredictions.ts
export const usePredictions = () => {
  return useQuery({
    queryKey: ['predictions', 'next-race'],
    queryFn: async () => {
      const response = await api.get('/api/v1/predictions/next-race');
      return response.data as NextRacePredictionResponse;
    },
    staleTime: 1000 * 60 * 60, // 1 hour
    cacheTime: 1000 * 60 * 60 * 24, // 24 hours
  });
};

// context/AuthContext.tsx
export const AuthContext = createContext<AuthContextType | null>(null);

export const AuthProvider: React.FC<{ children: ReactNode }> = ({ children }) => {
  const [token, setToken] = useState<string | null>(localStorage.getItem('jwt'));
  
  const login = async (email: string, password: string) => {
    const response = await authApi.login({ email, password });
    setToken(response.token);
    localStorage.setItem('jwt', response.token);
  };
  
  const logout = () => {
    setToken(null);
    localStorage.removeItem('jwt');
  };
  
  return (
    <AuthContext.Provider value={{ token, login, logout }}>
      {children}
    </AuthContext.Provider>
  );
};
```

**Routing**:
```typescript
// App.tsx
const router = createBrowserRouter([
  {
    path: "/f1-analytics",
    element: <Layout />,
    children: [
      { path: "", element: <HomePage /> },
      { path: "calendar", element: <CalendarPage /> },
      { path: "analytics", element: <AnalyticsPage /> },
      { path: "rankings", element: <RankingsPage /> },
      { path: "login", element: <LoginPage /> },
    ],
  },
]);
```

### 3.6 Database Service (PostgreSQL)

**Purpose**: Persistent storage for F1 data and predictions

**Design**:
- PostgreSQL 15 with TimescaleDB extension for time-series optimization
- Table partitioning by `season_year` for RaceResult, Prediction tables
- Indexes on foreign keys and frequently queried columns
- Read replicas for query distribution (2 replicas)

**Connection Pooling**:
```python
# database.py
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import QueuePool

engine = create_engine(
    DATABASE_URL,
    poolclass=QueuePool,
    pool_size=20,
    max_overflow=10,
    pool_pre_ping=True,
    echo=False
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
```

---

## 4. Database Schema Changes

### Migration Script: 001_initial_schema.py

```sql
-- Alembic migration for initial F1 analytics schema

CREATE TABLE drivers (
    driver_id SERIAL PRIMARY KEY,
    driver_code VARCHAR(3) UNIQUE NOT NULL,
    driver_name VARCHAR(100) NOT NULL,
    nationality VARCHAR(50),
    date_of_birth DATE,
    current_team_id INTEGER,
    current_elo_rating INTEGER DEFAULT 1500,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX idx_drivers_code ON drivers(driver_code);
CREATE INDEX idx_drivers_elo ON drivers(current_elo_rating DESC);

CREATE TABLE teams (
    team_id SERIAL PRIMARY KEY,
    team_name VARCHAR(100) UNIQUE NOT NULL,
    nationality VARCHAR(50),
    current_elo_rating INTEGER DEFAULT 1500,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

CREATE TABLE circuits (
    circuit_id SERIAL PRIMARY KEY,
    circuit_name VARCHAR(100) UNIQUE NOT NULL,
    location VARCHAR(100),
    country VARCHAR(50),
    track_length_km DECIMAL(5, 2),
    track_type VARCHAR(20) CHECK (track_type IN ('street', 'permanent')),
    created_at TIMESTAMP DEFAULT NOW()
);

CREATE TABLE races (
    race_id SERIAL PRIMARY KEY,
    season_year INTEGER NOT NULL,
    round_number INTEGER NOT NULL,
    circuit_id INTEGER REFERENCES circuits(circuit_id),
    race_date DATE NOT NULL,
    race_name VARCHAR(100) NOT NULL,
    status VARCHAR(20) DEFAULT 'scheduled' CHECK (status IN ('scheduled', 'completed', 'cancelled')),
    created_at TIMESTAMP DEFAULT NOW(),
    UNIQUE(season_year, round_number)
);

CREATE INDEX idx_races_date ON races(race_date);
CREATE INDEX idx_races_season ON races(season_year, round_number);
CREATE INDEX idx_races_status ON races(status);

CREATE TABLE race_results (
    result_id SERIAL PRIMARY KEY,
    race_id INTEGER REFERENCES races(race_id),
    driver_id INTEGER REFERENCES drivers(driver_id),
    team_id INTEGER REFERENCES teams(team_id),
    grid_position INTEGER,
    final_position INTEGER,
    points DECIMAL(4, 1),
    fastest_lap_time INTERVAL,
    status VARCHAR(20) DEFAULT 'finished' CHECK (status IN ('finished', 'retired', 'dnf', 'disqualified')),
    created_at TIMESTAMP DEFAULT NOW(),
    UNIQUE(race_id, driver_id)
) PARTITION BY RANGE (race_id);

CREATE TABLE race_results_2020_2025 PARTITION OF race_results
    FOR VALUES FROM (1) TO (500);

CREATE TABLE race_results_2026_2030 PARTITION OF race_results
    FOR VALUES FROM (500) TO (1000);

CREATE INDEX idx_race_results_race ON race_results(race_id);
CREATE INDEX idx_race_results_driver ON race_results(driver_id);

CREATE TABLE qualifying_results (
    qualifying_id SERIAL PRIMARY KEY,
    race_id INTEGER REFERENCES races(race_id),
    driver_id INTEGER REFERENCES drivers(driver_id),
    q1_time INTERVAL,
    q2_time INTERVAL,
    q3_time INTERVAL,
    final_grid_position INTEGER,
    created_at TIMESTAMP DEFAULT NOW(),
    UNIQUE(race_id, driver_id)
);

CREATE INDEX idx_qualifying_race ON qualifying_results(race_id);

CREATE TABLE weather_data (
    weather_id SERIAL PRIMARY KEY,
    race_id INTEGER UNIQUE REFERENCES races(race_id),
    temperature_celsius DECIMAL(4, 1),
    precipitation_mm DECIMAL(5, 2),
    wind_speed_kph DECIMAL(5, 2),
    conditions VARCHAR(20) CHECK (conditions IN ('dry', 'wet', 'mixed')),
    created_at TIMESTAMP DEFAULT NOW()
);

CREATE TABLE predictions (
    prediction_id SERIAL PRIMARY KEY,
    race_id INTEGER REFERENCES races(race_id),
    driver_id INTEGER REFERENCES drivers(driver_id),
    predicted_win_probability DECIMAL(5, 2) CHECK (predicted_win_probability >= 0 AND predicted_win_probability <= 100),
    model_version VARCHAR(50) NOT NULL,
    prediction_timestamp TIMESTAMP DEFAULT NOW(),
    created_at TIMESTAMP DEFAULT NOW(),
    UNIQUE(race_id, driver_id, model_version)
) PARTITION BY RANGE (race_id);

CREATE TABLE predictions_2020_2025 PARTITION OF predictions
    FOR VALUES FROM (1) TO (500);

CREATE TABLE predictions_2026_2030 PARTITION OF predictions
    FOR VALUES FROM (500) TO (1000);

CREATE INDEX idx_predictions_race ON predictions(race_id);
CREATE INDEX idx_predictions_timestamp ON predictions(prediction_timestamp DESC);

CREATE TABLE prediction_accuracy (
    accuracy_id SERIAL PRIMARY KEY,
    race_id INTEGER UNIQUE REFERENCES races(race_id),
    brier_score DECIMAL(6, 4),
    log_loss DECIMAL(6, 4),
    correct_winner BOOLEAN,
    top_3_accuracy BOOLEAN,
    created_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX idx_accuracy_race ON prediction_accuracy(race_id);

CREATE TABLE users (
    user_id SERIAL PRIMARY KEY,
    email VARCHAR(255) UNIQUE NOT NULL,
    password_hash VARCHAR(255) NOT NULL,
    created_at TIMESTAMP DEFAULT NOW(),
    last_login TIMESTAMP,
    role VARCHAR(20) DEFAULT 'user' CHECK (role IN ('user', 'admin'))
);

CREATE INDEX idx_users_email ON users(email);

-- Add foreign key constraint for drivers.current_team_id
ALTER TABLE drivers ADD CONSTRAINT fk_drivers_team 
    FOREIGN KEY (current_team_id) REFERENCES teams(team_id);

-- Create materialized view for driver rankings (performance optimization)
CREATE MATERIALIZED VIEW driver_rankings AS
SELECT 
    d.driver_id,
    d.driver_name,
    d.current_elo_rating,
    COUNT(CASE WHEN rr.final_position = 1 THEN 1 END) as wins,
    SUM(rr.points) as total_points,
    MAX(r.season_year) as latest_season
FROM drivers d
LEFT JOIN race_results rr ON d.driver_id = rr.driver_id
LEFT JOIN races r ON rr.race_id = r.race_id
GROUP BY d.driver_id, d.driver_name, d.current_elo_rating
ORDER BY d.current_elo_rating DESC;

CREATE UNIQUE INDEX idx_driver_rankings_driver ON driver_rankings(driver_id);

-- Refresh materialized view daily via cron job
```

### Pydantic Models (ORM)

```python
# models/driver.py
from sqlalchemy import Column, Integer, String, Date, ForeignKey
from sqlalchemy.orm import relationship
from app.database import Base

class Driver(Base):
    __tablename__ = "drivers"
    
    driver_id = Column(Integer, primary_key=True, index=True)
    driver_code = Column(String(3), unique=True, nullable=False)
    driver_name = Column(String(100), nullable=False)
    nationality = Column(String(50))
    date_of_birth = Column(Date)
    current_team_id = Column(Integer, ForeignKey("teams.team_id"))
    current_elo_rating = Column(Integer, default=1500)
    
    team = relationship("Team", back_populates="drivers")
    race_results = relationship("RaceResult", back_populates="driver")

# models/prediction.py
class Prediction(Base):
    __tablename__ = "predictions"
    
    prediction_id = Column(Integer, primary_key=True, index=True)
    race_id = Column(Integer, ForeignKey("races.race_id"), nullable=False)
    driver_id = Column(Integer, ForeignKey("drivers.driver_id"), nullable=False)
    predicted_win_probability = Column(Numeric(5, 2), nullable=False)
    model_version = Column(String(50), nullable=False)
    prediction_timestamp = Column(DateTime, default=datetime.utcnow)
    
    race = relationship("Race", back_populates="predictions")
    driver = relationship("Driver")
```

---

## 5. API Implementation Details

### Authentication Endpoints

**POST /api/v1/auth/register**

```python
# routes/auth.py
@router.post("/register", response_model=TokenResponse, status_code=201)
async def register_user(
    user_data: UserRegisterRequest,
    auth_service: AuthService = Depends(get_auth_service)
):
    """
    Request validation:
    - Email format (RFC 5322)
    - Password min 8 chars, 1 uppercase, 1 lowercase, 1 digit
    
    Steps:
    1. Check if email already exists (raise 409 Conflict)
    2. Hash password with bcrypt (12 rounds)
    3. Create user in database
    4. Generate JWT token (24h expiry)
    5. Return token and user_id
    
    Error handling:
    - 400: Invalid email/password format
    - 409: Email already registered
    - 500: Database error
    """
    if await auth_service.user_exists(user_data.email):
        raise HTTPException(status_code=409, detail="Email already registered")
    
    user = await auth_service.create_user(user_data)
    token = auth_service.generate_token(user.user_id)
    
    return TokenResponse(
        user_id=str(user.user_id),
        token=token,
        expires_at=(datetime.utcnow() + timedelta(hours=24)).isoformat()
    )
```

**POST /api/v1/auth/login**

```python
@router.post("/login", response_model=TokenResponse)
async def login_user(
    credentials: UserLoginRequest,
    auth_service: AuthService = Depends(get_auth_service)
):
    """
    Steps:
    1. Retrieve user by email
    2. Verify password with bcrypt.checkpw()
    3. Update last_login timestamp
    4. Generate JWT token
    5. Return token
    
    Error handling:
    - 401: Invalid credentials (generic message for security)
    - 500: Database error
    """
    user = await auth_service.authenticate(credentials.email, credentials.password)
    if not user:
        raise HTTPException(status_code=401, detail="Invalid credentials")
    
    token = auth_service.generate_token(user.user_id)
    await auth_service.update_last_login(user.user_id)
    
    return TokenResponse(token=token, expires_at=...)
```

### Prediction Endpoints

**GET /api/v1/predictions/next-race**

```python
@router.get("/next-race", response_model=NextRacePredictionResponse)
async def get_next_race_predictions(
    current_user: User = Depends(get_current_user),
    prediction_service: PredictionService = Depends(get_prediction_service),
    cache_service: CacheService = Depends(get_cache_service)
):
    """
    Steps:
    1. Find next scheduled race (status='scheduled', race_date >= today)
    2. Check Redis cache for predictions (key: f"predictions:race:{race_id}")
    3. If cache hit, deserialize and return (avg 8ms)
    4. If cache miss:
       a. Load latest ML model from S3
       b. Generate predictions via inference engine
       c. Persist predictions to database
       d. Cache in Redis (TTL 7 days)
    5. Return predictions sorted by probability descending
    
    Performance:
    - Cache hit: <50ms
    - Cache miss: <5s (model inference)
    
    Error handling:
    - 404: No upcoming races found
    - 500: Model inference failure (return last cached predictions)
    """
    next_race = await prediction_service.get_next_race()
    if not next_race:
        raise HTTPException(status_code=404, detail="No upcoming races")
    
    cached = await cache_service.get_predictions(next_race.race_id)
    if cached:
        return NextRacePredictionResponse(**cached)
    
    predictions = await prediction_service.generate_predictions(next_race.race_id)
    await cache_service.set_predictions(next_race.race_id, predictions)
    
    return NextRacePredictionResponse(
        race_id=next_race.race_id,
        race_name=next_race.race_name,
        race_date=next_race.race_date.isoformat(),
        circuit=next_race.circuit.circuit_name,
        predictions=predictions,
        model_version=predictions[0].model_version,
        generated_at=datetime.utcnow().isoformat()
    )
```

### Analytics Endpoints

**GET /api/v1/analytics/accuracy?season=2026**

```python
@router.get("/accuracy", response_model=AccuracyMetricsResponse)
async def get_accuracy_metrics(
    season: int = Query(..., ge=2010, le=2030),
    analytics_service: AnalyticsService = Depends(get_analytics_service)
):
    """
    Steps:
    1. Fetch all completed races for season
    2. Join predictions and actual results
    3. Calculate metrics:
       - Brier score: mean((p - actual)^2)
       - Correct winner %: count(predicted_winner == actual_winner) / total_races
       - Top-3 accuracy: count(actual_winner in top_3_predicted)
    4. Group by race for detailed breakdown
    5. Return aggregated and per-race metrics
    
    Database query optimization:
    - Use materialized view for pre-aggregated stats
    - Query only completed races (status='completed')
    - Leverage race_id partition for fast filtering
    
    Error handling:
    - 400: Invalid season parameter
    - 404: No completed races for season
    """
    metrics = await analytics_service.calculate_season_accuracy(season)
    return AccuracyMetricsResponse(**metrics)
```

### Export Endpoints

**GET /api/v1/export/race-results?season=2026&format=csv**

```python
@router.get("/race-results")
async def export_race_results(
    season: int = Query(...),
    format: ExportFormat = Query(ExportFormat.JSON),
    export_service: ExportService = Depends(get_export_service)
):
    """
    Steps:
    1. Query race results for season with joins (driver, team, circuit)
    2. Format data based on export format:
       - CSV: pandas.DataFrame.to_csv()
       - JSON: json.dumps() with pretty printing
    3. Return StreamingResponse with appropriate Content-Type
    
    Headers:
    - Content-Disposition: attachment; filename="race_results_2026.csv"
    - Content-Type: text/csv or application/json
    
    Performance:
    - Stream data to avoid memory issues with large datasets
    - Use database cursor for chunked retrieval
    
    Error handling:
    - 400: Invalid format parameter
    - 404: No results for season
    """
    results = await export_service.get_race_results(season)
    
    if format == ExportFormat.CSV:
        output = export_service.to_csv(results)
        return StreamingResponse(
            io.BytesIO(output.encode()),
            media_type="text/csv",
            headers={"Content-Disposition": f"attachment; filename=race_results_{season}.csv"}
        )
    else:
        return JSONResponse(content=results)
```

---

## 6. Function Signatures

### Services Layer

```python
# services/auth_service.py
class AuthService:
    def __init__(self, user_repo: UserRepository, jwt_manager: JWTManager):
        self.user_repo = user_repo
        self.jwt_manager = jwt_manager
    
    async def create_user(self, user_data: UserRegisterRequest) -> User:
        """Hash password and create user in database"""
    
    async def authenticate(self, email: str, password: str) -> Optional[User]:
        """Verify credentials and return user if valid"""
    
    def generate_token(self, user_id: int) -> str:
        """Generate JWT with 24h expiry"""
    
    def verify_token(self, token: str) -> dict:
        """Decode and validate JWT, raise if invalid/expired"""
    
    async def user_exists(self, email: str) -> bool:
        """Check if email already registered"""

# services/prediction_service.py
class PredictionService:
    def __init__(
        self, 
        race_repo: RaceRepository,
        prediction_repo: PredictionRepository,
        inference_engine: InferenceEngine,
        cache_service: CacheService
    ):
        ...
    
    async def get_next_race(self) -> Optional[Race]:
        """Find next scheduled race after today"""
    
    async def generate_predictions(self, race_id: int) -> list[PredictionCreate]:
        """
        Generate predictions for race using ML models.
        Returns list of predictions sorted by probability descending.
        """
    
    async def get_predictions_by_race(self, race_id: int) -> list[Prediction]:
        """Retrieve predictions from database/cache"""
    
    async def invalidate_cache(self, race_id: int):
        """Clear cached predictions after model update"""

# services/analytics_service.py
class AnalyticsService:
    async def calculate_season_accuracy(self, season: int) -> dict:
        """
        Calculate prediction accuracy metrics for season.
        Returns: {
            "season": int,
            "races_completed": int,
            "correct_winner_percentage": float,
            "top_3_accuracy": float,
            "average_brier_score": float,
            "by_race": list[dict]
        }
        """
    
    async def get_driver_rankings(self, season: int) -> list[dict]:
        """
        Retrieve driver rankings with ELO, points, wins.
        Uses materialized view for performance.
        """
    
    async def get_team_rankings(self, season: int) -> list[dict]:
        """Retrieve constructor standings"""
```

### ML Layer

```python
# ml/feature_engineering.py
class FeatureEngineering:
    def __init__(self, db_session: Session):
        self.db = db_session
    
    def extract_driver_features(self, driver_id: int, race_id: int) -> pd.Series:
        """
        Extract features for driver at race:
        - current_elo_rating
        - avg_position_last_5_races
        - wins_at_circuit
        - team_avg_position_last_5
        - qualifying_position (if available)
        Returns: pandas Series with feature names as index
        """
    
    def extract_weather_features(self, race_id: int) -> pd.Series:
        """
        Extract weather features:
        - temperature_celsius
        - is_wet (bool)
        - wind_speed_kph
        Returns: pandas Series
        """
    
    def build_feature_matrix(self, race_id: int) -> pd.DataFrame:
        """
        Build feature matrix for all drivers in race.
        Returns: DataFrame with shape (n_drivers, n_features)
        """

# ml/elo_calculator.py
class ELOCalculator:
    def __init__(self, k_factor: int = 32, base_rating: int = 1500):
        self.k_factor = k_factor
        self.base_rating = base_rating
    
    def calculate_expected_score(self, rating_a: int, rating_b: int) -> float:
        """Calculate expected score using ELO formula: 1 / (1 + 10^((Rb - Ra)/400))"""
    
    def update_ratings(self, race_result: list[tuple[int, int]]) -> dict[int, int]:
        """
        Update ELO ratings based on race finish positions.
        Args:
            race_result: List of (driver_id, final_position) tuples
        Returns:
            Dict mapping driver_id to new ELO rating
        """
    
    def get_rating_change(self, actual_position: int, expected_position: float) -> int:
        """Calculate ELO change based on actual vs expected performance"""

# ml/training.py
class ModelTrainer:
    def __init__(self, db_session: Session, s3_client: S3Client):
        self.db = db_session
        self.s3 = s3_client
    
    def prepare_training_data(self, start_season: int = 2010) -> tuple[pd.DataFrame, pd.Series]:
        """
        Prepare training data from historical races.
        Returns: (X_features, y_labels) where y is binary (1=winner, 0=not winner)
        """
    
    def train_random_forest(self, X: pd.DataFrame, y: pd.Series) -> RandomForestClassifier:
        """
        Train Random Forest with hyperparameters:
        - n_estimators=100
        - max_depth=10
        - min_samples_split=5
        - class_weight='balanced' (handle imbalanced classes)
        Returns: Trained model
        """
    
    def train_xgboost(self, X: pd.DataFrame, y: pd.Series) -> XGBClassifier:
        """
        Train XGBoost with hyperparameters:
        - learning_rate=0.1
        - n_estimators=200
        - max_depth=6
        - scale_pos_weight (handle class imbalance)
        Returns: Trained model
        """
    
    def evaluate_model(self, model, X_val: pd.DataFrame, y_val: pd.Series) -> dict:
        """
        Evaluate model on validation set.
        Returns: {"brier_score": float, "log_loss": float, "accuracy": float}
        """
    
    def save_model(self, model, model_type: str, version: str):
        """Save model to S3 with versioning: s3://bucket/models/{model_type}_{version}.pkl"""

# ml/inference.py
class InferenceEngine:
    def __init__(self, ensemble_model: EnsemblePredictor, feature_engineering: FeatureEngineering):
        self.model = ensemble_model
        self.feature_eng = feature_engineering
    
    def predict_race(self, race_id: int) -> list[tuple[int, float]]:
        """
        Generate predictions for race.
        Returns: List of (driver_id, win_probability) tuples, normalized to sum=100
        """
    
    def normalize_probabilities(self, raw_probs: np.ndarray) -> np.ndarray:
        """Normalize probabilities to sum to 100%"""
```

### Repository Layer

```python
# repositories/base.py
class BaseRepository(Generic[T]):
    def __init__(self, model: Type[T], db: Session):
        self.model = model
        self.db = db
    
    async def get_by_id(self, id: int) -> Optional[T]:
        """Retrieve entity by primary key"""
    
    async def get_all(self, skip: int = 0, limit: int = 100) -> list[T]:
        """Paginated retrieval"""
    
    async def create(self, obj: T) -> T:
        """Insert new entity"""
    
    async def update(self, id: int, updates: dict) -> T:
        """Update entity fields"""
    
    async def delete(self, id: int) -> bool:
        """Delete entity"""

# repositories/race_repository.py
class RaceRepository(BaseRepository[Race]):
    async def get_next_race(self) -> Optional[Race]:
        """Find next scheduled race after today"""
        return self.db.query(Race).filter(
            Race.status == "scheduled",
            Race.race_date >= datetime.now().date()
        ).order_by(Race.race_date).first()
    
    async def get_races_by_season(self, season: int) -> list[Race]:
        """Get all races for season ordered by round"""
    
    async def get_completed_races(self, season: int) -> list[Race]:
        """Get completed races for accuracy calculation"""
```

---

## 7. State Management

### Backend State Management

**Database as Source of Truth**:
- All persistent state stored in PostgreSQL (drivers, races, predictions, users)
- No in-memory application state (enables horizontal scaling)
- Database transactions ensure ACID properties for critical operations (ELO updates, prediction generation)

**Redis for Transient State**:
- **Prediction Cache**: Key format `predictions:race:{race_id}`, value: JSON serialized predictions, TTL: 7 days
- **User Sessions**: Key format `session:{user_id}`, value: JWT metadata, TTL: 24 hours
- **Rate Limit Counters**: Key format `rate_limit:{user_id}`, value: request count, TTL: 60 seconds
- **Cache Invalidation**: Pub/Sub pattern - when new predictions generated, publish message to invalidate race cache

**Celery Task State**:
- Task results stored in Redis backend
- Task states: PENDING, STARTED, SUCCESS, FAILURE, RETRY
- Retry logic with exponential backoff for failed ingestion/training tasks

### Frontend State Management

**React Query for Server State**:
```typescript
// Query cache configuration
const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      staleTime: 1000 * 60 * 5, // 5 minutes
      cacheTime: 1000 * 60 * 30, // 30 minutes
      refetchOnWindowFocus: false,
      retry: 3,
    },
  },
});

// Example query with automatic caching
const { data: predictions } = useQuery({
  queryKey: ['predictions', 'next-race'],
  queryFn: fetchNextRacePredictions,
  staleTime: 1000 * 60 * 60, // Predictions valid for 1 hour
});
```

**Context API for Client State**:
- `AuthContext`: JWT token, user profile, login/logout functions
- `ThemeContext`: Dark/light mode preference (persisted to localStorage)

**LocalStorage for Persistence**:
- JWT token stored at key `f1_analytics_jwt`
- Theme preference stored at key `f1_analytics_theme`
- Cleared on logout

---

## 8. Error Handling Strategy

### Backend Error Handling

**HTTP Error Codes**:
- `400 Bad Request`: Invalid request parameters (e.g., malformed email, invalid season)
- `401 Unauthorized`: Missing or invalid JWT token
- `403 Forbidden`: Valid token but insufficient permissions (admin-only endpoints)
- `404 Not Found`: Resource doesn't exist (e.g., race_id not found)
- `409 Conflict`: Resource conflict (e.g., email already registered)
- `429 Too Many Requests`: Rate limit exceeded
- `500 Internal Server Error`: Unhandled exceptions, database errors
- `503 Service Unavailable`: Dependent service down (Ergast API, Redis)

**Global Exception Handler**:
```python
# middleware/error_handler.py
from fastapi import Request, HTTPException
from fastapi.responses import JSONResponse

@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    # Log full traceback for debugging
    logger.exception(f"Unhandled exception: {exc}")
    
    # Return sanitized error to user
    if isinstance(exc, HTTPException):
        return JSONResponse(
            status_code=exc.status_code,
            content={"error": exc.detail, "error_code": exc.status_code}
        )
    
    # Hide internal errors from users
    return JSONResponse(
        status_code=500,
        content={"error": "Internal server error", "error_code": 500}
    )
```

**Service-Specific Errors**:
```python
class PredictionServiceError(Exception):
    """Base exception for prediction service"""

class ModelNotFoundError(PredictionServiceError):
    """Raised when ML model file not found in S3"""

class InferenceError(PredictionServiceError):
    """Raised when model inference fails"""

# Usage in service
try:
    model = load_model_from_s3(version)
except FileNotFoundError:
    raise ModelNotFoundError(f"Model version {version} not found")
```

**Retry Logic for External APIs**:
```python
# data_ingestion/ergast_client.py
@retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=2, max=10),
    retry=retry_if_exception_type(httpx.HTTPStatusError)
)
async def fetch_race_results(self, season: int, round: int) -> dict:
    response = await self.session.get(f"/api/f1/{season}/{round}/results.json")
    response.raise_for_status()
    return response.json()
```

**Graceful Degradation**:
- If Redis cache unavailable, bypass cache and query database directly (slower but functional)
- If ML model inference fails, return last successfully cached predictions with warning
- If data ingestion fails, alert admins but don't block API serving cached data

### Frontend Error Handling

**API Error Responses**:
```typescript
// api/client.ts
import axios from 'axios';

const apiClient = axios.create({
  baseURL: import.meta.env.VITE_API_URL,
});

apiClient.interceptors.response.use(
  response => response,
  error => {
    if (error.response?.status === 401) {
      // Token expired, redirect to login
      localStorage.removeItem('f1_analytics_jwt');
      window.location.href = '/f1-analytics/login';
    } else if (error.response?.status === 429) {
      // Rate limit exceeded
      toast.error('Too many requests. Please try again later.');
    } else if (error.response?.status >= 500) {
      // Server error
      toast.error('Server error. Please try again later.');
    }
    return Promise.reject(error);
  }
);
```

**React Error Boundaries**:
```typescript
// components/common/ErrorBoundary.tsx
export class ErrorBoundary extends React.Component<Props, State> {
  state = { hasError: false, error: null };
  
  static getDerivedStateFromError(error: Error) {
    return { hasError: true, error };
  }
  
  componentDidCatch(error: Error, errorInfo: ErrorInfo) {
    console.error('React error boundary caught:', error, errorInfo);
  }
  
  render() {
    if (this.state.hasError) {
      return (
        <div className="error-container">
          <h1>Something went wrong</h1>
          <button onClick={() => window.location.reload()}>Reload Page</button>
        </div>
      );
    }
    return this.props.children;
  }
}
```

**User-Friendly Messages**:
- Network errors: "Unable to connect to server. Check your internet connection."
- Validation errors: Display field-specific messages (e.g., "Password must be at least 8 characters")
- Not found errors: "No predictions available for this race yet."

---

## 9. Test Plan

### Unit Tests

**Backend Unit Tests** (pytest):

```python
# tests/unit/test_elo_calculator.py
def test_elo_expected_score():
    calculator = ELOCalculator()
    # Equal ratings should give 0.5 expected score
    assert calculator.calculate_expected_score(1500, 1500) == pytest.approx(0.5)
    # Higher rating should have higher expected score
    assert calculator.calculate_expected_score(1600, 1500) > 0.5

def test_elo_update_ratings():
    calculator = ELOCalculator(k_factor=32)
    race_result = [(1, 1), (2, 2), (3, 3)]  # (driver_id, position)
    initial_ratings = {1: 1500, 2: 1500, 3: 1500}
    
    new_ratings = calculator.update_ratings(race_result, initial_ratings)
    # Winner should gain points, losers should lose points
    assert new_ratings[1] > 1500
    assert new_ratings[3] < 1500

# tests/unit/test_services.py
@pytest.mark.asyncio
async def test_auth_service_create_user(db_session):
    auth_service = AuthService(UserRepository(db_session), JWTManager())
    user_data = UserRegisterRequest(email="test@example.com", password="SecurePass123")
    
    user = await auth_service.create_user(user_data)
    assert user.email == "test@example.com"
    assert user.password_hash != "SecurePass123"  # Should be hashed

@pytest.mark.asyncio
async def test_prediction_service_get_next_race(db_session):
    # Seed database with test races
    future_race = Race(season_year=2026, round_number=5, race_date=date.today() + timedelta(days=7), status="scheduled")
    db_session.add(future_race)
    db_session.commit()
    
    prediction_service = PredictionService(...)
    next_race = await prediction_service.get_next_race()
    assert next_race.race_id == future_race.race_id

# tests/unit/test_feature_engineering.py
def test_extract_driver_features(db_session):
    feature_eng = FeatureEngineering(db_session)
    features = feature_eng.extract_driver_features(driver_id=1, race_id=100)
    
    assert "current_elo_rating" in features.index
    assert "avg_position_last_5_races" in features.index
    assert features["current_elo_rating"] > 0
```

**Frontend Unit Tests** (Vitest + React Testing Library):

```typescript
// tests/unit/components.test.tsx
import { render, screen } from '@testing-library/react';
import { DriverProbabilityBar } from '@/components/predictions/DriverProbabilityBar';

test('renders driver name and probability', () => {
  render(
    <DriverProbabilityBar 
      driverName="Max Verstappen" 
      probability={35.2} 
      teamColor="#0600EF" 
    />
  );
  
  expect(screen.getByText('Max Verstappen')).toBeInTheDocument();
  expect(screen.getByText('35.2%')).toBeInTheDocument();
});

test('probability bar width matches percentage', () => {
  const { container } = render(
    <DriverProbabilityBar driverName="Test" probability={50} teamColor="#000" />
  );
  
  const bar = container.querySelector('[style*="width: 50%"]');
  expect(bar).toBeInTheDocument();
});
```

**Coverage Target**: 80% line coverage for critical paths (auth, prediction generation, ELO calculation)

### Integration Tests

**API Endpoint Integration Tests**:

```python
# tests/integration/test_api_endpoints.py
from fastapi.testclient import TestClient

@pytest.fixture
def client():
    return TestClient(app)

@pytest.fixture
def auth_token(client):
    # Register and login to get token
    client.post("/api/v1/auth/register", json={"email": "test@test.com", "password": "Pass123"})
    response = client.post("/api/v1/auth/login", json={"email": "test@test.com", "password": "Pass123"})
    return response.json()["token"]

def test_get_next_race_predictions_authenticated(client, auth_token, db_session):
    # Seed database with race and predictions
    race = create_test_race(db_session)
    create_test_predictions(db_session, race.race_id)
    
    response = client.get(
        "/api/v1/predictions/next-race",
        headers={"Authorization": f"Bearer {auth_token}"}
    )
    assert response.status_code == 200
    data = response.json()
    assert data["race_id"] == race.race_id
    assert len(data["predictions"]) > 0
    assert sum(p["win_probability"] for p in data["predictions"]) == pytest.approx(100, rel=0.1)

def test_get_predictions_unauthenticated(client):
    response = client.get("/api/v1/predictions/next-race")
    assert response.status_code == 401

def test_rate_limiting(client, auth_token):
    # Send 101 requests rapidly
    for i in range(101):
        response = client.get("/api/v1/races/calendar", headers={"Authorization": f"Bearer {auth_token}"})
        if i < 100:
            assert response.status_code == 200
        else:
            assert response.status_code == 429  # Rate limit exceeded
```

**Data Ingestion Pipeline Tests**:

```python
# tests/integration/test_ingestion_pipeline.py
@pytest.mark.asyncio
async def test_ergast_ingestion_workflow(db_session, mock_ergast_api):
    # Mock Ergast API responses
    mock_ergast_api.get("/api/f1/2025/1/results.json").return_value = mock_race_results_json
    
    # Run ingestion
    ingestion_service = DataIngestionService(db_session, ErgastClient())
    await ingestion_service.ingest_race_results(season=2025, round=1)
    
    # Verify data in database
    race = db_session.query(Race).filter_by(season_year=2025, round_number=1).first()
    assert race is not None
    assert len(race.race_results) == 20  # 20 drivers

@pytest.mark.asyncio
async def test_weather_ingestion(db_session, mock_weather_api):
    mock_weather_api.get("/data/2.5/weather").return_value = {"temp": 25, "weather": [{"main": "Clear"}]}
    
    weather_service = WeatherIngestionService(db_session, WeatherClient())
    await weather_service.ingest_weather(race_id=1)
    
    weather = db_session.query(WeatherData).filter_by(race_id=1).first()
    assert weather.temperature_celsius == 25
    assert weather.conditions == "dry"
```

**ML Training Integration Tests**:

```python
# tests/integration/test_ml_training.py
def test_end_to_end_training_pipeline(db_session, s3_mock):
    # Seed database with historical race data
    seed_historical_races(db_session, seasons=[2020, 2021, 2022])
    
    # Run training
    trainer = ModelTrainer(db_session, s3_mock)
    rf_model, xgb_model = trainer.train_models()
    
    # Verify models saved to S3
    assert s3_mock.object_exists("models/random_forest_v1.pkl")
    assert s3_mock.object_exists("models/xgboost_v1.pkl")
    
    # Verify model can make predictions
    inference_engine = InferenceEngine(EnsemblePredictor(...), ...)
    predictions = inference_engine.predict_race(race_id=100)
    assert len(predictions) == 20  # 20 drivers
    assert all(0 <= prob <= 100 for _, prob in predictions)
```

### E2E Tests

**Frontend E2E Tests** (Playwright):

```typescript
// tests/e2e/prediction-flow.spec.ts
import { test, expect } from '@playwright/test';

test('user can view next race predictions', async ({ page }) => {
  // Navigate to homepage
  await page.goto('http://localhost:5173/f1-analytics');
  
  // Should redirect to login if not authenticated
  await expect(page).toHaveURL(/.*login/);
  
  // Login
  await page.fill('input[name="email"]', 'test@example.com');
  await page.fill('input[name="password"]', 'SecurePass123');
  await page.click('button[type="submit"]');
  
  // Should redirect to homepage after login
  await expect(page).toHaveURL('http://localhost:5173/f1-analytics');
  
  // Wait for predictions to load
  await page.waitForSelector('[data-testid="prediction-card"]');
  
  // Verify predictions displayed
  const predictions = await page.locator('[data-testid="driver-probability"]').count();
  expect(predictions).toBeGreaterThan(0);
  
  // Verify race details shown
  await expect(page.locator('[data-testid="race-name"]')).toBeVisible();
  await expect(page.locator('[data-testid="race-date"]')).toBeVisible();
});

test('user can export predictions', async ({ page }) => {
  await page.goto('http://localhost:5173/f1-analytics');
  // Assume user is logged in
  
  // Click export button
  const downloadPromise = page.waitForEvent('download');
  await page.click('[data-testid="export-csv-button"]');
  const download = await downloadPromise;
  
  // Verify file downloaded
  expect(download.suggestedFilename()).toMatch(/predictions.*\.csv/);
});
```

**Performance Tests**:
```python
# tests/performance/test_load.py
from locust import HttpUser, task, between

class F1AnalyticsUser(HttpUser):
    wait_time = between(1, 3)
    
    def on_start(self):
        # Login to get token
        response = self.client.post("/api/v1/auth/login", json={
            "email": "load_test@example.com",
            "password": "Pass123"
        })
        self.token = response.json()["token"]
    
    @task(3)
    def get_predictions(self):
        self.client.get(
            "/api/v1/predictions/next-race",
            headers={"Authorization": f"Bearer {self.token}"}
        )
    
    @task(1)
    def get_calendar(self):
        self.client.get("/api/v1/races/calendar?season=2026")

# Run with: locust -f tests/performance/test_load.py --users 1000 --spawn-rate 50
# Target: <500ms p95 latency at 1000 concurrent users
```

---

## 10. Migration Strategy

### Phase 1: Infrastructure Setup (Week 1)

1. **Provision Cloud Resources**:
   - Create AWS EKS cluster via Terraform
   - Provision RDS PostgreSQL instance (db.r5.large, Multi-AZ)
   - Create ElastiCache Redis cluster (cache.r5.large, 3 nodes)
   - Set up S3 buckets for model storage and backups
   - Configure VPC, subnets, security groups

2. **Deploy Base Services**:
   - Deploy PostgreSQL with initial schema via Alembic
   - Deploy Redis with basic configuration
   - Set up RabbitMQ or AWS SQS for message queue
   - Configure monitoring (Prometheus, Grafana, ELK stack)

3. **CI/CD Pipeline**:
   - Create GitHub Actions workflows for backend/frontend
   - Set up Docker image registry (AWS ECR)
   - Configure staging and production environments
   - Implement blue-green deployment strategy

### Phase 2: Data Migration (Week 2)

1. **Historical Data Ingestion**:
   - Run `scripts/seed_data.py` to fetch F1 data from 2010-present via Ergast API
   - Batch import race results, qualifying times, driver/team profiles
   - Import weather data for historical races
   - Validate data integrity (foreign keys, null checks)

2. **Initial ELO Calculation**:
   - Run ELO calculator on all historical races in chronological order
   - Persist ELO ratings to drivers and teams tables
   - Verify ratings are reasonable (top drivers >2000, rookies ~1500)

3. **Data Quality Checks**:
   - Verify all races have results and weather data
   - Check for missing drivers or teams
   - Validate qualifying-race linkage

### Phase 3: ML Model Training (Week 2-3)

1. **Feature Engineering**:
   - Extract features from historical data
   - Generate training dataset (80/20 train/val split)
   - Validate feature distributions (no NaNs, outliers)

2. **Model Training**:
   - Train Random Forest and XGBoost on historical data
   - Evaluate on validation set (target Brier score <0.20)
   - Hyperparameter tuning via grid search
   - Save trained models to S3 with version v1.0.0

3. **Generate Historical Predictions**:
   - Backtest models on past seasons (2023-2025)
   - Calculate accuracy metrics to validate model quality
   - Persist predictions and accuracy to database

### Phase 4: Backend Deployment (Week 3-4)

1. **Deploy API Gateway**:
   - Build Docker image for FastAPI application
   - Deploy to Kubernetes with 3 replicas
   - Configure load balancer and ingress
   - Test API endpoints with Postman/curl

2. **Deploy Prediction Service**:
   - Deploy inference service with model loading from S3
   - Configure Redis caching
   - Test prediction generation for upcoming race

3. **Deploy Data Ingestion Service**:
   - Deploy Airflow with daily ingestion DAG
   - Schedule first run to verify end-to-end workflow
   - Configure alerting for ingestion failures

### Phase 5: Frontend Deployment (Week 4)

1. **Build and Deploy Dashboard**:
   - Build React app with Vite (`npm run build`)
   - Deploy to Nginx container or AWS S3 + CloudFront
   - Configure API_URL environment variable
   - Test authentication and data fetching

2. **Integration Testing**:
   - Run E2E tests in staging environment
   - Verify all features work end-to-end
   - Load test with 1000 concurrent users

### Phase 6: Production Launch (Week 5)

1. **Pre-Launch Checklist**:
   - Database backups configured and tested
   - Monitoring dashboards validated
   - Alert routing to PagerDuty/Slack confirmed
   - Security scan (OWASP ZAP) passed
   - SSL/TLS certificates installed

2. **Gradual Rollout**:
   - Deploy to production with traffic routing disabled
   - Smoke test critical paths
   - Enable traffic routing with canary (10% users)
   - Monitor error rates and latency for 24 hours
   - Full rollout if metrics healthy

3. **Post-Launch Monitoring**:
   - Monitor system metrics for first week
   - Track prediction accuracy as new races complete
   - Gather user feedback for improvements

---

## 11. Rollback Plan

### Automated Rollback Triggers

**Health Check Failures**:
- If >50% of pods fail readiness checks for 5 minutes, trigger automatic rollback
- If API error rate >10% for 3 minutes, rollback to previous version

**Performance Degradation**:
- If p95 latency exceeds 2 seconds for 5 minutes, rollback
- If database connection pool exhausted, rollback and investigate

### Manual Rollback Procedures

**Kubernetes Rollback**:
```bash
# Rollback to previous deployment
kubectl rollout undo deployment/api-gateway -n production
kubectl rollout undo deployment/prediction-service -n production
kubectl rollout undo deployment/frontend -n production

# Verify rollback status
kubectl rollout status deployment/api-gateway -n production

# Check pod health
kubectl get pods -n production -w
```

**Database Rollback**:
```bash
# Rollback Alembic migration
alembic downgrade -1

# Restore database from backup (if data corruption)
pg_restore -h db-host -U admin -d f1_analytics /backups/f1_analytics_2026_02_11.dump
```

**Model Rollback**:
```python
# Update model version pointer in database to previous version
UPDATE model_metadata SET active_version = 'v1.2.0' WHERE id = 1;

# Clear Redis cache to force reload
FLUSHDB
```

### Rollback Testing

**Pre-Deployment**:
- Test rollback procedure in staging environment
- Verify previous version still functional after rollback
- Document rollback time (target: <5 minutes)

**Post-Rollback**:
- Verify all services healthy
- Check data integrity (no data loss)
- Analyze root cause of failure
- Create post-mortem document

---

## 12. Performance Considerations

### Database Optimizations

**Indexing Strategy**:
```sql
-- Composite indexes for common queries
CREATE INDEX idx_races_season_status ON races(season_year, status);
CREATE INDEX idx_predictions_race_prob ON predictions(race_id, predicted_win_probability DESC);
CREATE INDEX idx_race_results_driver_date ON race_results(driver_id, race_id);

-- Partial index for active races
CREATE INDEX idx_races_upcoming ON races(race_date) WHERE status = 'scheduled';
```

**Query Optimization**:
- Use `EXPLAIN ANALYZE` to identify slow queries
- Implement materialized views for complex aggregations (driver rankings, accuracy metrics)
- Refresh materialized views daily via cron job
- Use database connection pooling (max 20 connections per service)

**Partitioning**:
- Partition `race_results` and `predictions` tables by race_id range
- Prune old partitions (pre-2018) to archive storage

### Caching Strategy

**Redis Caching Layers**:
1. **Prediction Cache**: TTL 7 days, invalidate on new model deployment
2. **Race Calendar Cache**: TTL 24 hours, invalidate on schedule updates
3. **Driver Rankings Cache**: TTL 1 hour, invalidate on race completion
4. **Query Result Cache**: Cache expensive database queries (top 10 drivers, season standings)

**Cache Warming**:
- Pre-warm cache with next race predictions on deployment
- Background job refreshes frequently accessed data (driver rankings) hourly

**Cache Eviction**:
- LRU eviction policy for memory management
- Monitor cache hit ratio (target >80%)

### API Performance

**Response Optimization**:
- Enable gzip compression for API responses (reduces payload by ~70%)
- Implement pagination for large result sets (max 100 records per page)
- Use HTTP caching headers (ETag, Cache-Control) for static data

**Async Processing**:
- Use FastAPI's async/await for non-blocking I/O
- Background tasks (Celery) for expensive operations (model training, data export)
- Streaming responses for file downloads

### Frontend Performance

**Code Splitting**:
```typescript
// Lazy load routes
const CalendarPage = lazy(() => import('./pages/CalendarPage'));
const AnalyticsPage = lazy(() => import('./pages/AnalyticsPage'));

<Route path="calendar" element={<Suspense fallback={<Spinner />}><CalendarPage /></Suspense>} />
```

**Asset Optimization**:
- Minify and bundle JavaScript/CSS with Vite
- Compress images (WebP format, lazy loading)
- Use CDN for static asset delivery (CloudFront)
- Implement service worker for offline caching

**React Optimization**:
- Memoize expensive components with `React.memo`
- Use `useMemo` for expensive calculations (probability sorting)
- Debounce search inputs to reduce API calls

### ML Inference Performance

**Model Optimization**:
- Use GPU acceleration for XGBoost training (NVIDIA T4)
- Quantize models to reduce size and inference time (int8 quantization)
- Batch predictions for all drivers in single inference call

**Feature Caching**:
- Cache feature extraction results in Redis (driver stats, weather data)
- Recompute features only when underlying data changes

### Monitoring Performance

**Key Metrics**:
- API latency: p50, p95, p99 per endpoint
- Database query execution time (slow query log)
- Cache hit ratio (target >80%)
- Model inference time (target <5 seconds)
- Frontend page load time (target <2 seconds)

**Alerting Thresholds**:
- Warning: p95 latency >1 second
- Critical: p95 latency >2 seconds or error rate >5%
