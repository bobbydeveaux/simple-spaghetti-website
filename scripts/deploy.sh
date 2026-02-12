#!/bin/bash

# F1 Analytics Kubernetes Deployment Script
# Usage: ./scripts/deploy.sh [environment]
# Environments: development, staging, production (default)

set -e

# Configuration
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
ENVIRONMENT="${1:-production}"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Logging functions
log_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

log_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

log_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Validate environment
validate_environment() {
    case $ENVIRONMENT in
        development|staging|production)
            log_info "Deploying to environment: $ENVIRONMENT"
            ;;
        *)
            log_error "Invalid environment: $ENVIRONMENT"
            log_info "Valid environments: development, staging, production"
            exit 1
            ;;
    esac
}

# Check prerequisites
check_prerequisites() {
    log_info "Checking prerequisites..."

    # Check kubectl
    if ! command -v kubectl &> /dev/null; then
        log_error "kubectl is not installed or not in PATH"
        exit 1
    fi

    # Check kubernetes connection
    if ! kubectl cluster-info &> /dev/null; then
        log_error "Cannot connect to Kubernetes cluster"
        log_info "Please ensure kubectl is configured correctly"
        exit 1
    fi

    # Check required files
    required_files=(
        "infrastructure/kubernetes/namespace.yaml"
        "infrastructure/kubernetes/external-secrets/external-secrets-operator.yaml"
        "infrastructure/kubernetes/external-secrets/aws-iam-role.yaml"
        "infrastructure/kubernetes/external-secrets/aws-secret-store.yaml"
        "infrastructure/kubernetes/external-secrets/external-secrets.yaml"
        "infrastructure/kubernetes/configmaps.yaml"
        "infrastructure/kubernetes/postgres-statefulset.yaml"
        "infrastructure/kubernetes/redis-deployment.yaml"
        "infrastructure/kubernetes/api-gateway-deployment.yaml"
        "infrastructure/kubernetes/prediction-service-deployment.yaml"
        "infrastructure/kubernetes/frontend-deployment.yaml"
        "infrastructure/kubernetes/airflow-deployment.yaml"
        "infrastructure/kubernetes/ingress.yaml"
    )

    for file in "${required_files[@]}"; do
        if [[ ! -f "$PROJECT_ROOT/$file" ]]; then
            log_error "Required file not found: $file"
            exit 1
        fi
    done

    log_success "Prerequisites check passed"
}

# Set namespace based on environment
set_namespace() {
    case $ENVIRONMENT in
        development)
            NAMESPACE="f1-analytics-development"
            ;;
        staging)
            NAMESPACE="f1-analytics-staging"
            ;;
        production)
            NAMESPACE="f1-analytics"
            ;;
    esac

    log_info "Using namespace: $NAMESPACE"

    # Set current context to namespace
    kubectl config set-context --current --namespace="$NAMESPACE"
}

# Deploy namespaces
deploy_namespaces() {
    log_info "Creating namespaces..."
    kubectl apply -f "$PROJECT_ROOT/infrastructure/kubernetes/namespace.yaml"
    log_success "Namespaces created"
}

# Deploy External Secrets Operator and secrets
deploy_secrets() {
    log_info "Deploying External Secrets Operator and secrets..."

    # Check if External Secrets Operator directory exists
    if [[ ! -d "$PROJECT_ROOT/infrastructure/kubernetes/external-secrets" ]]; then
        log_error "External Secrets configuration not found!"
        log_error "Please ensure external-secrets/ directory exists with proper configuration"
        exit 1
    fi

    # Deploy External Secrets Operator
    log_info "Deploying External Secrets Operator..."
    kubectl apply -f "$PROJECT_ROOT/infrastructure/kubernetes/external-secrets/external-secrets-operator.yaml" || {
        log_warning "External Secrets Operator may already be installed, continuing..."
    }

    # Wait for operator to be ready
    log_info "Waiting for External Secrets Operator to be ready..."
    sleep 30

    # Deploy IAM role and service account
    log_info "Deploying IAM roles and service accounts..."
    kubectl apply -f "$PROJECT_ROOT/infrastructure/kubernetes/external-secrets/aws-iam-role.yaml"

    # Deploy secret stores
    log_info "Deploying AWS Secret Stores..."
    kubectl apply -f "$PROJECT_ROOT/infrastructure/kubernetes/external-secrets/aws-secret-store.yaml"

    # Deploy external secrets
    log_info "Deploying External Secrets..."
    kubectl apply -f "$PROJECT_ROOT/infrastructure/kubernetes/external-secrets/external-secrets.yaml"

    log_success "External Secrets Operator and secrets deployed"
    log_info "Secrets will be automatically synchronized from AWS Secrets Manager"
}

