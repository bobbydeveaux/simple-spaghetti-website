# Simple Spaghetti Website

A multi-service web platform combining pasta recipe management, PTA voting systems, and F1 prediction analytics with comprehensive CI/CD automation.

## 🏗️ Architecture

This repository contains multiple integrated services:

### Core Services
- **Pasta Recipe App**: React-based recipe management system
- **PTA Voting System**: Democratic voting platform for Parent-Teacher Association
- **F1 Prediction Analytics**: Machine learning platform for Formula 1 race predictions
- **Polymarket Bot**: Automated trading bot for Polymarket prediction markets with validated data models

### Infrastructure
- **CI/CD Pipelines**: Automated testing, deployment, and monitoring with GitHub Actions
- **Containerization**: Docker multi-service support with development and production configurations
- **Database Management**: PostgreSQL with automated migrations and backups
- **ML Operations**: Automated model training, validation, and deployment

## 🚀 CI/CD Pipeline

### Automated Workflows

| Workflow | Trigger | Purpose |
|----------|---------|---------|
| **CI Pipeline** | PR to main/develop | Testing, security scanning, quality gates |
| **Backend Deployment** | Push to main | Blue-green deployment with rollback |
| **Frontend Deployment** | Frontend changes | S3/CloudFront deployment with CDN |
| **Database Migration** | Schema changes | Safe migrations with automated backups |
| **ML Model Training** | Weekly/new data | F1 prediction model training and deployment |
| **Docker Build** | Code changes | Multi-service containerization |

### Key Features
- ✅ **Zero-downtime deployments** with blue-green strategy
- ✅ **Automated rollback** on failure detection
- ✅ **Security scanning** with Trivy and Snyk
- ✅ **Performance monitoring** with Lighthouse CI
- ✅ **ML pipeline automation** for F1 predictions
- ✅ **Multi-environment support** (staging/production)

## 🔧 Development Setup

### Quick Start with Docker
```bash
# Clone the repository
git clone https://github.com/bobbydeveaux/simple-spaghetti-website.git
cd simple-spaghetti-website

# Start all services
docker-compose up -d

# Check service status
docker-compose ps
```

### Manual Setup
```bash
# Backend setup
cd api
pip install -r requirements.txt
python app.py

# Frontend setup
npm install
npm run dev

# F1 Analytics setup
cd f1-analytics/backend
pip install -r requirements.txt
uvicorn app.main:app --host 0.0.0.0 --port 8001
```

## 🌐 Service Endpoints

| Service | Local URL | Production URL | Purpose |
|---------|-----------|---------------|---------|
| **Main App** | http://localhost:3000 | https://f1-analytics.example.com | Recipe management UI |
| **API Service** | http://localhost:5000 | https://api.f1-analytics.example.com | Backend API |
| **F1 Analytics** | http://localhost:8001 | https://api.f1-analytics.example.com/api/v1 | ML prediction API |
| **F1 Dashboard** | http://localhost:3001 | https://f1-analytics.example.com/f1-analytics | Prediction dashboard |

## 🧪 Testing

### Automated Testing
```bash
# Run all tests
npm test
python -m pytest

# Integration tests
python test_voting_implementation.py

# F1 Analytics tests
python test_f1_models.py
python -m pytest f1-analytics/backend/tests/test_ingestion.py

# Performance tests
locust -f tests/performance/test_load.py
```

### CI/CD Testing
- **Unit Tests**: Component and service level validation
- **Integration Tests**: API and database interaction testing
- **E2E Tests**: Full user workflow validation
- **Security Tests**: Vulnerability and dependency scanning
- **Performance Tests**: Load testing and metrics validation

## 📊 F1 Prediction Analytics

A comprehensive Formula One race prediction system built with modern microservices architecture and machine learning. This platform aggregates F1 data from multiple sources, applies statistical models, and provides real-time race winner predictions through an interactive web dashboard.

