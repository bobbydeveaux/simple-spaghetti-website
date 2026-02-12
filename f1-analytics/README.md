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

### Backend Tests

```bash
# Run all backend tests
docker-compose exec backend pytest

# Run with coverage
docker-compose exec backend pytest --cov=app

# Run specific test file
docker-compose exec backend pytest tests/test_predictions.py -v

# Run only unit tests
docker-compose exec backend pytest -m unit
```

### Frontend Tests

```bash
# Run frontend tests
docker-compose exec frontend npm test

# Run with coverage
docker-compose exec frontend npm run test:coverage

# Run in watch mode
docker-compose exec frontend npm test -- --watch
```

## 📝 Environment Configuration

### Development (.env files)

Environment files are automatically created during setup:

- `backend/.env` - Backend API configuration
- `frontend/.env` - Frontend build configuration

### Key Environment Variables

**Backend:**
```env
DATABASE_URL=postgresql://f1user:f1password@postgres:5432/f1_analytics
REDIS_URL=redis://:f1redis@redis:6379/0
JWT_SECRET_KEY=dev-secret-key-change-in-production
WEATHER_API_KEY=your-openweathermap-api-key
DEBUG=true
ENVIRONMENT=development
```

**Frontend:**
```env
VITE_API_URL=http://localhost:8000
VITE_APP_NAME=F1 Analytics Dashboard
VITE_ENVIRONMENT=development
```

## 🚀 Production Deployment

### Production Docker Compose

```bash
# Copy and configure environment
cp .env.example .env.prod
# Edit .env.prod with production values

# Deploy with production compose file
docker-compose -f docker-compose.prod.yml up -d
```

### Production Environment Variables

Create `.env.prod` with production values:

```env
# Database
POSTGRES_DB=f1_analytics_prod
POSTGRES_USER=f1user_prod
POSTGRES_PASSWORD=secure_db_password

# Redis
REDIS_PASSWORD=secure_redis_password

# JWT
JWT_SECRET_KEY=super-secure-jwt-secret-key

# External APIs
WEATHER_API_KEY=your-production-weather-api-key

# Frontend
VITE_API_URL=https://api.yourdomain.com
CORS_ORIGINS=https://yourdomain.com
ALLOWED_HOSTS=yourdomain.com,api.yourdomain.com

# Monitoring
GRAFANA_ADMIN_PASSWORD=secure_grafana_password
```

## 📊 API Documentation

### Interactive API Docs

- **Swagger UI**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc
- **OpenAPI JSON**: http://localhost:8000/openapi.json

### Key Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/v1/predictions/next-race` | Next race predictions |
| GET | `/api/v1/races/calendar` | Race calendar |
| GET | `/api/v1/analytics/accuracy` | Prediction accuracy metrics |
| GET | `/api/v1/drivers/rankings` | Driver ELO rankings |
| POST | `/api/v1/auth/login` | User authentication |
| GET | `/api/v1/export/predictions` | Export predictions (CSV/JSON) |

## 🔧 Troubleshooting

### Common Issues

**Services won't start:**
```bash
# Check service status
docker-compose ps

# View service logs
docker-compose logs backend

# Restart specific service
docker-compose restart backend
```

**Database connection issues:**
```bash
# Verify database is running
docker-compose exec postgres pg_isready -U f1user

# Check database logs
docker-compose logs postgres

# Reset database
docker-compose down -v postgres && docker-compose up -d postgres
```

**Permission errors:**
```bash
# Fix file permissions
sudo chown -R $USER:$USER f1-analytics/
chmod +x scripts/*.sh
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

## 🤝 Contributing

1. Fork the repository
2. Create feature branch
3. Make changes in Docker environment
4. Run tests
5. Submit pull request

### Development Setup for Contributors

```bash
git clone <your-fork>
cd f1-analytics
./scripts/init_dev.sh
./scripts/dev_commands.sh test-backend
./scripts/dev_commands.sh test-frontend
```

## 📄 License

MIT License - see [LICENSE](LICENSE) file for details.

## 🆘 Support

- **Documentation**: Check this README first
- **Issues**: Create GitHub issue with logs
- **Discussions**: GitHub Discussions for questions

---

**Happy Racing! 🏁**