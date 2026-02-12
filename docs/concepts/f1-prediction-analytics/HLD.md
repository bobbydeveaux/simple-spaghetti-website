# High-Level Design: simple-spaghetti-repo

**Created:** 2026-02-12T22:42:57Z
**Status:** Draft

## 1. Architecture Overview

The system follows a **three-tier monolithic architecture** with clear separation between data ingestion, prediction engine, and presentation layers. This design prioritizes simplicity and maintainability while supporting the required ML workflows.

**Architecture Pattern:** Layered monolith with asynchronous task processing

- **Data Layer:** PostgreSQL database storing historical F1 data, predictions, and model metadata
- **Application Layer:** Python-based backend handling API requests, data ingestion, and ML model orchestration
- **Presentation Layer:** JavaScript SPA (Single Page Application) serving the dashboard interface
- **Background Processing:** Celery task queue for scheduled data imports and model retraining

**Rationale:** A monolithic approach reduces operational complexity for a data-driven application where components share the same database and ML pipeline. Celery provides asynchronous processing without introducing microservices complexity.

---

## 2. System Components

### 2.1 Data Ingestion Service
Scheduled jobs that fetch data from external APIs and populate the database. Implements retry logic and rate limiting.

**Responsibilities:**
- Import race results, qualifying data, standings from Ergast API
- Fetch historical and forecast weather data
- Store track characteristics and metadata
- Trigger prediction pipeline after data updates

### 2.2 Prediction Engine
Core ML module containing multiple prediction models and ensemble logic.

**Responsibilities:**
- Train and persist regression, Random Forest, XGBoost models
- Calculate ELO ratings for drivers and constructors
- Generate track-specific performance coefficients
- Produce win probability predictions with confidence intervals
- Log predictions for accuracy tracking

### 2.3 Web API Service
RESTful API exposing endpoints for dashboard consumption.

**Responsibilities:**
- Serve prediction data for upcoming races
- Provide historical accuracy metrics
- Deliver driver/constructor standings
- Return calendar and schedule information
- Cache frequently accessed data

### 2.4 Dashboard Application
Client-side SPA rendering interactive visualizations and prediction tables.

**Responsibilities:**
- Display win probability predictions
- Render performance charts and trends
- Show model comparison views
- Present F1 calendar with prediction status
- Visualize historical accuracy metrics

### 2.5 Task Scheduler
Celery worker pool executing background jobs on defined schedules.

**Responsibilities:**
- Schedule post-race data imports (24-hour window)
- Trigger model retraining after new data availability
- Execute periodic health checks on external APIs
- Clean up expired cache entries

---

## 3. Data Model

### 3.1 Core Entities

**Seasons**
- `season_id` (PK), `year`, `race_count`

**Races**
- `race_id` (PK), `season_id` (FK), `circuit_id` (FK), `name`, `date`, `round_number`

**Circuits**
- `circuit_id` (PK), `name`, `location`, `country`, `length_km`, `turn_count`, `elevation_profile_json`

**Drivers**
- `driver_id` (PK), `name`, `nationality`, `date_of_birth`, `driver_code`

**Constructors**
- `constructor_id` (PK), `name`, `nationality`, `headquarters`

**RaceResults**
- `result_id` (PK), `race_id` (FK), `driver_id` (FK), `constructor_id` (FK), `grid_position`, `finish_position`, `points`, `fastest_lap_time`

**QualifyingResults**
- `qualifying_id` (PK), `race_id` (FK), `driver_id` (FK), `q1_time`, `q2_time`, `q3_time`, `grid_position`

**WeatherData**
- `weather_id` (PK), `race_id` (FK), `temperature_c`, `precipitation_mm`, `wind_speed_kmh`, `conditions_text`

**DriverStandings**
- `standing_id` (PK), `race_id` (FK), `driver_id` (FK), `position`, `points`, `wins`

**ConstructorStandings**
- `standing_id` (PK), `race_id` (FK), `constructor_id` (FK), `position`, `points`, `wins`

### 3.2 Prediction Entities