### 🏎️ Features

#### Core Functionality
- **Real-time Predictions**: ML-powered race winner probability calculations
- **Interactive Dashboard**: React-based web interface with live data visualizations
- **Historical Analysis**: Track prediction accuracy and model performance over time
- **Data Export**: CSV/JSON export functionality for analysis
- **Multi-Model Ensemble**: Random Forest, XGBoost, and ELO rating systems

#### Technical Capabilities
- **Cloud-Native Architecture**: Kubernetes-ready microservices deployment
- **High Availability**: Redis clustering, PostgreSQL replication, auto-scaling
- **Real-time Analytics**: Live prediction updates and performance monitoring
- **ML Pipeline**: Apache Airflow orchestration for automated model training
- **Comprehensive Monitoring**: Prometheus, Grafana, and custom metrics

### Database Models

#### Core F1 Models
- `Driver`: F1 drivers with ELO ratings and team associations
- `Team`: Constructor teams with performance metrics
- `Circuit`: Race circuits with technical specifications
- `Race`: Individual races with scheduling and status
- `RaceResult`: Race finish positions and points
- `QualifyingResult`: Qualifying session results
- `WeatherData`: Weather conditions for each race

#### Prediction Models
- `Prediction`: ML-generated win probability predictions
- `PredictionAccuracy`: Model performance tracking and metrics

#### Authentication
- `User`: User accounts with role-based permissions

### ML Pipeline
1. **Data Ingestion**: Automated collection from Ergast API and weather services
2. **Feature Engineering**: ELO ratings, recent form, track performance
3. **Model Training**: Random Forest + XGBoost ensemble
4. **Validation**: Staging environment testing
5. **Deployment**: Production model updates with A/B testing

### 📥 Data Ingestion System

The F1 analytics platform includes a comprehensive data ingestion system that automatically imports race and qualifying data from external sources.

#### Features
- **Automated Data Collection**: Scheduled imports from Ergast Motor Racing API
- **Race Data Import**: Complete race schedules, results, and metadata
- **Qualifying Data Import**: Q1, Q2, Q3 session times and grid positions
- **Data Validation**: Integrity checks and consistency validation
- **Error Handling**: Robust retry mechanisms and comprehensive error reporting
- **CLI Interface**: Command-line tools for manual data management operations

#### Usage Examples

```bash
# Import complete 2024 season data
python scripts/ingest_f1_data.py season 2024

# Import specific race data
python scripts/ingest_f1_data.py race 2024 --round 5

# Import qualifying data
python scripts/ingest_f1_data.py qualifying 2024

# Validate data integrity
python scripts/ingest_f1_data.py validate 2024
```

#### Data Sources
- **Ergast Motor Racing API**: Historical F1 data from 1950 onwards
- **Race schedules and results**: Complete championship data
- **Driver and team information**: Current and historical records
- **Circuit details**: Track characteristics and specifications

See [F1 Data Ingestion Documentation](docs/F1_DATA_INGESTION.md) for detailed usage and configuration information.

### Technical Architecture
The F1 analytics system follows a layered architecture:
- **Models Layer**: SQLAlchemy ORM models with relationships
- **Database Layer**: PostgreSQL with connection pooling
- **API Layer**: FastAPI REST endpoints
- **ML Layer**: Scikit-learn and XGBoost models
- **Cache Layer**: Redis for performance optimization

### 🔒 Enterprise Security Standards
- **🔐 External Secret Management**: AWS Secrets Manager integration with External Secrets Operator
- **🛡️ Zero Hardcoded Secrets**: No credentials stored in version control
- **🔑 Modern Authentication**: SCRAM-SHA-256 PostgreSQL authentication
- **🌐 Environment-Specific Configuration**: Separate configs for production/staging/development
- **🚫 Non-Root Containers**: All services run with minimal privileges
- **🛂 Network Security**: Comprehensive network policies with micro-segmentation and default-deny-all
- **📜 SSL/TLS**: Encrypted connections for all database and Redis communications
- **🔄 Secret Rotation**: Automated secret rotation support via AWS