# Deploy configuration
deploy_config() {
    log_info "Deploying configuration..."
    kubectl apply -f "$PROJECT_ROOT/infrastructure/kubernetes/configmaps.yaml"
    kubectl apply -f "$PROJECT_ROOT/infrastructure/kubernetes/postgres-config.yaml"
    kubectl apply -f "$PROJECT_ROOT/infrastructure/kubernetes/redis-config.yaml"
    log_success "Configuration deployed"
}

# Deploy database layer
deploy_database() {
    log_info "Deploying database layer..."

    # PostgreSQL
    kubectl apply -f "$PROJECT_ROOT/infrastructure/kubernetes/postgres-statefulset.yaml"
    log_info "Waiting for PostgreSQL to be ready..."
    kubectl wait --for=condition=ready pod -l app=postgres --timeout=300s -n "$NAMESPACE" || {
        log_error "PostgreSQL deployment failed"
        kubectl describe pods -l app=postgres -n "$NAMESPACE"
        exit 1
    }

    # Redis
    kubectl apply -f "$PROJECT_ROOT/infrastructure/kubernetes/redis-deployment.yaml"
    log_info "Waiting for Redis to be ready..."
    kubectl wait --for=condition=ready pod -l app=redis --timeout=180s -n "$NAMESPACE" || {
        log_error "Redis deployment failed"
        kubectl describe pods -l app=redis -n "$NAMESPACE"
        exit 1
    }

    log_success "Database layer deployed successfully"
}

# Deploy application services
deploy_applications() {
    log_info "Deploying application services..."

    # API Gateway
    log_info "Deploying API Gateway..."
    kubectl apply -f "$PROJECT_ROOT/infrastructure/kubernetes/api-gateway-deployment.yaml"

    # Prediction Service
    log_info "Deploying Prediction Service..."
    kubectl apply -f "$PROJECT_ROOT/infrastructure/kubernetes/prediction-service-deployment.yaml"

    # Frontend
    log_info "Deploying Frontend..."
    kubectl apply -f "$PROJECT_ROOT/infrastructure/kubernetes/frontend-deployment.yaml"

    # Airflow
    log_info "Deploying Airflow..."
    kubectl apply -f "$PROJECT_ROOT/infrastructure/kubernetes/airflow-deployment.yaml"

    log_info "Waiting for application services to be ready..."
    sleep 30

    # Check service status
    kubectl get pods -n "$NAMESPACE" -o wide

    log_success "Application services deployed"
}

# Deploy ingress
deploy_ingress() {
    log_info "Deploying ingress..."

    # Deploy environment-specific domain configuration first
    if [[ -f "$PROJECT_ROOT/infrastructure/kubernetes/environments/$ENVIRONMENT/domains.yaml" ]]; then
        kubectl apply -f "$PROJECT_ROOT/infrastructure/kubernetes/environments/$ENVIRONMENT/domains.yaml"
        log_info "Environment-specific domain configuration applied"
    fi

    # Deploy environment-specific ingress if available
    if [[ -f "$PROJECT_ROOT/infrastructure/kubernetes/environments/$ENVIRONMENT/ingress.yaml" ]]; then
        kubectl apply -f "$PROJECT_ROOT/infrastructure/kubernetes/environments/$ENVIRONMENT/ingress.yaml"
        log_info "Environment-specific ingress applied"
    else
        # Deploy general ingress
        kubectl apply -f "$PROJECT_ROOT/infrastructure/kubernetes/ingress.yaml"
        log_info "General ingress applied"
    fi

    log_success "Ingress deployed"
}

