#!/bin/bash

# F1 Analytics Security Secrets Generator
# This script generates cryptographically secure secrets for production use

set -e

echo "🔐 F1 Analytics Security Secrets Generator"
echo "=========================================="

# Colors for output
GREEN='\033[0;32m'
YELLOW='\033[0;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

print_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

print_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

# Function to generate secure password
generate_password() {
    local length=${1:-32}
    openssl rand -base64 $((length * 3 / 4)) | tr -d "=+/" | cut -c1-$length
}

# Function to generate JWT secret
generate_jwt_secret() {
    openssl rand -base64 64 | tr -d "\n"
}

print_info "Generating cryptographically secure secrets..."

# Generate secrets
POSTGRES_PASSWORD=$(generate_password 32)
REDIS_PASSWORD=$(generate_password 32)
JWT_SECRET=$(generate_jwt_secret)
FLOWER_PASSWORD=$(generate_password 24)
GRAFANA_PASSWORD=$(generate_password 24)

echo
print_success "Generated secure secrets:"
echo
echo "# Generated on $(date)"
echo "# Copy these values to your .env file"
echo
echo "POSTGRES_PASSWORD=$POSTGRES_PASSWORD"
echo "REDIS_PASSWORD=$REDIS_PASSWORD"
echo "JWT_SECRET_KEY=$JWT_SECRET"
echo "FLOWER_BASIC_AUTH=admin:$FLOWER_PASSWORD"
echo "GRAFANA_ADMIN_PASSWORD=$GRAFANA_PASSWORD"

# Create a secure env file template
cat > .env.secure.generated << EOF
# F1 Analytics Secure Environment Configuration
# Generated on $(date)
# IMPORTANT: Review and customize these values before use

# Database Configuration (GENERATED - SECURE)
POSTGRES_DB=f1_analytics
POSTGRES_USER=f1user
POSTGRES_PASSWORD=$POSTGRES_PASSWORD
DATABASE_URL=postgresql://f1user:$POSTGRES_PASSWORD@postgres:5432/f1_analytics

# Redis Configuration (GENERATED - SECURE)
REDIS_PASSWORD=$REDIS_PASSWORD
REDIS_URL=redis://:$REDIS_PASSWORD@redis:6379/0

# Celery Configuration (GENERATED - SECURE)
CELERY_BROKER_URL=redis://:$REDIS_PASSWORD@redis:6379/0
CELERY_RESULT_BACKEND=redis://:$REDIS_PASSWORD@redis:6379/0

# JWT Configuration (GENERATED - SECURE)
JWT_SECRET_KEY=$JWT_SECRET
JWT_ALGORITHM=HS256
JWT_EXPIRE_MINUTES=1440

# Flower Monitoring Configuration (GENERATED - SECURE)
FLOWER_BASIC_AUTH=admin:$FLOWER_PASSWORD

# Monitoring Configuration (GENERATED - SECURE)
GRAFANA_ADMIN_PASSWORD=$GRAFANA_PASSWORD

# External API Configuration (UPDATE REQUIRED)
ERGAST_API_URL=https://ergast.com/api/f1
WEATHER_API_KEY=your_openweathermap_api_key_here
WEATHER_API_URL=https://api.openweathermap.org/data/2.5

# Application Configuration (REVIEW AND UPDATE)
ENVIRONMENT=development
DEBUG=true
LOG_LEVEL=INFO
VITE_API_URL=http://localhost:8000
VITE_APP_NAME=F1 Analytics Dashboard
VITE_ENVIRONMENT=development

# Security Configuration for Production (UPDATE REQUIRED)
CORS_ORIGINS=http://localhost:3000,http://127.0.0.1:3000
ALLOWED_HOSTS=localhost,127.0.0.1,0.0.0.0
EOF

echo
print_success "Created .env.secure.generated file with secure defaults"
echo
print_warning "NEXT STEPS:"
echo "1. Copy .env.secure.generated to .env"
echo "2. Update API keys and domain configurations"
echo "3. For production: Update CORS_ORIGINS and ALLOWED_HOSTS"
echo "4. Delete .env.secure.generated file after copying"
echo
print_warning "SECURITY REMINDER:"
echo "- Never commit .env files to version control"
echo "- Rotate these secrets regularly in production"
echo "- Use different secrets for each environment"
echo "- Store production secrets in secure secret management system"