### Production Deployment

**⚠️ Important:** For F1 Analytics production deployment with secure external secret management:

1. **Configure AWS Secrets Manager** (see [External Secrets Setup](infrastructure/kubernetes/external-secrets/README.md))
2. **Set up environment-specific domains** (see [Environment Configuration](infrastructure/kubernetes/environments/))
3. **Deploy with proper security configurations**

```bash
# F1 Analytics Kubernetes deployment
# 1. Configure secrets in AWS Secrets Manager
# See infrastructure/kubernetes/external-secrets/README.md

# 2. Update domain configuration
# Edit infrastructure/kubernetes/environments/production/domains.yaml

# 3. Deploy External Secrets Operator first
kubectl apply -f infrastructure/kubernetes/external-secrets/

# 4. Deploy F1 Analytics with environment-specific config
kubectl apply -f infrastructure/kubernetes/environments/production/
kubectl apply -f infrastructure/kubernetes/
```

### F1 Analytics Setup
```bash
# Set Environment Variables
export DATABASE_URL="postgresql://user:pass@localhost:5432/f1_analytics"
export JWT_SECRET_KEY="your-secret-key"

# Initialize Database
python -c "from api.migrations.001_initial_schema import create_initial_schema; create_initial_schema()"

# Configuration
# Key settings in api/config.py:
# - Database connection settings
# - JWT authentication parameters
# - External API endpoints (Ergast, Weather)
# - ML model configuration
# - Rate limiting settings
```

## 🛠️ Operations

### Deployment
```bash
# Deploy to staging
git push origin develop

# Deploy to production (requires approval)
git push origin main

# Manual deployment
gh workflow run deploy-backend.yml -f environment=production
```

### Database Management
```bash
# Run migrations
alembic upgrade head

# Create migration
alembic revision -m "description"

# Rollback
alembic downgrade -1
```

### Monitoring
- **Health Checks**: Automated service monitoring with custom probes
- **Metrics Collection**: Prometheus with PostgreSQL, Redis, and Node exporters
- **Alerting**: Comprehensive Alertmanager rules for F1 prediction analytics
  - 25+ alert rules covering system health, ML performance, data pipeline
  - Multi-channel notifications (Slack, Email, PagerDuty)
  - Service-specific routing and escalation policies
- **Visualization**: Grafana dashboards for system and ML performance metrics
- **Security Monitoring**: Anomaly detection and authentication failure alerts
- **Logs**: Centralized logging with search capabilities

## 📁 Project Structure

```
├── api/                        # Backend API services
│   ├── app.py                  # Flask application
│   ├── main.py                 # FastAPI service
│   ├── models/                 # SQLAlchemy ORM models
│   ├── migrations/             # Database migration scripts
│   └── voting/                 # PTA voting system
├── src/                        # Frontend React application
│   ├── components/             # Reusable UI components
│   ├── voting/                 # Voting system UI
│   └── utils/                  # Helper functions
├── f1-analytics/               # F1 prediction platform
│   ├── backend/                # Python ML services
│   │   ├── app/                # FastAPI application
│   │   │   ├── models/         # F1 data models
│   │   │   ├── repositories/   # Data access layer
│   │   │   ├── routes/         # API endpoints
│   │   │   └── utils/          # Authentication and utilities
│   │   ├── alembic/            # Database migrations
│   │   └── tests/              # Test suites
│   └── frontend/               # React dashboard
├── polymarket-bot/             # Polymarket trading bot
│   ├── models.py               # Core data models (BotState, Trade, Position, MarketData)
│   ├── tests/                  # Comprehensive test suite
│   └── README.md               # Module documentation
├── .github/workflows/          # CI/CD pipeline definitions
├── docs/                       # Documentation
└── docker-compose.yml         # Multi-service container setup
```