# Deploy monitoring (optional)
deploy_monitoring() {
    if [[ -d "$PROJECT_ROOT/infrastructure/monitoring" ]]; then
        log_info "Deploying monitoring stack..."

        kubectl apply -f "$PROJECT_ROOT/infrastructure/monitoring/prometheus.yaml"
        kubectl apply -f "$PROJECT_ROOT/infrastructure/monitoring/grafana.yaml"
        kubectl apply -f "$PROJECT_ROOT/infrastructure/monitoring/exporters.yaml"

        log_success "Monitoring stack deployed"
    else
        log_warning "Monitoring configuration not found, skipping"
    fi
}

# Run health checks
run_health_checks() {
    log_info "Running health checks..."

    # Check pod status
    log_info "Pod Status:"
    kubectl get pods -n "$NAMESPACE"

    # Check service status
    log_info "Service Status:"
    kubectl get svc -n "$NAMESPACE"

    # Check ingress status
    log_info "Ingress Status:"
    kubectl get ingress -n "$NAMESPACE" 2>/dev/null || log_warning "No ingress found"

    # Wait for pods to be ready
    log_info "Waiting for all pods to be ready..."
    if kubectl wait --for=condition=ready pod --all --timeout=300s -n "$NAMESPACE"; then
        log_success "All pods are ready"
    else
        log_warning "Some pods are not ready, check pod status above"
    fi
}

# Print access information
print_access_info() {
    log_success "Deployment completed successfully!"
    echo
    log_info "=== Access Information ==="

    case $ENVIRONMENT in
        production)
            echo "Frontend: https://f1-analytics.com"
            echo "API: https://api.f1-analytics.com"
            echo "Airflow: https://airflow.f1-analytics.com"
            echo "Grafana: https://grafana.f1-analytics.com"
            echo ""
            echo "NOTE: Replace f1-analytics.com with your actual domain in:"
            echo "  - infrastructure/kubernetes/environments/production/domains.yaml"
            echo "  - infrastructure/kubernetes/environments/production/ingress.yaml"
            ;;
        staging)
            echo "Frontend: https://staging.f1-analytics.com"
            echo "API: https://staging-api.f1-analytics.com"
            echo "Airflow: https://staging-airflow.f1-analytics.com"
            echo ""
            echo "NOTE: Replace with your actual staging domain in:"
            echo "  - infrastructure/kubernetes/environments/staging/domains.yaml"
            echo "  - infrastructure/kubernetes/environments/staging/ingress.yaml"
            ;;
        development)
            echo "Use kubectl port-forward for local access:"
            echo "kubectl port-forward svc/frontend-service 8080:80 -n $NAMESPACE"
            echo "kubectl port-forward svc/api-gateway-service 8000:8000 -n $NAMESPACE"
            echo "kubectl port-forward svc/airflow-webserver 8081:8080 -n $NAMESPACE"
            ;;
    esac

    echo
    log_info "=== Useful Commands ==="
    echo "View pods:     kubectl get pods -n $NAMESPACE"
    echo "View services: kubectl get svc -n $NAMESPACE"
    echo "View logs:     kubectl logs -l app=api-gateway -n $NAMESPACE"
    echo "Scale service: kubectl scale deployment api-gateway --replicas=5 -n $NAMESPACE"

    echo
    log_info "For detailed instructions, see: docs/KUBERNETES_DEPLOYMENT.md"
}

# Cleanup function for errors
cleanup() {
    if [[ $? -ne 0 ]]; then
        log_error "Deployment failed!"
        log_info "Check the error messages above and retry"
        log_info "You can also check pod status with: kubectl get pods -n $NAMESPACE"
        log_info "And view logs with: kubectl logs <pod-name> -n $NAMESPACE"
    fi
}

# Set trap for cleanup
trap cleanup EXIT

# Main deployment function
main() {
    echo "F1 Analytics Kubernetes Deployment Script"
    echo "=========================================="
    echo

    validate_environment
    check_prerequisites
    set_namespace

    log_info "Starting deployment to $ENVIRONMENT environment..."
    echo

    deploy_namespaces
    deploy_secrets
    deploy_config
    deploy_database
    deploy_applications
    deploy_ingress

    # Deploy monitoring only for staging and production
    if [[ "$ENVIRONMENT" != "development" ]]; then
        deploy_monitoring
    fi

    run_health_checks
    print_access_info
}

# Run main function
main "$@"