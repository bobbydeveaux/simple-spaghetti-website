# High-Level Design: simple-spaghetti-repo

**Created:** 2026-02-12T15:11:49Z
**Status:** Draft

## 1. Architecture Overview

The system follows a **layered microservices architecture** with three primary tiers:

1. **Data Ingestion Layer**: Orchestrated batch processing pipeline that fetches data from external APIs (Ergast, weather services), transforms it, and loads into the data warehouse
2. **Analytics & Prediction Layer**: ML model training and inference services that process historical data to generate race winner predictions
3. **Presentation Layer**: RESTful API backend and web dashboard frontend for user interaction

The architecture decouples data ingestion from model training and serving, enabling independent scaling and fault isolation. A message queue system coordinates asynchronous workflows between layers. Redis caching sits between the API and database to optimize read-heavy workloads.

This design supports the 99.5% uptime requirement through service redundancy, graceful degradation (cached predictions when live computation fails), and horizontal scaling of stateless components.

---

## 2. System Components

### Data Ingestion Service
Scheduled ETL pipeline (Apache Airflow) that:
- Fetches race results, qualifying data, driver/team standings from Ergast API
- Retrieves weather data (temperature, precipitation, wind) for each circuit
- Validates and transforms raw data into normalized schema
- Loads processed data into PostgreSQL database
- Triggers model retraining workflows after race completion

### ML Model Training Service
Batch processing service that:
- Trains Random Forest and XGBoost classification models on historical race data
- Calculates and updates ELO ratings for drivers and teams
- Performs track-specific performance analysis using circuit-level aggregations
- Generates feature engineering pipelines (weather impact, recent form trends)
- Persists trained models to object storage with versioning
- Runs on-demand or scheduled (post-race) via message queue triggers

### Prediction Service
Real-time inference API that:
- Loads latest trained models from storage
- Generates win probability predictions for upcoming race
- Computes predictions for all active drivers (probabilities sum to 100%)
- Caches results in Redis with TTL until next race or model update
- Exposes predictions via REST API endpoints
- Completes inference in <5 seconds per race prediction

### API Gateway
FastAPI-based REST API that:
- Handles authentication/authorization (JWT tokens)
- Exposes endpoints for predictions, race calendar, historical data, accuracy metrics
- Implements rate limiting (100 req/min per user)
- Validates requests and formats responses (JSON)
- Aggregates data from database and prediction service
- Returns responses in <500ms (95th percentile)

### Web Dashboard
React.js single-page application that:
- Displays next race win probabilities with interactive visualizations (Chart.js)
- Shows race calendar with upcoming events and circuit details
- Renders historical prediction accuracy metrics (Brier score, precision, recall)
- Provides driver/team rankings with sortable tables
- Supports data export (CSV, JSON) for race results
- Authenticates users and manages sessions via JWT

### Database Service
PostgreSQL relational database storing:
- Historical race results (2010-present)
- Driver and team profiles, standings
- Qualifying times and race classifications
- Weather conditions per race
- Prediction history and accuracy metrics
- User accounts and authentication data

### Cache Layer
Redis in-memory store providing:
- Cached prediction results (TTL-based invalidation)
- Session management for authenticated users
- Frequently accessed queries (race calendar, driver standings)
- Rate limiting counters per user

### Message Queue
RabbitMQ or AWS SQS for:
- Decoupling data ingestion from model training
- Triggering model retraining after race completion
- Scheduling background jobs (accuracy calculation, data exports)
- Retry logic with exponential backoff for failed tasks

---

## 3. Data Model

### Core Entities

**Driver**
- driver_id (PK)
- driver_name, driver_code, nationality, date_of_birth
- current_team_id (FK to Team)
- current_elo_rating

**Team (Constructor)**
- team_id (PK)
- team_name, nationality
- current_elo_rating

**Circuit**
- circuit_id (PK)
- circuit_name, location, country
- track_length, track_type (street/permanent)

**Race**
- race_id (PK)
- season_year, round_number
- circuit_id (FK)
- race_date, race_name
- status (scheduled/completed)

**RaceResult**
- result_id (PK)
- race_id (FK)
- driver_id (FK)
- team_id (FK)
- grid_position, final_position, points
- fastest_lap_time, status (finished/retired/DNF)