**Predictions**
- `prediction_id` (PK), `race_id` (FK), `model_id` (FK), `driver_id` (FK), `win_probability`, `confidence_interval_lower`, `confidence_interval_upper`, `created_at`

**Models**
- `model_id` (PK), `name`, `type` (regression/random_forest/xgboost/elo), `version`, `trained_at`, `hyperparameters_json`

**ModelAccuracy**
- `accuracy_id` (PK), `model_id` (FK), `race_id` (FK), `brier_score`, `top3_accuracy`, `predicted_winner_id`, `actual_winner_id`

**EloRatings**
- `rating_id` (PK), `driver_id` (FK), `constructor_id` (FK), `race_id` (FK), `rating_value`, `calculated_at`

### 3.3 Key Relationships

- One Season has many Races
- One Circuit hosts many Races
- One Race has many RaceResults, QualifyingResults, Predictions
- One Driver/Constructor has many Ratings across Races
- One Model generates many Predictions

---

## 4. API Contracts

### 4.1 Prediction Endpoints

**GET /api/v1/predictions/next-race**
```json
Response 200:
{
  "race": {
    "race_id": 1045,
    "name": "Monaco Grand Prix",
    "date": "2026-05-24",
    "circuit": "Circuit de Monaco"
  },
  "predictions": [
    {
      "driver": "Max Verstappen",
      "constructor": "Red Bull Racing",
      "win_probability": 0.34,
      "confidence_interval": [0.28, 0.40],
      "model": "ensemble"
    }
  ],
  "generated_at": "2026-05-22T14:30:00Z"
}
```

**GET /api/v1/predictions/race/{race_id}**
Query params: `model_id` (optional)

**GET /api/v1/predictions/compare/{race_id}**
Returns predictions from all models for comparison.

### 4.2 Standings Endpoints

**GET /api/v1/standings/drivers**
```json
Response 200:
{
  "season": 2026,
  "standings": [
    {
      "position": 1,
      "driver": "Max Verstappen",
      "constructor": "Red Bull Racing",
      "points": 195,
      "wins": 7
    }
  ]
}
```

**GET /api/v1/standings/constructors**

### 4.3 Calendar Endpoints

**GET /api/v1/calendar/{year}**
```json
Response 200:
{
  "season": 2026,
  "races": [
    {
      "round": 8,
      "name": "Monaco Grand Prix",
      "date": "2026-05-24",
      "circuit": "Circuit de Monaco",
      "prediction_available": true
    }
  ]
}
```

### 4.4 Analytics Endpoints

**GET /api/v1/analytics/model-accuracy**
Query params: `model_id`, `season`

**GET /api/v1/analytics/driver-performance/{driver_id}**
Returns historical performance metrics and ELO evolution.

**GET /api/v1/analytics/track-coefficients/{circuit_id}**

---

## 5. Technology Stack

### Backend

- **Language:** Python 3.11+
- **Framework:** Flask 3.x (lightweight, suitable for API-driven architecture)
- **ML Libraries:** scikit-learn 1.4+, XGBoost 2.0+, NumPy 1.26+, Pandas 2.2+
- **Task Queue:** Celery 5.3+ with Redis as broker
- **ORM:** SQLAlchemy 2.0 for database interactions
- **HTTP Client:** Requests 2.31+ with retry decorators for external API calls
- **Validation:** Marshmallow 3.x for request/response schemas

### Frontend

- **Framework:** React 18+ with functional components and hooks
- **Charting:** Chart.js 4.x for performance and simplicity
- **State Management:** React Context API (sufficient for read-heavy dashboard)
- **HTTP Client:** Axios with interceptors for error handling
- **Styling:** Tailwind CSS for rapid UI development
- **Build Tool:** Vite for fast development and optimized builds

### Infrastructure

- **Container Runtime:** Docker with Docker Compose for local development
- **Orchestration:** Kubernetes (minimal setup: 2-3 nodes) or single-server Docker deployment
- **Reverse Proxy:** Nginx for static file serving and API proxying
- **Process Manager:** Supervisor for managing Flask/Celery processes
- **Scheduler:** Celery Beat for periodic task execution

### Data Storage

