#!/bin/bash

# F1 Analytics Development Helper Commands
# Provides common development operations

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[0;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

print_usage() {
    echo "🏎️  F1 Analytics Development Commands"
    echo "===================================="
    echo
    echo "Usage: $0 <command> [options]"
    echo
    echo "Commands:"
    echo "  start           Start all services"
    echo "  stop            Stop all services"
    echo "  restart         Restart all services"
    echo "  logs [service]  Show logs (optionally for specific service)"
    echo "  build           Rebuild all containers"
    echo "  clean           Stop and remove all containers and volumes"
    echo "  db-shell        Open PostgreSQL shell"
    echo "  redis-shell     Open Redis shell"
    echo "  backend-shell   Open backend container shell"
    echo "  test-backend    Run backend tests"
    echo "  test-frontend   Run frontend tests"
    echo "  migrate         Run database migrations"
    echo "  seed-data       Load sample data"
    echo "  status          Show service status"
    echo
    echo "Examples:"
    echo "  $0 start"
    echo "  $0 logs backend"
    echo "  $0 test-backend"
    echo "  $0 clean"
}

print_status() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

print_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Get script directory and project root
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
COMPOSE_DIR="$PROJECT_ROOT/infrastructure"

# Change to compose directory
cd "$COMPOSE_DIR"

case "$1" in
    start)
        print_status "Starting F1 Analytics services..."
        docker-compose up -d
        print_success "Services started"
        ;;

    stop)
        print_status "Stopping F1 Analytics services..."
        docker-compose down
        print_success "Services stopped"
        ;;

    restart)
        print_status "Restarting F1 Analytics services..."
        docker-compose restart
        print_success "Services restarted"
        ;;

    logs)
        if [ -n "$2" ]; then
            print_status "Showing logs for $2..."
            docker-compose logs -f "$2"
        else
            print_status "Showing logs for all services..."
            docker-compose logs -f
        fi
        ;;

    build)
        print_status "Building all containers..."
        docker-compose build --no-cache
        print_success "Build completed"
        ;;

    clean)
        print_status "Cleaning up all containers and volumes..."
        docker-compose down --volumes --remove-orphans
        docker system prune -f
        print_success "Cleanup completed"
        ;;

    db-shell)
        print_status "Opening PostgreSQL shell..."
        docker-compose exec postgres psql -U f1user -d f1_analytics
        ;;

    redis-shell)
        print_status "Opening Redis shell..."
        docker-compose exec redis redis-cli -a f1redis
        ;;

    backend-shell)
        print_status "Opening backend container shell..."
        docker-compose exec backend bash
        ;;

    test-backend)
        print_status "Running backend tests..."
        docker-compose exec backend pytest tests/ -v
        ;;

    test-frontend)
        print_status "Running frontend tests..."
        docker-compose exec frontend npm test
        ;;

    migrate)
        print_status "Running database migrations..."
        docker-compose exec backend alembic upgrade head
        print_success "Migrations completed"
        ;;

    seed-data)
        print_status "Loading sample data..."
        docker-compose exec backend python scripts/seed_sample_data.py
        print_success "Sample data loaded"
        ;;

    status)
        print_status "Service status:"
        docker-compose ps
        ;;

    *)
        print_error "Unknown command: $1"
        print_usage
        exit 1
        ;;
esac