**QualifyingResult**
- qualifying_id (PK)
- race_id (FK)
- driver_id (FK)
- q1_time, q2_time, q3_time
- final_grid_position

**WeatherData**
- weather_id (PK)
- race_id (FK)
- temperature_celsius, precipitation_mm, wind_speed_kph
- conditions (dry/wet/mixed)

**Prediction**
- prediction_id (PK)
- race_id (FK)
- driver_id (FK)
- predicted_win_probability (0-100%)
- model_version
- prediction_timestamp

**PredictionAccuracy**
- accuracy_id (PK)
- race_id (FK)
- brier_score, log_loss
- correct_winner (boolean)
- top_3_accuracy (boolean)

**User**
- user_id (PK)
- email, password_hash
- created_at, last_login
- role (user/admin)

### Relationships
- Race → Circuit (many-to-one)
- RaceResult → Race, Driver, Team (many-to-one)
- QualifyingResult → Race, Driver (many-to-one)
- WeatherData → Race (one-to-one)
- Prediction → Race, Driver (many-to-one)
- PredictionAccuracy → Race (one-to-one)

---

## 4. API Contracts

### Authentication Endpoints

**POST /api/v1/auth/register**
Request: `{ "email": "user@example.com", "password": "securepass" }`
Response: `{ "user_id": "uuid", "token": "jwt_token" }`

**POST /api/v1/auth/login**
Request: `{ "email": "user@example.com", "password": "securepass" }`
Response: `{ "token": "jwt_token", "expires_at": "2026-02-13T15:11:49Z" }`

### Prediction Endpoints

**GET /api/v1/predictions/next-race**
Headers: `Authorization: Bearer <jwt_token>`
Response:
```json
{
  "race_id": "1234",
  "race_name": "Monaco Grand Prix",
  "race_date": "2026-05-25",
  "circuit": "Circuit de Monaco",
  "predictions": [
    { "driver_id": "1", "driver_name": "Max Verstappen", "win_probability": 35.2 },
    { "driver_id": "2", "driver_name": "Lewis Hamilton", "win_probability": 28.7 }
  ],
  "model_version": "v2.3.1",
  "generated_at": "2026-05-18T10:00:00Z"
}
```

**GET /api/v1/predictions/race/{race_id}**
Response: Same structure as next-race for historical races

### Race Data Endpoints

**GET /api/v1/races/calendar?season=2026**
Response:
```json
{
  "season": 2026,
  "races": [
    { "race_id": "1234", "round": 6, "race_name": "Monaco GP", "date": "2026-05-25", "circuit": "Monaco", "status": "scheduled" }
  ]
}
```

**GET /api/v1/races/{race_id}/results**
Response:
```json
{
  "race_id": "1234",
  "results": [
    { "position": 1, "driver_name": "Max Verstappen", "team": "Red Bull Racing", "points": 25, "grid": 1 }
  ],
  "weather": { "temperature": 22, "conditions": "dry" }
}
```

### Analytics Endpoints

**GET /api/v1/analytics/accuracy?season=2026**
Response:
```json
{
  "season": 2026,
  "races_completed": 8,
  "correct_winner_percentage": 62.5,
  "top_3_accuracy": 87.5,
  "average_brier_score": 0.18,
  "by_race": [
    { "race_name": "Bahrain GP", "correct_winner": true, "brier_score": 0.15 }
  ]
}
```

**GET /api/v1/analytics/driver-rankings?season=2026**
Response:
```json
{
  "rankings": [
    { "driver_name": "Max Verstappen", "elo_rating": 2150, "championship_points": 195, "wins": 6 }
  ]
}
```

### Data Export Endpoints

**GET /api/v1/export/race-results?season=2026&format=csv**
Response: CSV file download with race results

**GET /api/v1/export/predictions?race_id=1234&format=json**
Response: JSON file with prediction data

---

## 5. Technology Stack