- **Primary Database:** PostgreSQL 15+ with TimescaleDB extension for time-series optimization
- **Cache:** Redis 7.x for API response caching and Celery message broker
- **Model Storage:** Local filesystem or S3-compatible object storage for trained model artifacts
- **Backup:** pg_dump scheduled backups with point-in-time recovery capability

---

## 6. Integration Points

### 6.1 Ergast Developer API
- **URL:** `http://ergast.com/api/f1`
- **Rate Limit:** 200 requests/hour (4 requests/minute)
- **Data Fetched:** Race results, qualifying times, driver/constructor standings, race schedule
- **Format:** JSON and XML (prefer JSON)
- **Error Handling:** Exponential backoff retry (1s, 2s, 4s, 8s), fallback to cached data
- **Update Frequency:** Post-race imports within 24 hours, schedule refreshes weekly

### 6.2 Weather API (OpenWeatherMap)
- **Endpoints:** Historical Weather API, 5-day forecast API
- **Authentication:** API key in request parameters
- **Data Fetched:** Temperature, precipitation, wind speed, conditions
- **Rate Limit:** 1000 calls/day (free tier)
- **Error Handling:** Graceful degradation if weather unavailable (predictions still generated)

### 6.3 Internal Event Bus
- **Mechanism:** Celery task chains
- **Events:**
  - `data.imported` → triggers model retraining
  - `model.trained` → triggers prediction generation
  - `prediction.generated` → invalidates API cache
- **Purpose:** Coordinate pipeline stages without tight coupling

---

## 7. Security Architecture

### 7.1 Authentication & Authorization
- **Phase 1 (MVP):** No user authentication (public read-only dashboard)
- **Admin Access:** Basic HTTP authentication for admin endpoints (model management, manual imports)
- **Future:** OAuth2/JWT if user accounts added post-MVP

### 7.2 API Security
- **Rate Limiting:** 100 requests/minute per IP address using Flask-Limiter
- **CORS:** Whitelist dashboard domain only
- **Input Validation:** Marshmallow schemas validate all API inputs
- **SQL Injection:** SQLAlchemy ORM with parameterized queries

### 7.3 External API Security
- **HTTPS Only:** Enforce TLS 1.2+ for all external API calls
- **Certificate Validation:** Enabled by default in Requests library
- **API Key Storage:** Environment variables loaded from .env files
- **Secrets Management:** Docker secrets or Kubernetes secrets for production

### 7.4 Database Security
- **Credentials:** Environment variables, never committed to source control
- **Network Isolation:** Database accessible only from application containers
- **Principle of Least Privilege:** Application user has SELECT/INSERT/UPDATE only (no DROP/ALTER)
- **Encryption at Rest:** PostgreSQL with LUKS disk encryption

### 7.5 DDoS Protection
- **Nginx Rate Limiting:** Connection and request rate limits
- **CloudFlare (Optional):** CDN with DDoS mitigation for production
- **Graceful Degradation:** Return cached predictions if database overloaded

---

## 8. Deployment Architecture

### 8.1 Container Strategy
- **Images:**
  - `f1-api`: Flask application + ML dependencies
  - `f1-worker`: Celery workers with same dependencies
  - `f1-frontend`: Nginx serving React build artifacts
  - `postgres:15`: Official PostgreSQL image
  - `redis:7-alpine`: Official Redis image

### 8.2 Development Environment
```yaml
docker-compose.yml:
  - postgres (port 5432)
  - redis (port 6379)
  - api (port 5000)
  - celery-worker (3 instances)
  - celery-beat (1 instance)
  - frontend (port 3000, dev server)
```

### 8.3 Production Deployment Options

**Option A: Single-Server Deployment**
- Docker Compose on a single VPS (8GB RAM, 4 vCPUs)
- Nginx reverse proxy terminating SSL
- Suitable for MVP with <10k monthly users

**Option B: Kubernetes Cluster**
- Deployments: api (2 replicas), worker (3 replicas), frontend (2 replicas)
- Services: ClusterIP for internal, LoadBalancer for frontend
- StatefulSet for PostgreSQL with persistent volume
- ConfigMaps for environment configuration
- Secrets for sensitive credentials

