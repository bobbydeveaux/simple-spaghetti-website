#!/bin/bash

# F1 Analytics - Secure Secret Generation Script
# This script generates cryptographically secure secrets for production deployment

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"
OUTPUT_FILE="$PROJECT_DIR/.env.secure.generated"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Print with color
print_header() {
    echo -e "${BLUE}=====================================
🔐 F1 Analytics Security Generator
=====================================${NC}"
}

print_success() {
    echo -e "${GREEN}✅ $1${NC}"
}

print_warning() {
    echo -e "${YELLOW}⚠️  $1${NC}"
}

print_error() {
    echo -e "${RED}❌ $1${NC}"
}

# Generate a cryptographically secure password
generate_password() {
    local length=${1:-24}
    openssl rand -base64 $((length * 3 / 4)) | tr -d "=+/" | cut -c1-${length}
}

# Generate a JWT secret (64 characters minimum)
generate_jwt_secret() {
    openssl rand -base64 64 | tr -d "\n="
}

# Generate a UUID
generate_uuid() {
    python3 -c "import uuid; print(str(uuid.uuid4()))"
}

# Validate generated secrets
validate_secrets() {
    local env_file="$1"

    echo -e "\n${BLUE}🔍 Validating generated secrets...${NC}"

    # Check JWT secret length
    jwt_secret=$(grep "JWT_SECRET_KEY=" "$env_file" | cut -d'=' -f2)
    if [ ${#jwt_secret} -lt 64 ]; then
        print_error "JWT secret is too short (${#jwt_secret} characters, minimum 64 required)"
        return 1
    fi
    print_success "JWT secret length: ${#jwt_secret} characters"

    # Check password lengths
    db_pass=$(grep "POSTGRES_PASSWORD=" "$env_file" | cut -d'=' -f2)
    redis_pass=$(grep "REDIS_PASSWORD=" "$env_file" | cut -d'=' -f2)
    grafana_pass=$(grep "GRAFANA_ADMIN_PASSWORD=" "$env_file" | cut -d'=' -f2)

    if [ ${#db_pass} -lt 16 ]; then
        print_error "Database password is too short (${#db_pass} characters, minimum 16 required)"
        return 1
    fi
    print_success "Database password length: ${#db_pass} characters"

    if [ ${#redis_pass} -lt 16 ]; then
        print_error "Redis password is too short (${#redis_pass} characters, minimum 16 required)"
        return 1
    fi
    print_success "Redis password length: ${#redis_pass} characters"

    if [ ${#grafana_pass} -lt 16 ]; then
        print_error "Grafana password is too short (${#grafana_pass} characters, minimum 16 required)"
        return 1
    fi
    print_success "Grafana password length: ${#grafana_pass} characters"

    print_success "All secrets pass validation!"
    return 0
}

# Main secret generation function
generate_secrets() {
    print_header

    echo -e "\n${BLUE}🔧 Generating cryptographically secure secrets...${NC}"

    # Remove existing file if it exists
    if [ -f "$OUTPUT_FILE" ]; then
        print_warning "Removing existing generated secrets file"
        rm "$OUTPUT_FILE"
    fi

    # Generate secrets
    echo "# F1 Analytics - Generated Secure Environment Variables"
    echo "# Generated on: $(date)"
    echo "# WARNING: Keep these secrets secure and do not commit to version control!"
    echo ""
    echo "# Database Configuration"
    echo "POSTGRES_DB=f1_analytics_prod"
    echo "POSTGRES_USER=f1user_prod"
    echo "POSTGRES_PASSWORD=$(generate_password 24)"
    echo ""
    echo "# Redis Configuration"
    echo "REDIS_PASSWORD=$(generate_password 24)"
    echo ""
    echo "# JWT Configuration - CRITICAL: Cryptographically secure"
    echo "JWT_SECRET_KEY=$(generate_jwt_secret)"
    echo "JWT_ALGORITHM=HS256"
    echo "JWT_EXPIRE_MINUTES=60"
    echo ""
    echo "# External API Configuration"
    echo "ERGAST_API_URL=https://ergast.com/api/f1"
    echo "WEATHER_API_KEY=your_production_openweathermap_api_key"
    echo "WEATHER_API_URL=https://api.openweathermap.org/data/2.5"
    echo ""
    echo "# Application Configuration"
    echo "ENVIRONMENT=production"
    echo "DEBUG=false"
    echo "LOG_LEVEL=WARNING"
    echo ""
    echo "# Security Configuration"
    echo "CORS_ORIGINS=https://your-production-domain.com"
    echo "ALLOWED_HOSTS=your-production-domain.com"
    echo ""
    echo "# Rate Limiting Configuration"
    echo "RATE_LIMIT_PER_MINUTE=30"
    echo "RATE_LIMIT_BURST=60"
    echo ""
    echo "# Database Pool Configuration"
    echo "DATABASE_POOL_SIZE=10"
    echo "DATABASE_MAX_OVERFLOW=20"
    echo ""
    echo "# Redis Connection Pool"
    echo "REDIS_MAX_CONNECTIONS=50"
    echo ""
    echo "# Monitoring Configuration"
    echo "GRAFANA_ADMIN_PASSWORD=$(generate_password 20)"
    echo "ENABLE_METRICS=true"
    echo "METRICS_PORT=9090"
    echo ""
    echo "# Flower Configuration"
    echo "FLOWER_BASIC_AUTH=admin:$(generate_password 16)"
    echo ""
    echo "# Generated URLs (update with actual database/redis hosts in production)"
    db_password=$(generate_password 24)
    redis_password=$(generate_password 24)
    echo "DATABASE_URL=postgresql://f1user_prod:${db_password}@postgres:5432/f1_analytics_prod"
    echo "REDIS_URL=redis://:${redis_password}@redis:6379/0"
    echo "CELERY_BROKER_URL=redis://:${redis_password}@redis:6379/0"
    echo "CELERY_RESULT_BACKEND=redis://:${redis_password}@redis:6379/0"
} > "$OUTPUT_FILE"

# Show usage information
show_usage() {
    echo "Usage: $0 [--validate] [--help]"
    echo ""
    echo "Options:"
    echo "  --validate    Validate existing .env file security"
    echo "  --help       Show this help message"
    echo ""
    echo "Example:"
    echo "  $0                    # Generate new secure secrets"
    echo "  $0 --validate         # Validate existing configuration"
}

# Validate existing environment file
validate_existing() {
    local env_files=(".env" ".env.production" ".env.local")

    print_header
    echo -e "\n${BLUE}🔍 Validating existing environment files...${NC}"

    local found_env=false

    for env_file in "${env_files[@]}"; do
        if [ -f "$PROJECT_DIR/$env_file" ]; then
            echo -e "\n${BLUE}Checking $env_file...${NC}"
            found_env=true

            # Check for weak patterns (expanded list)
            weak_pattern="change.*this\|weak\|dev.*secret\|test.*secret\|f1password\|f1redis\|generate.*secure\|<generate_\|production.*password.*here\|minimum.*characters\|openssl.*rand\|base64.*64"
            if grep -iq "$weak_pattern" "$PROJECT_DIR/$env_file"; then
                print_error "Found weak/development/template credentials in $env_file"
                grep -i "$weak_pattern" "$PROJECT_DIR/$env_file" | head -5
                continue
            fi

            # Validate secret lengths
            if validate_secrets "$PROJECT_DIR/$env_file"; then
                print_success "$env_file passes security validation"
            else
                print_error "$env_file failed security validation"
            fi
        fi
    done

    if [ "$found_env" = false ]; then
        print_warning "No environment files found to validate"
        echo "Run without --validate to generate secure secrets"
    fi
}

# Main script logic
main() {
    case "${1:-}" in
        --validate)
            validate_existing
            ;;
        --help|-h)
            show_usage
            ;;
        "")
            generate_secrets

            echo ""
            print_success "Secure secrets generated successfully!"
            print_success "Output file: $OUTPUT_FILE"
            echo ""
            print_warning "Next steps:"
            echo "1. Copy the generated file to your production environment"
            echo "2. Rename it to .env.production"
            echo "3. Update domain names and API keys as needed"
            echo "4. Delete the .env.secure.generated file after copying"
            echo ""
            print_warning "Security reminders:"
            echo "• Never commit .env files to version control"
            echo "• Store secrets in a secure secrets management system"
            echo "• Rotate secrets regularly"
            echo "• Use HTTPS only in production"
            echo ""

            # Validate the generated file
            if validate_secrets "$OUTPUT_FILE"; then
                echo ""
                print_success "Generated secrets pass all security validations!"
            fi
            ;;
        *)
            print_error "Unknown option: $1"
            show_usage
            exit 1
            ;;
    esac
}

# Check dependencies
check_dependencies() {
    if ! command -v openssl &> /dev/null; then
        print_error "OpenSSL is required but not installed"
        exit 1
    fi

    if ! command -v python3 &> /dev/null; then
        print_error "Python 3 is required but not installed"
        exit 1
    fi
}

# Run the script
check_dependencies
main "$@"