### Backend
- **Python 3.11**: Core language for ML, data processing, and API services
- **FastAPI**: High-performance REST API framework with async support, auto-generated OpenAPI docs
- **scikit-learn 1.3+**: Random Forest classification models
- **XGBoost 2.0+**: Gradient boosting models for win prediction
- **pandas/NumPy**: Data manipulation and numerical computations
- **SQLAlchemy**: Database ORM for PostgreSQL interactions
- **Apache Airflow 2.7+**: Workflow orchestration for ETL pipelines
- **Celery**: Distributed task queue for async model training
- **Pydantic**: Data validation and serialization
- **python-jose**: JWT token generation and validation
- **bcrypt**: Password hashing
- **httpx/aiohttp**: Async HTTP clients for external API calls

### Frontend
- **React 18**: Component-based UI framework with hooks
- **TypeScript**: Type-safe JavaScript for maintainability
- **React Router**: Client-side routing for SPA navigation
- **Axios**: HTTP client for API requests
- **Chart.js 4.0**: Interactive charts (bar, line, pie) for predictions and rankings
- **TanStack Query (React Query)**: Data fetching, caching, and state management
- **Tailwind CSS**: Utility-first styling framework
- **Vite**: Fast build tool and dev server
- **React Hook Form**: Form validation and handling

### Infrastructure
- **Docker**: Containerization of all services
- **Kubernetes (K8s)**: Container orchestration, auto-scaling, service discovery
- **Nginx**: Reverse proxy and load balancer
- **Terraform**: Infrastructure as code for cloud provisioning
- **GitHub Actions**: CI/CD pipelines for automated testing and deployment
- **Prometheus**: Metrics collection and monitoring
- **Grafana**: Visualization dashboards for system metrics
- **ELK Stack (Elasticsearch, Logstash, Kibana)**: Centralized logging and analysis
- **Cloudflare CDN**: Static asset distribution and DDoS protection

### Data Storage
- **PostgreSQL 15**: Primary relational database for structured F1 data, ACID compliance
- **Redis 7**: In-memory cache for predictions, session storage, rate limiting
- **AWS S3 / MinIO**: Object storage for trained ML models, data exports
- **RabbitMQ**: Message queue for async task coordination

---

## 6. Integration Points

### Ergast Developer API
- **Endpoint**: http://ergast.com/api/f1
- **Data**: Historical race results, qualifying times, driver/team standings, circuit info (2010-present)
- **Format**: JSON/XML responses
- **Rate Limit**: No official limit but respectful polling (1 request per minute for updates)
- **Integration**: Daily scheduled job fetches latest race results, incremental updates for current season
- **Failure Handling**: Retry with exponential backoff (3 attempts), alert on persistent failure

### OpenWeatherMap API
- **Endpoint**: https://api.openweathermap.org/data/2.5/
- **Data**: Historical weather data for race circuits (temperature, precipitation, wind)
- **Authentication**: API key required
- **Rate Limit**: 1000 calls/day (free tier) or paid tier for higher limits
- **Integration**: Fetch weather data for race date ±1 day, store in WeatherData table
- **Failure Handling**: Use cached/historical average if live data unavailable

### Official Formula 1 API (if accessible)
- **Endpoint**: Proprietary (conditional access)
- **Data**: Real-time race calendar updates, official timing data
- **Authentication**: OAuth or API key
- **Integration**: Supplement Ergast data with official calendar changes
- **Fallback**: Use Ergast as primary source if F1 API unavailable

### Internal Service Communication
- **API Gateway ↔ Prediction Service**: REST over HTTP with JSON
- **Data Ingestion ↔ Message Queue**: AMQP protocol (RabbitMQ)
- **Model Training ↔ Object Storage**: S3-compatible API for model artifacts
- **All Services ↔ PostgreSQL**: Connection pooling via SQLAlchemy (max 20 connections per service)
- **All Services ↔ Redis**: Redis protocol with connection pooling

---

## 7. Security Architecture

### Authentication & Authorization
- **JWT-based authentication**: Tokens issued on login, 24-hour expiry, refresh token support
- **bcrypt password hashing**: Minimum 12 rounds for user passwords
- **Role-based access control (RBAC)**: User roles (user, admin) with granular permissions
- **API key authentication**: Optional for programmatic API access (separate from user accounts)
- **Session management**: Redis-backed sessions with secure, HTTP-only cookies