### 8.4 CI/CD Pipeline
- **GitHub Actions:** Build, test, push Docker images
- **Automated Tests:** Unit tests for prediction logic, integration tests for API
- **Deployment:** Rolling updates with health checks
- **Rollback:** Automated rollback if health checks fail post-deployment

---

## 9. Scalability Strategy

### 9.1 Horizontal Scaling
- **API Service:** Stateless, scales horizontally behind load balancer
- **Celery Workers:** Add workers to handle increased data import/model training load
- **Frontend:** Static assets served via CDN, scales trivially

### 9.2 Database Scaling
- **Read Replicas:** Add PostgreSQL read replicas for dashboard queries (writes are infrequent)
- **Connection Pooling:** PgBouncer or SQLAlchemy pooling (pool size: 20 connections)
- **Indexing Strategy:** Indexes on `race_id`, `driver_id`, `date`, `season_id`
- **Partitioning:** Partition predictions table by season if exceeds 10M rows

### 9.3 Caching Strategy
- **L1 Cache:** In-memory LRU cache in Flask app (TTL: 5 minutes)
- **L2 Cache:** Redis cache for API responses (TTL: 1 hour for predictions, 24 hours for historical data)
- **Cache Invalidation:** Event-driven invalidation when new predictions generated

### 9.4 Performance Optimization
- **Model Serving:** Preload trained models into memory, avoid disk I/O per request
- **Batch Predictions:** Generate predictions for all drivers in single model inference
- **Database Query Optimization:** Use `JOIN`s strategically, `EXPLAIN ANALYZE` for slow queries
- **Pagination:** Limit API responses to 50 records, provide pagination links

### 9.5 Auto-Scaling (Kubernetes)
- **Horizontal Pod Autoscaler:** Scale API pods based on CPU >70%
- **Celery Autoscaling:** KEDA (Kubernetes Event Driven Autoscaling) based on Redis queue length
- **Thresholds:** Scale up at 100 requests/second, scale down after 5 minutes below threshold

---

## 10. Monitoring & Observability

### 10.1 Logging
- **Format:** JSON structured logs with timestamp, level, service, trace_id
- **Levels:** INFO for requests, WARNING for retries, ERROR for failures
- **Centralization:** Ship logs to Elasticsearch/CloudWatch or simple file rotation for MVP
- **Sensitive Data:** Never log API keys, mask driver names in debug logs

### 10.2 Metrics
- **Application Metrics (Prometheus):**
  - API request latency (p50, p95, p99)
  - Prediction generation time
  - Model inference duration
  - Cache hit/miss ratio
  - Celery task queue length
- **System Metrics:** CPU, memory, disk I/O per container
- **Business Metrics:** Predictions generated per day, unique dashboard visitors

### 10.3 Tracing
- **Tool:** OpenTelemetry with Jaeger (optional for MVP)
- **Traces:** End-to-end traces for data import → model training → prediction generation

### 10.4 Alerting
- **Alert Manager:** Prometheus Alertmanager or PagerDuty
- **Critical Alerts:**
  - API 5xx error rate >1%
  - Database connection failures
  - Ergast API unreachable for >1 hour
  - Prediction generation failure
  - Disk usage >85%
- **Warning Alerts:**
  - API latency p95 >2 seconds
  - Model accuracy drops below 20%
  - Celery queue backlog >50 tasks

### 10.5 Health Checks
- **Endpoints:**
  - `/health/live`: Kubernetes liveness probe (app running?)
  - `/health/ready`: Readiness probe (database connected, Redis available?)
- **Dashboard Health:** Synthetic monitoring pinging dashboard every 5 minutes

---

## 11. Architectural Decisions (ADRs)

### ADR-001: Monolith over Microservices
**Decision:** Build as a monolithic application with modular code structure.

**Rationale:**
- Single deployment unit reduces operational overhead for small team
- Shared database access simplifies ML pipeline (models need historical data)
- No distributed transaction complexity
- Can extract services later if needed (YAGNI principle)

**Consequences:** Easier debugging, faster development velocity, potential scaling limits at very high load.

---

