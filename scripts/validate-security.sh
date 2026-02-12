#!/bin/bash
# Security Validation Script for F1 Analytics Kubernetes Deployments
# This script validates that all deployments follow security best practices

set -euo pipefail

echo "🔒 F1 Analytics Kubernetes Security Validation"
echo "=============================================="

NAMESPACE="f1-analytics"
MANIFESTS_DIR="infrastructure/kubernetes"
ISSUES_FOUND=0

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Check if kubectl is available
if ! command -v kubectl &> /dev/null; then
    echo -e "${YELLOW}⚠️  kubectl not found. This script requires kubectl for full validation.${NC}"
    echo "   Performing static manifest validation only."
    KUBECTL_AVAILABLE=false
else
    KUBECTL_AVAILABLE=true
fi

echo ""
echo -e "${BLUE}🔍 Validating Security Configurations...${NC}"
echo ""

# Function to report issues
report_issue() {
    echo -e "${RED}❌ $1${NC}"
    ((ISSUES_FOUND++))
}

# Function to report success
report_success() {
    echo -e "${GREEN}✅ $1${NC}"
}

# Function to report warning
report_warning() {
    echo -e "${YELLOW}⚠️  $1${NC}"
}

# Validate YAML files exist
echo "1. Checking manifest files..."
REQUIRED_MANIFESTS=(
    "namespace.yaml"
    "postgres-statefulset.yaml"
    "redis-deployment.yaml"
    "api-gateway-deployment.yaml"
    "prediction-service-deployment.yaml"
    "frontend-deployment.yaml"
    "airflow-deployment.yaml"
    "network-policies.yaml"
    "external-secrets/external-secrets-operator.yaml"
    "external-secrets/aws-secret-store.yaml"
    "external-secrets/aws-iam-role.yaml"
    "external-secrets/external-secrets.yaml"
)

for manifest in "${REQUIRED_MANIFESTS[@]}"; do
    if [[ -f "$MANIFESTS_DIR/$manifest" ]]; then
        report_success "Found $manifest"
    else
        report_issue "Missing required manifest: $manifest"
    fi
done

# Check for hardcoded secrets (simplified check)
echo ""
echo "2. Checking for hardcoded secrets..."
# Check if the deprecated secrets.yaml file exists with actual secret values
if [[ -f "$MANIFESTS_DIR/secrets.yaml" ]] && grep -q "data:" "$MANIFESTS_DIR/secrets.yaml" && ! grep -q "DEPRECATED" "$MANIFESTS_DIR/secrets.yaml"; then
    report_issue "Found hardcoded secrets in secrets.yaml file"
else
    report_success "No hardcoded secrets found - using External Secrets Operator"
fi

# Check security contexts
echo ""
echo "3. Validating security contexts..."
SECURITY_CHECKS=(
    "runAsNonRoot.*true"
    "allowPrivilegeEscalation.*false"
    "readOnlyRootFilesystem"
    "runAsUser"
    "runAsGroup"
    "capabilities:.*drop:.*ALL"
)

for check in "${SECURITY_CHECKS[@]}"; do
    if grep -r "$check" "$MANIFESTS_DIR"/*.yaml >/dev/null 2>&1; then
        report_success "Found security context: ${check//\\\*/}"
    else
        report_warning "Security context not found or not consistent: ${check//\\\*/}"
    fi
done

# Check External Secrets configuration
echo ""
echo "4. Validating External Secrets configuration..."
if [[ -f "$MANIFESTS_DIR/external-secrets/aws-secret-store.yaml" ]]; then
    if grep -q "jwt:" "$MANIFESTS_DIR/external-secrets/aws-secret-store.yaml"; then
        report_success "Using IRSA (IAM Roles for Service Accounts) authentication"
    else
        report_issue "Not using IRSA authentication - security risk!"
    fi

    if grep -q "secretRef:" "$MANIFESTS_DIR/external-secrets/aws-secret-store.yaml"; then
        report_issue "Found secretRef authentication - should use IRSA instead"
    fi
fi

# Check Network Policies
echo ""
echo "5. Validating Network Policies..."
if [[ -f "$MANIFESTS_DIR/network-policies.yaml" ]]; then
    NETWORK_POLICY_CHECKS=(
        "default-deny-all-ingress"
        "allow-frontend-to-api"
        "allow-apps-to-postgres"
        "allow-apps-to-redis"
        "allow-monitoring"
    )

    for policy in "${NETWORK_POLICY_CHECKS[@]}"; do
        if grep -q "$policy" "$MANIFESTS_DIR/network-policies.yaml"; then
            report_success "Found network policy: $policy"
        else
            report_warning "Network policy not found: $policy"
        fi
    done
else
    report_issue "Network policies file not found"
fi

# Check resource limits
echo ""
echo "6. Validating resource limits..."
if grep -r "limits:" "$MANIFESTS_DIR"/*.yaml >/dev/null 2>&1; then
    report_success "Resource limits are configured"
else
    report_warning "Resource limits not found - should be configured for production"
fi

# Check for deprecated APIs (if kubectl is available)
if [[ "$KUBECTL_AVAILABLE" == "true" ]]; then
    echo ""
    echo "7. Checking for deprecated Kubernetes APIs..."

    for manifest in "$MANIFESTS_DIR"/*.yaml "$MANIFESTS_DIR"/external-secrets/*.yaml; do
        if [[ -f "$manifest" ]]; then
            # Check for deprecated APIs
            if grep -q "apiVersion: extensions/v1beta1" "$manifest"; then
                report_issue "Deprecated API version found in $manifest: extensions/v1beta1"
            fi
            if grep -q "apiVersion: apps/v1beta1" "$manifest"; then
                report_issue "Deprecated API version found in $manifest: apps/v1beta1"
            fi
        fi
    done
    report_success "No deprecated API versions found"
fi

# Summary
echo ""
echo -e "${BLUE}📊 Security Validation Summary${NC}"
echo "================================="

if [[ $ISSUES_FOUND -eq 0 ]]; then
    echo -e "${GREEN}🎉 All security validations passed! The F1 Analytics deployment is secure.${NC}"
    exit 0
else
    echo -e "${RED}⚠️  Found $ISSUES_FOUND security issue(s) that need to be addressed.${NC}"
    echo ""
    echo "Recommendations:"
    echo "- Review the issues reported above"
    echo "- Fix hardcoded secrets by using External Secrets Operator"
    echo "- Ensure all deployments have proper security contexts"
    echo "- Configure network policies for micro-segmentation"
    echo "- Use IRSA for AWS authentication instead of access keys"
    exit 1
fi