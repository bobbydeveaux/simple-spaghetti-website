# 🏎️ F1 Analytics - Docker Development Environment

A comprehensive Formula One prediction analytics platform with Docker containerization for seamless development and deployment.

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

## 🐳 Container Services

| Service | Description | Port | Health Check |
|---------|-------------|------|--------------|
| **frontend** | React TypeScript dashboard | 3000 | `/health` |
| **backend** | FastAPI Python application | 8000 | `/health` |
| **postgres** | PostgreSQL database | 5432 | `pg_isready` |
| **redis** | Redis cache & message broker | 6379 | `ping` |
| **celery-worker** | Background task processor | - | Internal |
| **celery-beat** | Task scheduler | - | Internal |
| **flower** | Celery monitoring | 5555 | Web interface |

## 🛠️ Development Commands

### Using the Helper Script

```bash
# Start services
./scripts/dev_commands.sh start

# View logs
./scripts/dev_commands.sh logs [service-name]

# Stop services
./scripts/dev_commands.sh stop

# Open database shell
./scripts/dev_commands.sh db-shell

# Run tests
./scripts/dev_commands.sh test-backend

# Clean everything
./scripts/dev_commands.sh clean
```

### Manual Docker Compose Commands

```bash
cd f1-analytics/infrastructure

# Start development environment
docker-compose up -d

# View logs
docker-compose logs -f [service]

# Rebuild containers
docker-compose build --no-cache

# Scale services
docker-compose up -d --scale backend=3

# Stop everything
docker-compose down --volumes
```

## 🗄️ Database Management

### Accessing the Database

```bash
# Using helper script
./scripts/dev_commands.sh db-shell

# Or directly
docker-compose exec postgres psql -U f1user -d f1_analytics
```

### Running Migrations

```bash
# Apply migrations
docker-compose exec backend alembic upgrade head

# Create new migration
docker-compose exec backend alembic revision --autogenerate -m "migration_name"

# Check migration status
docker-compose exec backend alembic current
```

### Sample Data

The database is automatically initialized with:
- 10 F1 teams with official colors
- Sample drivers (Verstappen, Hamilton, Leclerc, etc.)
- Famous circuits (Monaco, Silverstone, Spa, etc.)
- Admin user: `admin@f1analytics.com` / `admin123`

## 🧪 Testing

### Comprehensive Test Coverage

The application includes extensive test suites for security and functionality:

**Backend Test Coverage (80%+ required):**
- API endpoint testing with security validation
- JWT token security and validation testing
- Database and Redis connectivity testing
- Health check functionality with failure scenarios
- Error handling and exception management
- Security configuration validation

**Frontend Test Coverage (80%+ required):**
- React component testing with API integration
- Error boundary and fallback testing
- Loading states and user interaction testing
- API failure handling and retry logic

### Running Tests

**Backend Tests:**
```bash
# Run all backend tests with coverage
docker-compose exec backend pytest --cov=app --cov-report=html

# Run security-specific tests
docker-compose exec backend pytest -m security -v

# Run health check tests
docker-compose exec backend pytest tests/test_health_checks.py -v

# Run with strict coverage requirements (80% minimum)
docker-compose exec backend pytest --cov=app --cov-fail-under=80
```

**Frontend Tests:**
```bash
# Run frontend tests with coverage
docker-compose exec frontend npm run test:coverage

# Run specific component tests
docker-compose exec frontend npm test -- App.test.tsx

# Watch mode for development
docker-compose exec frontend npm test -- --watch
```

**Security Validation Tests:**
```bash
# Test environment security
docker-compose exec backend python -c "
from app.core.security import validate_environment_security
result = validate_environment_security()
print('Security Issues:', result['issues'])
"

# Validate JWT secret strength
docker-compose exec backend python -c "
from app.core.security import validate_jwt_secret
try: validate_jwt_secret(); print('JWT Secret: SECURE')
except: print('JWT Secret: WEAK - Fix required')
"
```

## 📝 Environment Configuration

### 🔐 Security First Approach

This application implements enterprise-grade security practices:

- **Secure credential management** with environment variables
- **JWT token validation** with strong secret requirements
- **Real health checks** that verify actual service connectivity
- **Comprehensive test coverage** (>80% backend, >80% frontend)
- **Production security hardening** with rate limiting and security headers

### Environment Files

Environment configuration uses secure templates:

- `.env.template` - Development template with placeholders
- `.env.example` - Example with secure defaults
- `.env.production.template` - Production security template

**⚠️ Important**: Never commit `.env` files to version control!

### Generating Secure Secrets

```bash
# Generate secure secrets for production
./scripts/generate_secrets.sh

# Creates .env.secure.generated with cryptographically secure values
cp .env.secure.generated .env
rm .env.secure.generated  # Remove after copying
```

### Key Environment Variables