## 🔐 Security

### Implemented Measures
- **Authentication**: JWT-based with secure session management
- **Input Validation**: Comprehensive sanitization and validation
- **Database Security**: Parameterized queries, connection encryption
- **Container Security**: Minimal base images, vulnerability scanning
- **Network Security**: VPC isolation, security groups
- **Secrets Management**: GitHub Secrets, environment-based configuration

### Compliance
- **Vulnerability Scanning**: Automated with Trivy and Snyk
- **SBOM Generation**: Software Bill of Materials for compliance
- **Audit Logging**: All authentication and admin actions logged
- **Access Controls**: Role-based permissions and approval workflows

## 📈 Metrics and Performance

### Key Performance Indicators
- **Deployment Frequency**: Multiple deployments per day
- **Lead Time**: <30 minutes from commit to production
- **Mean Time to Recovery**: <5 minutes
- **Change Failure Rate**: <5%
- **Test Coverage**: >80%
- **Prediction Accuracy**: >70% (F1 race winners)

### Performance Targets
- **API Response Time**: <500ms (95th percentile)
- **Frontend Load Time**: <2 seconds
- **Database Query Time**: <100ms average
- **Model Inference**: <5 seconds
- **System Uptime**: 99.5%

## 🤝 Contributing

### Development Workflow
1. Fork the repository
2. Create feature branch: `git checkout -b feature/amazing-feature`
3. Commit changes: `git commit -m 'Add amazing feature'`
4. Push to branch: `git push origin feature/amazing-feature`
5. Open Pull Request

### Pull Request Process
- All PRs require passing CI checks
- Code review required for production deployments
- Automated security and quality scanning
- Integration tests must pass
- Documentation updates required for new features

### Code Standards
- Python: Black formatting, flake8 linting, type hints
- JavaScript: ESLint, Prettier, TypeScript
- Documentation: Comprehensive README and inline comments
- Testing: Minimum 90% test coverage required

## 📚 Documentation

- [CI/CD Implementation Guide](docs/CI-CD-IMPLEMENTATION.md)
- [Docker Deployment Guide](DOCKER_DEPLOYMENT.md) (auto-generated)
- [F1 Analytics Architecture](docs/concepts/f1-prediction-analytics/)
- [F1 Database Models](docs/F1_DATABASE_MODELS.md)
- [PTA Voting System](docs/concepts/pta-voting-system/)

### F1 Analytics Documentation
- [**🔒 Secure Kubernetes Deployment**](docs/SECURE_DEPLOYMENT.md) - Complete production deployment with enterprise security
- [**📋 Security Implementation Checklist**](docs/SECURITY_CHECKLIST.md) - Verification and compliance guide
- [**🔐 External Secrets Setup**](infrastructure/kubernetes/external-secrets/README.md) - AWS Secrets Manager integration
- [**🛡️ Security Validation**](scripts/validate-security.sh) - Automated security compliance checking
- [**📊 Alertmanager Configuration**](docs/monitoring/alertmanager-configuration.md) - Comprehensive monitoring and alerting setup
- [**💻 Local Development Setup**](docs/concepts/f1-prediction-analytics/LLD.md) - Development environment configuration
- [**🔧 Data Transformation & Validation Layer**](docs/data-transformation-validation.md) - Comprehensive validation and transformation system

## 📧 Support

For questions, issues, or contributions:
- **Issues**: GitHub Issues for bug reports and feature requests
- **Discussions**: GitHub Discussions for general questions
- **Security**: Email security@example.com for security-related issues

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 🙏 Acknowledgments

- **Ergast API**: Historical F1 data source
- **OpenWeatherMap**: Weather data for race predictions
- **Formula 1**: Inspiration and data standards
- **Open Source Community**: Libraries and frameworks used

---

**Built with ❤️ for Formula 1 fans and data enthusiasts**