### Network Security
- **HTTPS/TLS 1.3**: Enforced for all web traffic, certificates via Let's Encrypt
- **API rate limiting**: 100 requests/minute per user, 1000/minute per IP (DDoS mitigation)
- **CORS policies**: Whitelist allowed origins for API access
- **Network segmentation**: Kubernetes network policies isolate services (DB not publicly accessible)

### Data Protection
- **Secrets management**: HashiCorp Vault or AWS Secrets Manager for API keys, DB credentials
- **Database encryption**: PostgreSQL with TLS connections, encrypted backups
- **PII protection**: Email addresses hashed in logs, GDPR compliance for user data
- **Input validation**: Pydantic models validate all API inputs, SQL injection prevention via ORM

### Security Operations
- **Dependency scanning**: Automated vulnerability scanning (Snyk, Dependabot) on every commit
- **Security headers**: HSTS, CSP, X-Frame-Options, X-Content-Type-Options
- **Audit logging**: All authentication events, admin actions logged to immutable store
- **Penetration testing**: Annual third-party security audits
- **Incident response**: Documented runbook for security incidents, on-call rotation

---

## 8. Deployment Architecture

### Kubernetes Cluster Layout
- **Namespaces**: `production`, `staging`, `development` for environment isolation
- **Deployments**:
  - API Gateway: 3 replicas (horizontal pod autoscaler: 3-10 based on CPU/memory)
  - Prediction Service: 2 replicas (scales to 6 during high load)
  - Web Dashboard: Nginx serving static files (3 replicas behind CDN)
  - Data Ingestion Service: 1 scheduled CronJob (daily 2am UTC)
  - ML Training Service: On-demand Jobs triggered by message queue
- **Services**: ClusterIP for internal communication, LoadBalancer for ingress
- **Ingress Controller**: Nginx Ingress with TLS termination
- **Persistent Volumes**: StatefulSets for PostgreSQL (3-node cluster with replication), Redis (single master with replicas)

### Container Strategy
- **Base images**: Python 3.11-slim, Node 20-alpine for minimal attack surface
- **Multi-stage builds**: Separate build and runtime stages to reduce image size
- **Image registry**: Private registry (AWS ECR, Google Artifact Registry)
- **Tagging**: Semantic versioning with Git SHA for traceability
- **Security scanning**: Trivy scans on all images before deployment

### CI/CD Pipeline
- **GitHub Actions workflows**:
  1. On PR: Lint, unit tests, integration tests, security scan
  2. On merge to main: Build Docker images, push to registry, deploy to staging
  3. On tagged release: Deploy to production with manual approval gate
- **Database migrations**: Alembic migrations run automatically before API deployment
- **Blue-green deployments**: Zero-downtime updates, rollback capability within 2 minutes
- **Canary releases**: Route 10% traffic to new version, monitor error rates, full rollout if healthy

### Cloud Provider Strategy
- **Primary**: AWS (EKS for Kubernetes, RDS for PostgreSQL, ElastiCache for Redis, S3 for storage)
- **Alternative**: GCP or Azure for multi-cloud optionality
- **Regions**: Single region (us-east-1 or eu-west-1) with multi-AZ for HA
- **Disaster recovery**: Daily database backups to S3 with 30-day retention, cross-region replication

---

## 9. Scalability Strategy

### Horizontal Scaling
- **Stateless services**: API Gateway, Prediction Service, Web Dashboard scale horizontally via K8s HPA
- **Auto-scaling triggers**: CPU >70% or memory >80% triggers scale-up, <30% for 10 minutes triggers scale-down
- **Database read replicas**: PostgreSQL read replicas (2-3 nodes) for query distribution
- **Redis clustering**: Redis Cluster mode for cache distribution across 3+ nodes

### Vertical Scaling
- **Database**: PostgreSQL primary with 16-32 CPU cores, 64-128GB RAM for 10M+ records
- **ML Training Service**: GPU-enabled nodes (NVIDIA T4/A10G) for XGBoost training acceleration
- **Message Queue**: RabbitMQ with 8-16GB RAM for high-throughput message buffering

