#!/bin/bash

# F1 Analytics Development Environment Setup Script
# This script initializes the complete development environment

set -e

echo "🏎️  F1 Analytics Development Environment Setup"
echo "=============================================="

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[0;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Function to print colored output
print_status() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

print_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Check if Docker is installed
if ! command -v docker &> /dev/null; then
    print_error "Docker is not installed. Please install Docker first."
    exit 1
fi

# Check if Docker Compose is installed
if ! command -v docker-compose &> /dev/null && ! docker compose version &> /dev/null; then
    print_error "Docker Compose is not installed. Please install Docker Compose first."
    exit 1
fi

# Set the correct directory
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
cd "$PROJECT_ROOT"

print_status "Project root: $PROJECT_ROOT"

# Create necessary directories
print_status "Creating necessary directories..."
mkdir -p f1-analytics/backend/app
mkdir -p f1-analytics/backend/models
mkdir -p f1-analytics/backend/logs
mkdir -p f1-analytics/frontend/src
mkdir -p f1-analytics/infrastructure/monitoring
mkdir -p f1-analytics/data/models
mkdir -p f1-analytics/data/cache

# Create environment files
print_status "Creating environment configuration files..."

# Backend .env file
cat > f1-analytics/backend/.env << 'EOF'
# F1 Analytics Backend Environment Variables (Development)

# Database
DATABASE_URL=postgresql://f1user:f1password@localhost:5432/f1_analytics

# Redis
REDIS_URL=redis://:f1redis@localhost:6379/0

# JWT
JWT_SECRET_KEY=dev-secret-key-change-in-production-please
JWT_ALGORITHM=HS256
JWT_EXPIRE_MINUTES=1440

# External APIs
ERGAST_API_URL=https://ergast.com/api/f1
WEATHER_API_KEY=your-openweathermap-api-key-here
WEATHER_API_URL=https://api.openweathermap.org/data/2.5

# Celery
CELERY_BROKER_URL=redis://:f1redis@localhost:6379/0
CELERY_RESULT_BACKEND=redis://:f1redis@localhost:6379/0

# Environment
ENVIRONMENT=development
DEBUG=true
LOG_LEVEL=INFO

# Security
CORS_ORIGINS=http://localhost:3000,http://127.0.0.1:3000
ALLOWED_HOSTS=localhost,127.0.0.1,0.0.0.0

# ML Models
MODEL_STORAGE_PATH=/app/models
MODEL_CACHE_TTL=3600
EOF

# Frontend .env file
cat > f1-analytics/frontend/.env << 'EOF'
# F1 Analytics Frontend Environment Variables (Development)

VITE_API_URL=http://localhost:8000
VITE_APP_NAME=F1 Analytics Dashboard
VITE_ENVIRONMENT=development
VITE_DEBUG=true

# Features
VITE_ENABLE_ANALYTICS=true
VITE_ENABLE_PREDICTIONS=true
VITE_ENABLE_HISTORICAL_DATA=true
EOF

print_success "Environment files created"

# Stop any existing containers
print_status "Stopping any existing containers..."
cd f1-analytics/infrastructure
docker-compose down --remove-orphans 2>/dev/null || true

# Build and start the services
print_status "Building Docker images..."
docker-compose build --no-cache

print_status "Starting services..."
docker-compose up -d

# Wait for services to be ready
print_status "Waiting for services to be ready..."
sleep 10

# Check if services are running
print_status "Checking service health..."

# Check PostgreSQL
if docker-compose exec postgres pg_isready -U f1user -d f1_analytics &> /dev/null; then
    print_success "PostgreSQL is ready"
else
    print_error "PostgreSQL is not ready"
fi

# Check Redis
if docker-compose exec redis redis-cli ping &> /dev/null; then
    print_success "Redis is ready"
else
    print_error "Redis is not ready"
fi

# Check Backend API
print_status "Waiting for backend API..."
max_attempts=30
attempt=1

while [ $attempt -le $max_attempts ]; do
    if curl -s http://localhost:8000/health &> /dev/null; then
        print_success "Backend API is ready"
        break
    fi

    if [ $attempt -eq $max_attempts ]; then
        print_error "Backend API is not responding after $max_attempts attempts"
        print_error "Check the logs with: cd f1-analytics/infrastructure && docker-compose logs backend"
    fi

    sleep 2
    ((attempt++))
done

# Check Frontend
print_status "Waiting for frontend..."
max_attempts=15
attempt=1

while [ $attempt -le $max_attempts ]; do
    if curl -s http://localhost:3000/health &> /dev/null; then
        print_success "Frontend is ready"
        break
    fi

    if [ $attempt -eq $max_attempts ]; then
        print_error "Frontend is not responding after $max_attempts attempts"
        print_error "Check the logs with: cd f1-analytics/infrastructure && docker-compose logs frontend"
    fi

    sleep 2
    ((attempt++))
done

echo
print_success "🎉 F1 Analytics Development Environment is ready!"
echo
echo "📊 Access points:"
echo "  • Frontend Dashboard: http://localhost:3000"
echo "  • Backend API: http://localhost:8000"
echo "  • API Documentation: http://localhost:8000/docs"
echo "  • Flower (Task Monitor): http://localhost:5555"
echo "  • PostgreSQL: localhost:5432"
echo "  • Redis: localhost:6379"
echo
echo "🔧 Useful commands:"
echo "  • View logs: cd f1-analytics/infrastructure && docker-compose logs -f [service-name]"
echo "  • Stop services: cd f1-analytics/infrastructure && docker-compose down"
echo "  • Restart services: cd f1-analytics/infrastructure && docker-compose restart"
echo "  • Shell into backend: docker-compose exec backend bash"
echo "  • Database shell: docker-compose exec postgres psql -U f1user -d f1_analytics"
echo
echo "📝 Default admin credentials:"
echo "  • Email: admin@f1analytics.com"
echo "  • Password: admin123"
echo
print_warning "Don't forget to update API keys in the .env files for external services!"
echo