**Backend (Secure Configuration):**
```env
# Database (use strong passwords)
DATABASE_URL=postgresql://f1user:STRONG_PASSWORD@postgres:5432/f1_analytics

# Redis (use strong passwords)
REDIS_URL=redis://:STRONG_REDIS_PASSWORD@redis:6379/0

# JWT (use: openssl rand -base64 64)
JWT_SECRET_KEY=cryptographically_secure_64_character_minimum_secret

# External APIs
WEATHER_API_KEY=your-production-weather-api-key

# Security
CORS_ORIGINS=https://yourdomain.com
ALLOWED_HOSTS=yourdomain.com

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
```

### Production Features

- **Auto-HTTPS redirect** in production environment
- **Security headers** (HSTS, CSP, X-Frame-Options, etc.)
- **Rate limiting** (30 req/min default, configurable)
- **Real health checks** with database/Redis connectivity verification
- **Comprehensive logging** with request IDs and timing
- **Resource limits** and horizontal scaling support
- **Monitoring stack** (Prometheus + Grafana)

## 📊 API Documentation

### Interactive API Docs

- **Swagger UI**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc
- **OpenAPI JSON**: http://localhost:8000/openapi.json

### Key Endpoints

| Method | Endpoint | Description | Rate Limit |
|--------|----------|-------------|------------|
| GET | `/api/v1/predictions/next-race` | Next race predictions | 30/min |
| GET | `/api/v1/races/calendar` | Race calendar | 60/min |
| GET | `/api/v1/analytics/accuracy` | Prediction accuracy metrics | 30/min |
| GET | `/api/v1/drivers/rankings` | Driver ELO rankings | 60/min |
| POST | `/api/v1/auth/login` | User authentication | 10/min |
| GET | `/api/v1/export/predictions` | Export predictions (CSV/JSON) | 5/min |
| GET | `/health` | Comprehensive health check | 300/min |

### Security Features

- **JWT Authentication** with secure secret validation
- **Rate Limiting** per endpoint with configurable limits
- **Security Headers** (HSTS, CSP, X-Frame-Options, etc.)
- **CORS Protection** with domain whitelisting
- **Request Logging** with unique request IDs
- **Health Checks** that verify actual service connectivity
- **Error Handling** without sensitive data exposure

## 🔧 Troubleshooting

### Common Issues

**Services won't start:**
```bash
# Check service status and health
docker-compose ps
curl http://localhost:8000/health | jq '.'

# View service logs with request IDs
docker-compose logs -f backend | grep "X-Request-ID"

# Restart specific service
docker-compose restart backend
```

**Database connection issues:**
```bash
# Verify database is running and accessible
docker-compose exec postgres pg_isready -U $POSTGRES_USER -d $POSTGRES_DB

# Test database connectivity from backend
docker-compose exec backend python -c "
import asyncio
from app.main import check_database_connectivity
print('DB Connected:', asyncio.run(check_database_connectivity()))
"

# Check database logs
docker-compose logs postgres
```

**Redis connection issues:**
```bash
# Test Redis connectivity
docker-compose exec redis redis-cli -a $REDIS_PASSWORD ping

# Test Redis from backend
docker-compose exec backend python -c "
import asyncio
from app.main import check_redis_connectivity
print('Redis Connected:', asyncio.run(check_redis_connectivity()))
"
```

**Security configuration issues:**
```bash
# Validate environment security
docker-compose exec backend python -c "
from app.core.security import validate_environment_security
result = validate_environment_security()
print('Security Issues:')
for issue in result['issues']:
    print(f'  - {issue}')
"

# Check JWT secret strength
docker-compose exec backend python -c "
from app.core.security import validate_jwt_secret
try:
    validate_jwt_secret()
    print('JWT Secret: SECURE')
except Exception as e:
    print(f'JWT Secret Error: {e}')
"
```

**Rate limiting issues:**
```bash
# Check rate limit headers
curl -I http://localhost:8000/api/v1/info

# Test rate limiting
for i in {1..35}; do
  curl -s http://localhost:8000/api/v1/info >/dev/null && echo "Request $i: OK" || echo "Request $i: RATE LIMITED"
done
```

**Permission errors:**
```bash
# Fix file permissions
sudo chown -R $USER:$USER f1-analytics/
chmod +x scripts/*.sh

# Check container user
docker-compose exec backend whoami
docker-compose exec frontend whoami
```

**Port conflicts:**
```bash
# Check what's using ports
sudo lsof -i :3000
sudo lsof -i :8000

# Kill processes
sudo kill -9 $(lsof -t -i:3000)
```

### Performance Tuning

**For Development:**
```bash
# Allocate more memory to Docker
# Docker Desktop > Settings > Resources > Memory: 8GB+

# Reduce services for lower-end machines
docker-compose up -d postgres redis backend frontend
```

**For Production:**
```bash
# Scale backend instances
docker-compose up -d --scale backend=3

# Monitor resource usage
docker stats
```

## 📚 Development Workflow

### Adding New Features

1. **Create feature branch:**
   ```bash
   git checkout -b feature/new-prediction-model
   ```

2. **Develop in containers:**
   ```bash
   # Backend changes are auto-reloaded
   # Frontend has hot reload enabled
   ```

