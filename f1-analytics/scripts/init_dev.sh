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

# Check if .env file exists
if [ ! -f .env ]; then
    print_status "Creating .env file from template..."
    if [ -f .env.example ]; then
        cp .env.example .env
        print_success "Created .env file from .env.example"
    else
        print_warning ".env.example not found, creating basic .env file..."
        cat > .env << 'EOF'
# F1 Analytics Environment Variables (Development)

# Database Configuration
POSTGRES_DB=f1_analytics
POSTGRES_USER=f1user
POSTGRES_PASSWORD=f1_dev_password_2024
DATABASE_URL=postgresql://f1user:f1_dev_password_2024@postgres:5432/f1_analytics

# Redis Configuration
REDIS_PASSWORD=redis_dev_password_2024
REDIS_URL=redis://:redis_dev_password_2024@redis:6379/0

# Celery Configuration
CELERY_BROKER_URL=redis://:redis_dev_password_2024@redis:6379/0
CELERY_RESULT_BACKEND=redis://:redis_dev_password_2024@redis:6379/0

# JWT Configuration (development only - generate secure key for production)
JWT_SECRET_KEY=dev_jwt_key_change_in_production_please
JWT_ALGORITHM=HS256
JWT_EXPIRE_MINUTES=1440

# Flower Monitoring Configuration
FLOWER_BASIC_AUTH=admin:flower_dev_password

# External API Configuration
ERGAST_API_URL=https://ergast.com/api/f1
WEATHER_API_KEY=your_openweathermap_api_key_here
WEATHER_API_URL=https://api.openweathermap.org/data/2.5

# Application Configuration
ENVIRONMENT=development
DEBUG=true
LOG_LEVEL=INFO
VITE_API_URL=http://localhost:8000
VITE_APP_NAME=F1 Analytics Dashboard
VITE_ENVIRONMENT=development
EOF
        print_success "Created basic .env file"
    fi
else
    print_warning ".env file already exists, skipping creation"
fi

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

# Source environment variables for health checks
set -a
source .env || print_warning "Could not source .env file"
set +a

# Check PostgreSQL
if docker-compose exec postgres pg_isready -U "${POSTGRES_USER:-f1user}" -d "${POSTGRES_DB:-f1_analytics}" &> /dev/null; then
    print_success "PostgreSQL is ready"
else
    print_error "PostgreSQL is not ready"
fi

# Check Redis
if docker-compose exec redis redis-cli -a "${REDIS_PASSWORD:-redis_dev_password_2024}" ping &> /dev/null; then
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
echo "  • Database shell: docker-compose exec postgres psql -U \$POSTGRES_USER -d \$POSTGRES_DB"
echo
echo "📝 Default admin credentials:"
echo "  • Email: admin@f1analytics.com"
echo "  • Password: admin123"
echo
echo "🔐 Security notes:"
echo "  • Update passwords in .env file for production"
echo "  • Generate secure JWT secret: openssl rand -base64 32"
echo "  • Add your OpenWeatherMap API key to WEATHER_API_KEY in .env"
echo
print_warning "Review and update credentials in .env file before production deployment!"
echo