### ADR-002: Flask over Django
**Decision:** Use Flask as the web framework instead of Django.

**Rationale:**
- Lightweight, minimal boilerplate for API-focused application
- Better control over ML pipeline integration
- Celery integrates cleanly without Django-specific patterns
- No need for Django ORM/admin (SQLAlchemy preferred for data science workflows)

**Consequences:** More manual configuration, no built-in admin UI, but greater flexibility for custom ML logic.

---

### ADR-003: PostgreSQL over NoSQL
**Decision:** Use PostgreSQL as the primary database.

**Rationale:**
- Structured F1 data fits relational model naturally (races, drivers, results)
- ACID guarantees for prediction logging and accuracy tracking
- Complex JOINs required for model training queries
- JSON columns available for semi-structured data (track characteristics)

**Consequences:** Vertical scaling limits eventual, but sufficient for projected load (1000+ concurrent users).

---

### ADR-004: Client-Side Rendering with React
**Decision:** Build dashboard as React SPA, not server-side rendered.

**Rationale:**
- Interactive charts require client-side interactivity
- API-driven architecture enables future mobile apps
- Dashboard updates don't require full page reloads
- SEO not critical (no public search traffic expected)

**Consequences:** Initial load time slightly higher, but superior UX for data exploration.

---

### ADR-005: Multiple Models over Single Algorithm
**Decision:** Implement regression, Random Forest, XGBoost, and ELO in parallel.

**Rationale:**
- Ensemble predictions improve accuracy (proven in ML research)
- Different models capture different patterns (linear trends vs. non-linear interactions)
- Enables model comparison for data analysts (user story requirement)
- Modular architecture supports adding new models without refactor

**Consequences:** Increased complexity in model management, longer training times, but better prediction quality.

---

### ADR-006: Celery over Cron
**Decision:** Use Celery Beat + Workers for scheduled tasks instead of system cron.

**Rationale:**
- Python-native, integrates with Flask application code
- Better error handling and retry logic than shell scripts
- Task queue allows throttling (prevent API rate limit breaches)
- Monitoring and observability built-in (Flower UI)

**Consequences:** Requires Redis infrastructure, but provides superior reliability and visibility.

---

### ADR-007: No User Authentication (Phase 1)
**Decision:** Launch MVP without user accounts or authentication.

**Rationale:**
- PRD explicitly lists user accounts as non-goal
- Reduces development timeline by 2-3 weeks
- Public dashboard serves core user stories
- Can add auth later without architectural changes (API already RESTful)

**Consequences:** Cannot personalize predictions or save user preferences, but acceptable for MVP.

---

### ADR-008: Cache Predictions Aggressively
**Decision:** Cache prediction API responses for 1 hour, historical data for 24 hours.

**Rationale:**
- Predictions change infrequently (only after races, max weekly)
- Model inference is CPU-intensive (30 seconds per race)
- Dashboard expects <3 second load times (NFR requirement)
- 1000 concurrent users would overwhelm database without caching

**Consequences:** Users may see stale predictions briefly after model retraining, mitigated by cache invalidation events.

---

### ADR-009: Store Models as Pickle Files
**Decision:** Persist trained scikit-learn/XGBoost models as pickle files on disk/S3.

**Rationale:**
- Standard Python ML serialization format
- Simple to load into memory at startup
- Version control via filenames (e.g., `random_forest_v1.2.pkl`)
- No need for complex model serving infrastructure (TensorFlow Serving, etc.)

**Consequences:** Pickle format is Python-specific, models cannot be shared with non-Python systems, but sufficient for current requirements.

---

### ADR-010: Desktop-First Design
**Decision:** Optimize dashboard for desktop browsers, mobile-responsive not required.

**Rationale:**
- PRD explicitly lists mobile optimization as out-of-scope
- Data-heavy tables and charts are difficult on small screens
- Target audience (F1 analysts, enthusiasts) likely uses desktop
- Mobile web will be functional but not optimized

**Consequences:** Some users may have suboptimal mobile experience, but reduces frontend complexity.

---

## Appendix: PRD Reference

[PRD content omitted for brevity - already included in prompt]