### Data Partitioning
- **Time-based partitioning**: PostgreSQL table partitioning by season_year for RaceResult, Prediction tables
- **Archival strategy**: Move pre-2018 data to cold storage (S3 Glacier) with on-demand retrieval
- **Caching layers**:
  - Redis L1 cache: Prediction results (TTL 7 days), frequently accessed queries (driver standings)
  - CDN L2 cache: Static assets, API responses for public endpoints (race calendar)

### Load Balancing
- **Nginx Ingress**: Round-robin distribution to API Gateway pods
- **Database connection pooling**: PgBouncer with 100 max connections per service
- **Rate limiting per user**: Distributed rate limiting via Redis to prevent single-user overload

### Performance Optimization
- **Database indexing**: Indexes on race_date, driver_id, season_year for fast lookups
- **Query optimization**: Materialized views for complex aggregations (driver rankings, accuracy metrics)
- **Async processing**: Non-blocking I/O in FastAPI, background tasks for expensive computations
- **Lazy loading**: Paginated API responses (max 100 records per page)

---

## 10. Monitoring & Observability

### Metrics Collection
- **Prometheus**: Scrapes metrics from all services every 15 seconds
  - System metrics: CPU, memory, disk I/O, network traffic
  - Application metrics: API request rates, latency percentiles (p50, p95, p99), error rates
  - Business metrics: Predictions generated, model inference time, prediction accuracy
  - Database metrics: Query execution time, connection pool usage, slow query log
- **Custom metrics**: Model training duration, data ingestion success rate, cache hit ratio

### Logging Strategy
- **Structured logging**: JSON-formatted logs with correlation IDs for request tracing
- **Log aggregation**: Fluentd collects logs from all pods, ships to Elasticsearch
- **Log levels**: DEBUG (dev), INFO (staging), WARN/ERROR (production)
- **Retention**: 30 days in Elasticsearch, archived to S3 for compliance (1 year)
- **Searchable fields**: timestamp, service, log_level, user_id, request_id, error_type

### Distributed Tracing
- **OpenTelemetry**: Instrument all services for end-to-end request tracing
- **Jaeger**: Trace visualization for debugging latency issues
- **Trace sampling**: 100% in staging, 10% in production (high-traffic scenarios)
- **Key spans**: External API calls (Ergast, weather), database queries, ML inference

### Alerting
- **Alertmanager**: Routes Prometheus alerts to PagerDuty, Slack
- **Critical alerts** (page on-call):
  - Service downtime (>5xx errors for 2 minutes)
  - API latency >2s for p95 (sustained 5 minutes)
  - Database connection exhaustion
  - Data ingestion failure (3 consecutive retries failed)
- **Warning alerts** (Slack notification):
  - Cache miss rate >50%
  - Disk usage >80%
  - Prediction staleness (no update in 8 hours before race)

### Dashboards
- **Grafana dashboards**:
  - System health: CPU, memory, network per service
  - API performance: Request rate, latency heatmap, error rate by endpoint
  - ML pipeline: Model training success rate, inference latency, prediction drift
  - Business KPIs: Daily active users, predictions served, accuracy trends
- **Real-time monitoring**: 30-second refresh for production dashboard, 5-minute for historical views

### Health Checks
- **Kubernetes liveness probes**: HTTP GET /health/live every 10s, restart pod on 3 failures
- **Readiness probes**: HTTP GET /health/ready checks DB connectivity, cache availability
- **Startup probes**: Allow 60s for ML service to load models before marking ready

---

## 11. Architectural Decisions (ADRs)