3. **Run tests:**
   ```bash
   ./scripts/dev_commands.sh test-backend
   ./scripts/dev_commands.sh test-frontend
   ```

4. **Update documentation:**
   ```bash
   # Update API documentation
   # Update this README if needed
   ```

### Code Quality

```bash
# Backend linting
docker-compose exec backend black app/
docker-compose exec backend isort app/
docker-compose exec backend flake8 app/

# Frontend linting
docker-compose exec frontend npm run lint:fix
docker-compose exec frontend npm run format
```

## 🔍 Monitoring & Logging

### Application Logs

```bash
# All services
docker-compose logs -f

# Specific service
docker-compose logs -f backend

# With timestamps
docker-compose logs -f -t backend
```

### Health Checks

All services include health checks:

```bash
# Check all service health
docker-compose ps

# Manual health check
curl http://localhost:8000/health
curl http://localhost:3000/health
```

### Performance Monitoring

- **Flower**: http://localhost:5555 (Celery tasks)
- **PostgreSQL queries**: Enable `log_statement = 'all'`
- **Redis**: Use `INFO` command in Redis CLI

## 🔐 Security & Compliance

### Security Features Summary

This application implements enterprise-grade security practices:

#### ✅ Security Vulnerabilities Fixed
- **Fixed hardcoded credentials** - All credentials now use secure environment variables
- **Fixed weak JWT secrets** - JWT secrets validated for cryptographic strength
- **Fixed false health checks** - Health endpoints now verify actual service connectivity
- **Added comprehensive error handling** - No sensitive data exposure in error messages
- **Implemented production security configurations** - Rate limiting, security headers, CORS protection

#### Security Architecture
```
Internet → Load Balancer (HTTPS) → Application (Security Headers, Rate Limiting) → Database (Encrypted)
```

#### Security Controls
- **Authentication**: JWT with 64+ character cryptographically secure secrets
- **Authorization**: Role-based access control
- **Rate Limiting**: Configurable per endpoint (30 req/min default)
- **Security Headers**: HSTS, CSP, X-Frame-Options, X-Content-Type-Options
- **CORS Protection**: Domain whitelisting, no wildcards in production
- **Data Protection**: Environment variables, no hardcoded secrets
- **Monitoring**: Request logging with unique IDs, security event tracking

#### Security Validation

```bash
# Run security checklist
./scripts/generate_secrets.sh --validate

# Comprehensive security test
docker-compose exec backend python -c "
from app.core.security import validate_environment_security
from app.core.config import validate_production_config, get_settings

settings = get_settings()
env_result = validate_environment_security()
prod_result = validate_production_config(settings)

print('=== SECURITY VALIDATION ===')
print(f'Environment: {settings.environment}')
print(f'Debug Mode: {settings.debug}')
print(f'JWT Secret Secure: {env_result[\"jwt_secret_secure\"]}')
print(f'Environment Issues: {len(env_result[\"issues\"])}')
print(f'Production Issues: {len(prod_result)}')

if env_result['issues']:
    print('\\nEnvironment Issues:')
    for issue in env_result['issues']:
        print(f'  - {issue}')

if prod_result:
    print('\\nProduction Issues:')
    for issue in prod_result:
        print(f'  - {issue}')

if not env_result['issues'] and not prod_result:
    print('\\n✅ All security checks PASSED')
else:
    print('\\n❌ Security issues found - review and fix')
"

# Test health check security
curl -s http://localhost:8000/health | jq '.checks'
```

### Security Documentation

- **Production Security Guide**: `PRODUCTION_SECURITY.md` - Comprehensive security checklist
- **Security Templates**: `.env.production.template` - Secure environment configuration
- **Security Scripts**: `scripts/generate_secrets.sh` - Cryptographically secure secret generation

### Security Contact

For security vulnerabilities, please email: security@f1analytics.com

Do not open public GitHub issues for security vulnerabilities.

## 🤝 Contributing

1. Fork the repository
2. Create feature branch
3. Make changes in Docker environment
4. Run tests and security validation
5. Submit pull request

### Development Setup for Contributors

```bash
git clone <your-fork>
cd f1-analytics
./scripts/init_dev.sh

# Run full test suite
./scripts/dev_commands.sh test-backend
./scripts/dev_commands.sh test-frontend

# Validate security configuration
./scripts/generate_secrets.sh --validate
```

### Code Review Checklist

- [ ] All tests pass (backend >80% coverage, frontend >80% coverage)
- [ ] Security validation passes
- [ ] No hardcoded credentials or secrets
- [ ] Environment variables used for configuration
- [ ] Health checks verify actual connectivity
- [ ] Error handling doesn't expose sensitive data
- [ ] Rate limiting appropriate for new endpoints
- [ ] Documentation updated

## 📄 License

MIT License - see [LICENSE](LICENSE) file for details.

## 🆘 Support

- **Documentation**: Check this README first
- **Issues**: Create GitHub issue with logs
- **Discussions**: GitHub Discussions for questions

---

**Happy Racing! 🏁**