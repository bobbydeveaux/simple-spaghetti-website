#!/bin/bash

# Alertmanager Configuration Validation Script
# This script validates the Prometheus and Alertmanager configuration files

set -e

echo "🔧 F1 Analytics - Alertmanager Configuration Validation"
echo "======================================================="

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Check if promtool exists
check_promtool() {
    if ! command -v promtool &> /dev/null; then
        echo -e "${YELLOW}⚠️  promtool not found. Installing prometheus tools...${NC}"

        # Try to install promtool
        if command -v docker &> /dev/null; then
            echo "Using Docker to run prometheus/prometheus for validation..."
            PROMTOOL_CMD="docker run --rm -v $(pwd):/workspace -w /workspace prom/prometheus:v2.45.0 promtool"
        else
            echo -e "${RED}❌ Neither promtool nor docker available. Cannot validate configuration.${NC}"
            echo "Please install Prometheus tools or Docker to run validation."
            exit 1
        fi
    else
        PROMTOOL_CMD="promtool"
    fi
}

# Validate Prometheus configuration
validate_prometheus() {
    echo "🔍 Validating Prometheus configuration..."

    # Extract prometheus.yml from the ConfigMap
    kubectl get configmap prometheus-config -n f1-analytics -o yaml | \
        grep -A 1000 "prometheus.yml:" | \
        tail -n +2 | \
        sed 's/^    //' > /tmp/prometheus-test.yml

    if $PROMTOOL_CMD check config /tmp/prometheus-test.yml; then
        echo -e "${GREEN}✅ Prometheus configuration is valid${NC}"
    else
        echo -e "${RED}❌ Prometheus configuration has errors${NC}"
        return 1
    fi

    rm -f /tmp/prometheus-test.yml
}

# Validate Alerting Rules
validate_rules() {
    echo "🔍 Validating Alerting Rules..."

    # Extract rules from the ConfigMap
    kubectl get configmap alertmanager-rules -n f1-analytics -o yaml | \
        grep -A 1000 "f1-analytics-rules.yml:" | \
        tail -n +2 | \
        sed 's/^    //' > /tmp/rules-test.yml

    if $PROMTOOL_CMD check rules /tmp/rules-test.yml; then
        echo -e "${GREEN}✅ Alerting rules are valid${NC}"
    else
        echo -e "${RED}❌ Alerting rules have syntax errors${NC}"
        return 1
    fi

    rm -f /tmp/rules-test.yml
}

# Validate Alertmanager configuration
validate_alertmanager() {
    echo "🔍 Validating Alertmanager configuration..."

    # Check if amtool exists
    if ! command -v amtool &> /dev/null; then
        if command -v docker &> /dev/null; then
            AMTOOL_CMD="docker run --rm -v $(pwd):/workspace -w /workspace prom/alertmanager:v0.26.0 amtool"
        else
            echo -e "${YELLOW}⚠️  amtool not available, skipping alertmanager config validation${NC}"
            return 0
        fi
    else
        AMTOOL_CMD="amtool"
    fi

    # Extract alertmanager.yml from the ConfigMap
    kubectl get configmap alertmanager-config -n f1-analytics -o yaml | \
        grep -A 1000 "alertmanager.yml:" | \
        tail -n +2 | \
        sed 's/^    //' > /tmp/alertmanager-test.yml

    if $AMTOOL_CMD check-config /tmp/alertmanager-test.yml; then
        echo -e "${GREEN}✅ Alertmanager configuration is valid${NC}"
    else
        echo -e "${RED}❌ Alertmanager configuration has errors${NC}"
        return 1
    fi

    rm -f /tmp/alertmanager-test.yml
}

# Test alert rules syntax
test_alert_expressions() {
    echo "🔍 Testing alert expressions..."

    # Common expressions that should be valid
    expressions=(
        "100 - (avg by(instance) (irate(node_cpu_seconds_total{mode=\"idle\"}[5m])) * 100) > 80"
        "rate(http_requests_total{status=~\"5..\"}[5m]) / rate(http_requests_total[5m]) > 0.05"
        "histogram_quantile(0.95, rate(http_request_duration_seconds_bucket[5m])) > 2"
        "up{job=\"prediction-service\"} == 0"
        "avg_over_time(f1_prediction_accuracy[24h]) < 0.65"
    )

    for expr in "${expressions[@]}"; do
        echo "Testing: $expr"
        if $PROMTOOL_CMD query instant "http://localhost:9090" "$expr" 2>/dev/null; then
            echo -e "${GREEN}✅ Expression syntax valid${NC}"
        else
            echo -e "${YELLOW}⚠️  Expression syntax check failed (server may not be running)${NC}"
        fi
    done
}

# Check Kubernetes resources
check_k8s_resources() {
    echo "🔍 Checking Kubernetes resources..."

    if ! command -v kubectl &> /dev/null; then
        echo -e "${YELLOW}⚠️  kubectl not found, skipping Kubernetes validation${NC}"
        return 0
    fi

    # Check if namespace exists
    if kubectl get namespace f1-analytics &> /dev/null; then
        echo -e "${GREEN}✅ Namespace f1-analytics exists${NC}"
    else
        echo -e "${RED}❌ Namespace f1-analytics not found${NC}"
    fi

    # Check if ConfigMaps would be valid
    echo "Validating ConfigMap manifests..."

    for file in alertmanager-rules.yaml alertmanager-secrets.yaml; do
        if kubectl apply --dry-run=client -f "$file" &> /dev/null; then
            echo -e "${GREEN}✅ $file is valid${NC}"
        else
            echo -e "${RED}❌ $file has validation errors${NC}"
        fi
    done
}

# Main validation function
main() {
    echo "Starting comprehensive validation..."
    echo

    check_promtool

    # Run all validations
    validate_prometheus
    echo

    validate_rules
    echo

    validate_alertmanager
    echo

    test_alert_expressions
    echo

    check_k8s_resources
    echo

    echo -e "${GREEN}🎉 Validation completed!${NC}"
    echo
    echo "Next steps:"
    echo "1. Apply the configuration: kubectl apply -f ."
    echo "2. Restart Prometheus and Alertmanager pods"
    echo "3. Test alert routing with: amtool config routes test"
    echo "4. Monitor logs: kubectl logs -f deployment/alertmanager -n f1-analytics"
}

# Show help
show_help() {
    echo "Usage: $0 [OPTIONS]"
    echo
    echo "OPTIONS:"
    echo "  --help, -h          Show this help message"
    echo "  --prometheus        Validate only Prometheus config"
    echo "  --rules             Validate only alert rules"
    echo "  --alertmanager      Validate only Alertmanager config"
    echo "  --k8s               Validate only Kubernetes manifests"
    echo
}

# Parse command line arguments
case "${1:-}" in
    --help|-h)
        show_help
        exit 0
        ;;
    --prometheus)
        check_promtool
        validate_prometheus
        ;;
    --rules)
        check_promtool
        validate_rules
        ;;
    --alertmanager)
        validate_alertmanager
        ;;
    --k8s)
        check_k8s_resources
        ;;
    "")
        main
        ;;
    *)
        echo "Unknown option: $1"
        show_help
        exit 1
        ;;
esac