### ADR-001: Microservices over Monolith
**Decision**: Adopt microservices architecture with separate services for ingestion, training, prediction, API.
**Rationale**: Enables independent scaling (ML training is compute-intensive, API is I/O-bound), fault isolation (ingestion failure doesn't break predictions), and technology flexibility (Python for ML, Node.js option for frontend tooling).
**Tradeoffs**: Increased operational complexity, network latency between services. Mitigated by Kubernetes orchestration and Redis caching.

### ADR-002: PostgreSQL for Primary Database
**Decision**: Use PostgreSQL over NoSQL (MongoDB, DynamoDB).
**Rationale**: F1 data has strong relational structure (drivers, teams, races, results), benefits from ACID guarantees for prediction history, supports complex joins for analytics queries. PostgreSQL's partitioning and indexing handle 10M+ records efficiently.
**Tradeoffs**: Harder to horizontally scale writes compared to NoSQL. Mitigated by read replicas and partitioning by season.

### ADR-003: Batch Predictions over Real-Time
**Decision**: Generate predictions asynchronously (post-race or daily), cache in Redis, serve from cache.
**Rationale**: Race predictions don't require sub-second updates. Batch approach allows complex ML inference (5+ seconds) without blocking API requests. Meets <500ms API latency requirement via caching.
**Tradeoffs**: Predictions may be slightly stale (up to 24 hours). Acceptable given race schedule is weekly.

### ADR-004: Apache Airflow for Orchestration
**Decision**: Use Airflow over custom cron jobs or AWS Step Functions.
**Rationale**: Airflow provides DAG-based workflow visualization, retry logic, dependency management (e.g., "train model after ingestion completes"), and extensive operator library. Open-source avoids vendor lock-in.
**Tradeoffs**: Additional service to manage. Mitigated by managed Airflow (AWS MWAA, Google Cloud Composer) option.

### ADR-005: XGBoost + Random Forest Ensemble
**Decision**: Use ensemble of XGBoost and Random Forest, average probabilities for final prediction.
**Rationale**: Ensemble reduces overfitting and improves generalization. XGBoost excels at gradient boosting with sparse features, Random Forest handles non-linear interactions. Averaging provides robust predictions.
**Tradeoffs**: Doubled inference time and model storage. Acceptable given batch prediction approach (not latency-critical).

### ADR-006: JWT for Authentication
**Decision**: Stateless JWT tokens over session cookies.
**Rationale**: JWTs enable horizontal scaling of API Gateway (no session store lookups), support mobile/SPA clients, and allow API key-based programmatic access. Refresh tokens handle expiry.
**Tradeoffs**: Token revocation requires blacklist (Redis). Mitigated by short TTL (24 hours) and refresh flow.

### ADR-007: Redis for Caching over In-Memory
**Decision**: Use Redis Cluster over application-level in-memory caches.
**Rationale**: Shared cache across all API Gateway replicas avoids duplicate predictions in memory. Redis persistence survives pod restarts. Pub/sub for cache invalidation when new predictions generated.
**Tradeoffs**: Network hop adds ~1ms latency. Acceptable given overall <500ms budget.

### ADR-008: React over Vue.js
**Decision**: Choose React for frontend dashboard.
**Rationale**: Larger ecosystem (Chart.js integrations, UI libraries), stronger TypeScript support, broader developer hiring pool. React Query simplifies data fetching and caching.
**Tradeoffs**: Steeper learning curve than Vue. Mitigated by team familiarity and extensive documentation.

### ADR-009: Kubernetes over Serverless
**Decision**: Deploy on Kubernetes (EKS/GKE) over AWS Lambda/Cloud Run.
**Rationale**: ML model training requires long-running jobs (>15 minutes), GPU support for XGBoost. Kubernetes provides fine-grained control over resource allocation and cost optimization. Airflow integration is native.
**Tradeoffs**: Higher operational overhead than serverless. Mitigated by managed K8s services and infrastructure-as-code (Terraform).

### ADR-010: Daily Data Ingestion over Real-Time
**Decision**: Scheduled daily ingestion (2am UTC) over event-driven real-time streaming.
**Rationale**: F1 races occur weekly on weekends. Ergast API updates within 2-4 hours post-race. Daily batch is sufficient for "next race" predictions (7+ days in advance). Simplifies architecture and reduces API costs.
**Tradeoffs**: Predictions lag by up to 24 hours post-race. Acceptable given race schedule and user expectations.

---

## Appendix: PRD Reference

# Product Requirements Document: A Formula One driver database with complicated analytical modeling to help predict the winner of the next race. The system should include:

1. **Data Import**: Ability to import data from online data sources (e.g., Ergast API, official F1 data feeds) including historical race results, driver statistics, qualifying times, weather conditions, and track characteristics.

2. **Statistical Modeling**: Process data using statistical modeling techniques such as:
   - Regression analysis for performance trends
   - Machine learning models for prediction (e.g., Random Forest, XGBoost)
   - ELO-style rating systems for drivers and teams
   - Track-specific performance analysis
   - Weather impact modeling

3. **Website Dashboard**: A web interface that displays:
   - Percentage chance of each driver winning the next Grand Prix
   - Race calendar with upcoming events
   - Historical prediction accuracy
   - Driver and team rankings
   - Interactive charts and visualizations

The predictions should update based on the F1 calendar and incorporate recent race results to improve model accuracy over time.

**Created:** 2026-02-12T15:10:49Z
**Status:** Draft

## 1. Overview

**Concept:** A Formula One driver database with complicated analytical modeling to help predict the winner of the next race. The system should include data import, statistical modeling, and a website dashboard.

**Description:** An enterprise-grade Formula One prediction analytics platform that aggregates historical and real-time F1 data, applies machine learning models to predict race outcomes, and presents actionable insights through an interactive web dashboard. The system will continuously improve predictions by incorporating recent race results and track-specific performance data.

---

## 2. Goals

- Achieve 70%+ prediction accuracy for race winner predictions within the first season of operation
- Ingest and process data from multiple F1 data sources (Ergast API, official feeds) with automated daily updates
- Deliver a production-ready web dashboard with real-time prediction updates and interactive visualizations
- Implement multiple statistical models (regression, ML ensembles, ELO ratings) to provide robust predictions
- Track and display historical prediction accuracy to validate model performance over time

---

## 3. Non-Goals

- Live race telemetry streaming or lap-by-lap updates during active races
- Fantasy F1 league management or betting integration
- Mobile native applications (iOS/Android) in initial release
- Social features such as user comments, forums, or prediction competitions
- Direct integration with F1 TV or video streaming services

---

## 4. User Stories

- As an F1 enthusiast, I want to view the predicted win probability for each driver before the next race so that I can make informed predictions
- As a data analyst, I want to access historical race data and driver statistics so that I can understand performance trends
- As a casual fan, I want to see the upcoming race calendar with predictions so that I know which races to watch
- As a user, I want to view interactive charts showing driver and team rankings so that I can compare performance visually
- As a returning user, I want to see how accurate past predictions were so that I can trust the system's forecasts
- As an API consumer, I want to query prediction data programmatically so that I can integrate it into my own applications
- As a system administrator, I want automated data ingestion pipelines so that predictions stay current without manual intervention
- As a power user, I want to filter predictions by track type or weather conditions so that I can analyze context-specific performance

---

## 5. Acceptance Criteria

**User Story: View predicted win probability**
- Given the user navigates to the dashboard homepage
- When the next scheduled race is within 14 days
- Then the system displays win probabilities for all drivers summing to 100%

**User Story: Access historical race data**
- Given the user selects a specific season and race
- When the race has been completed
- Then the system displays race results, qualifying times, and weather conditions

**User Story: View upcoming race calendar**
- Given the current date is during the F1 season
- When the user accesses the calendar view
- Then all upcoming races are listed with dates, circuits, and prediction summaries

**User Story: View prediction accuracy**
- Given at least 5 races have been completed in the current season
- When the user navigates to the accuracy dashboard
- Then historical prediction accuracy metrics are displayed with confidence intervals

**User Story: Automated data ingestion**
- Given a scheduled data ingestion job runs daily
- When new race results are available from source APIs
- Then the system updates the database and retrains prediction models automatically

---

## 6. Functional Requirements

**FR-001**: System shall ingest data from Ergast API including race results, qualifying times, driver standings, and constructor standings
**FR-002**: System shall store historical F1 data dating back to at least 2010 in a relational database
**FR-003**: System shall integrate weather data (temperature, precipitation, wind) for each race circuit
**FR-004**: System shall implement Random Forest and XGBoost classification models for win prediction
**FR-005**: System shall calculate and maintain ELO ratings for all active drivers and teams
**FR-006**: System shall perform track-specific performance analysis using historical results at each circuit
**FR-007**: System shall generate win probability percentages for all drivers in the next scheduled race
**FR-008**: System shall display race calendar with circuit details and scheduling information
**FR-009**: System shall provide interactive data visualizations (bar charts, line graphs, heatmaps) for driver/team performance
**FR-010**: System shall track and display prediction accuracy metrics (precision, recall, Brier score)
**FR-011**: System shall retrain ML models after each completed race using updated data
**FR-012**: System shall expose RESTful API endpoints for programmatic access to predictions and data
**FR-013**: System shall implement user authentication and authorization for dashboard access
**FR-014**: System shall provide data export functionality (CSV, JSON) for race results and predictions
**FR-015**: System shall display driver and constructor championship standings

---

## 7. Non-Functional Requirements

### Performance
- Dashboard page load time shall not exceed 2 seconds for 95th percentile users
- API response time for prediction queries shall be under 500ms
- Data ingestion pipeline shall process a full race weekend dataset within 30 minutes
- ML model inference shall generate predictions for all drivers in under 5 seconds
- System shall support concurrent access by 1,000+ users without degradation

### Security
- All API endpoints shall require authentication via JWT tokens
- User passwords shall be hashed using bcrypt with minimum 12 rounds
- HTTPS/TLS 1.3 shall be enforced for all web traffic
- API rate limiting shall prevent abuse (100 requests per minute per user)
- Sensitive configuration and API keys shall be stored in encrypted vaults
- Regular security audits and dependency vulnerability scanning shall be performed

### Scalability
- Database architecture shall support horizontal scaling to handle 10M+ historical records
- Prediction service shall scale horizontally to handle increased computational load
- CDN integration shall distribute static assets globally for low-latency access
- Caching layer shall reduce database queries for frequently accessed data
- Message queue system shall decouple data ingestion from model training workflows

### Reliability
- System uptime shall be 99.5% excluding planned maintenance windows
- Automated backup of database shall occur daily with 30-day retention
- Health monitoring and alerting shall detect service degradation within 2 minutes
- Data ingestion failures shall trigger automatic retries with exponential backoff
- Graceful degradation shall display cached predictions if live computation fails

---

## 8. Dependencies

**External APIs:**
- Ergast Developer API (http://ergast.com/mrd/) for historical F1 race data
- OpenWeatherMap API or Weather.com API for historical and forecast weather data
- Official Formula 1 API (if accessible) for real-time race calendar updates

**Technology Stack:**
- Python 3.10+ with scikit-learn, XGBoost, pandas, NumPy for ML modeling
- PostgreSQL or MySQL for relational data storage
- Redis for caching and session management
- React.js or Vue.js for frontend dashboard development
- FastAPI or Flask for backend API services
- Docker and Kubernetes for containerization and orchestration
- Apache Airflow or Celery for scheduled data pipeline orchestration

**Third-Party Libraries:**
- Chart.js or D3.js for data visualizations
- JWT libraries for authentication
- SQLAlchemy or Django ORM for database abstraction

---

## 9. Out of Scope

- Real-time lap timing and telemetry data during live races
- Predictive modeling for qualifying session outcomes (focus is on race winner only)
- Integration with sports betting platforms or odds providers
- Multi-language localization and internationalization
- Native mobile applications for iOS and Android
- User-generated content such as comments, forums, or social feeds
- Fantasy league scoring or team management features
- Historical data prior to 2010 season
- Predictions for sprint races or non-championship events
- Video content hosting or streaming integration
- Merchandise store or e-commerce functionality

---

## 10. Success Metrics

**Prediction Accuracy:**
- Achieve 70% correct winner predictions by end of first season
- Maintain top-3 prediction accuracy of 85% or higher
- Reduce Brier score below 0.15 for probabilistic predictions

**User Engagement:**
- Achieve 5,000 monthly active users within 6 months of launch
- Average session duration of 5+ minutes per user visit
- 40% user retention rate month-over-month

**System Performance:**
- 99.5% system uptime measured monthly
- API response times under 500ms for 95th percentile
- Zero data loss incidents during ingestion pipeline operations

**Business Metrics:**
- Complete data ingestion for 100% of scheduled races within 24 hours
- Deploy ML model updates within 48 hours of race completion
- Process and display predictions for upcoming race at least 7 days in advance

---

## Appendix: Clarification Q&A

### Clarification Questions & Answers
