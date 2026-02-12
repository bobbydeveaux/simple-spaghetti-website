# Secure Kubernetes Deployment Guide

This guide provides step-by-step instructions for securely deploying the F1 Prediction Analytics Platform to Kubernetes with enterprise-grade security.

## 🔒 Security Overview

The platform has been hardened with the following security measures:

### ✅ Fixed Security Issues

| Issue | Previous State | Current State | Status |
|-------|----------------|---------------|---------|
| Hardcoded Secrets | Base64-encoded in YAML | External Secrets Operator + AWS Secrets Manager | ✅ **FIXED** |
| Example Domains | f1-analytics.example.com | Environment-specific configuration | ✅ **FIXED** |
| Airflow Admin Password | Hardcoded `admin123` | Secure external secret | ✅ **FIXED** |
| PostgreSQL Init Container | Running as root (UID 0) | Non-privileged with fsGroup | ✅ **FIXED** |
| PostgreSQL Authentication | Trust + broad CIDR ranges | SCRAM-SHA-256 + restricted networks | ✅ **FIXED** |
| Redis Protected Mode | Disabled | Enabled | ✅ **FIXED** |
| Image Tags | Using `:latest` | Specific version tags | ✅ **FIXED** |
| SSL/TLS | Basic configuration | Enhanced with proper certificates | ✅ **FIXED** |

## 📋 Prerequisites

### Infrastructure Requirements
- **Kubernetes 1.25+** with OIDC identity provider enabled
- **AWS Account** with Secrets Manager access
- **Domain Name** with DNS control for certificate management
- **kubectl** configured with cluster access
- **Helm 3.0+** for External Secrets Operator

### AWS IAM Setup
- IAM role for External Secrets Operator with SecretsManager permissions
- OIDC identity provider configured in EKS (if using EKS)

## 🚀 Deployment Steps

### Step 1: Prepare AWS Secrets Manager

Create all required secrets in AWS Secrets Manager:

```bash
# PostgreSQL Secrets
aws secretsmanager create-secret \
  --name f1-analytics/postgres \
  --description "PostgreSQL database credentials" \
  --secret-string '{
    "username": "f1_analytics",
    "password": "'$(openssl rand -base64 32)'",
    "replication_password": "'$(openssl rand -base64 32)'"
  }'

# Redis Secrets
aws secretsmanager create-secret \
  --name f1-analytics/redis \
  --description "Redis cache credentials" \
  --secret-string '{
    "password": "'$(openssl rand -base64 32)'"
  }'

# Application Secrets
aws secretsmanager create-secret \
  --name f1-analytics/app \
  --description "Application secrets" \
  --secret-string '{
    "jwt_secret": "'$(openssl rand -base64 64)'",
    "app_secret_key": "'$(openssl rand -base64 64)'",
    "db_encryption_key": "'$(openssl rand -base64 32)'"
  }'

# External API Secrets
aws secretsmanager create-secret \
  --name f1-analytics/external-apis \
  --description "External API credentials" \
  --secret-string '{
    "openweather_api_key": "YOUR_OPENWEATHER_API_KEY",
    "ergast_api_key": ""
  }'

# Airflow Secrets
aws secretsmanager create-secret \
  --name f1-analytics/airflow \
  --description "Airflow orchestration secrets" \
  --secret-string '{
    "db_password": "'$(openssl rand -base64 32)'",
    "fernet_key": "'$(python3 -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())")'",
    "admin_password": "'$(openssl rand -base64 32)'",
    "admin_username": "admin"
  }'

# Monitoring Secrets
aws secretsmanager create-secret \
  --name f1-analytics/monitoring \
  --description "Monitoring stack secrets" \
  --secret-string '{
    "grafana_admin_user": "admin",
    "grafana_admin_password": "'$(openssl rand -base64 32)'",
    "prometheus_username": "prometheus",
    "prometheus_password": "'$(openssl rand -base64 32)'",
    "slack_webhook_url": "YOUR_SLACK_WEBHOOK_URL",
    "pagerduty_integration_key": "YOUR_PAGERDUTY_KEY"
  }'

# Staging Basic Auth
aws secretsmanager create-secret \
  --name f1-analytics/staging \
  --description "Staging environment authentication" \
  --secret-string '{
    "basic_auth": "'$(htpasswd -bn admin $(openssl rand -base64 12))"'"
  }'
```

### Step 2: Configure IAM Role

Create IAM policy for External Secrets access:

```bash
cat > external-secrets-policy.json << EOF
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "secretsmanager:GetSecretValue",
        "secretsmanager:DescribeSecret"
      ],
      "Resource": "arn:aws:secretsmanager:us-west-2:ACCOUNT_ID:secret:f1-analytics/*"
    }
  ]
}
EOF

# Create IAM policy
aws iam create-policy \
  --policy-name ExternalSecretsPolicy \
  --policy-document file://external-secrets-policy.json

# Create IAM role with OIDC trust relationship
# Replace ACCOUNT_ID and OIDC_ID with your values
cat > trust-policy.json << EOF
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Principal": {
        "Federated": "arn:aws:iam::ACCOUNT_ID:oidc-provider/oidc.eks.us-west-2.amazonaws.com/id/OIDC_ID"
      },
      "Action": "sts:AssumeRoleWithWebIdentity",
      "Condition": {
        "StringEquals": {
          "oidc.eks.us-west-2.amazonaws.com/id/OIDC_ID:sub": "system:serviceaccount:external-secrets:external-secrets-sa",
          "oidc.eks.us-west-2.amazonaws.com/id/OIDC_ID:aud": "sts.amazonaws.com"
        }
      }
    }
  ]
}
EOF

aws iam create-role \
  --role-name ExternalSecretsRole \
  --assume-role-policy-document file://trust-policy.json

aws iam attach-role-policy \
  --role-name ExternalSecretsRole \
  --policy-arn arn:aws:iam::ACCOUNT_ID:policy/ExternalSecretsPolicy
```

### Step 3: Configure Domain Settings

Update domain configuration for your environment:

```bash
# Edit production domain configuration
vi infrastructure/kubernetes/environments/production/domains.yaml
```

Replace example values:
```yaml
data:
  PRIMARY_DOMAIN: "f1-analytics.com"           # Your actual domain
  FRONTEND_DOMAIN: "f1-analytics.com"
  API_DOMAIN: "api.f1-analytics.com"
  CONTACT_EMAIL: "admin@f1-analytics.com"      # Your actual email
```

### Step 4: Update IAM Role ARN

Update the External Secrets ServiceAccount with your IAM role:

```bash
# Edit the IAM role configuration
vi infrastructure/kubernetes/external-secrets/aws-iam-role.yaml
```

Replace the placeholder:
```yaml
annotations:
  eks.amazonaws.com/role-arn: arn:aws:iam::YOUR_ACCOUNT_ID:role/ExternalSecretsRole
```

### Step 5: Deploy External Secrets Operator

```bash
# Deploy External Secrets Operator
kubectl apply -f infrastructure/kubernetes/external-secrets/external-secrets-operator.yaml

# Wait for operator to be ready
kubectl wait --for=condition=available deployment/external-secrets -n external-secrets --timeout=300s

# Deploy SecretStores and ExternalSecrets
kubectl apply -f infrastructure/kubernetes/external-secrets/aws-iam-role.yaml
kubectl apply -f infrastructure/kubernetes/external-secrets/aws-secret-store.yaml
kubectl apply -f infrastructure/kubernetes/external-secrets/external-secrets.yaml
```

### Step 6: Verify Secret Synchronization

```bash
# Check External Secrets status
kubectl get externalsecret -n f1-analytics

# Verify secrets are created
kubectl get secrets -n f1-analytics

# Check for any errors
kubectl describe externalsecret postgres-secret -n f1-analytics
```

### Step 7: Deploy Application Infrastructure

```bash
# Deploy namespaces
kubectl apply -f infrastructure/kubernetes/namespaces.yaml

# Deploy domain configuration
kubectl apply -f infrastructure/kubernetes/environments/production/domains.yaml

# Deploy application configuration
kubectl apply -f infrastructure/kubernetes/configmaps.yaml

# Deploy PostgreSQL with enhanced security
kubectl apply -f infrastructure/kubernetes/postgres-config.yaml
kubectl apply -f infrastructure/kubernetes/postgres-statefulset.yaml

# Deploy Redis with security hardening
kubectl apply -f infrastructure/kubernetes/redis-config.yaml
kubectl apply -f infrastructure/kubernetes/redis-deployment.yaml

# Deploy application services
kubectl apply -f infrastructure/kubernetes/api-gateway-deployment.yaml
kubectl apply -f infrastructure/kubernetes/prediction-service-deployment.yaml
kubectl apply -f infrastructure/kubernetes/frontend-deployment.yaml
kubectl apply -f infrastructure/kubernetes/airflow-deployment.yaml

# Deploy ingress with production domains
kubectl apply -f infrastructure/kubernetes/environments/production/ingress.yaml

# Deploy monitoring stack
kubectl apply -f infrastructure/kubernetes/monitoring-deployment.yaml
```

### Step 8: Verify Deployment

```bash
# Check pod status
kubectl get pods -n f1-analytics

# Check services
kubectl get svc -n f1-analytics

# Check ingress
kubectl get ingress -n f1-analytics

# Check certificates (if using cert-manager)
kubectl get certificates -n f1-analytics
```

## 🔍 Security Verification

### Verify Secret Management

```bash
# Verify no hardcoded secrets in deployment
grep -r "password.*=" infrastructure/kubernetes/ || echo "✅ No hardcoded passwords found"

# Verify External Secrets are syncing
kubectl get externalsecret -n f1-analytics -o wide

# Check secret rotation status
kubectl describe externalsecret -n f1-analytics
```

### Verify Security Contexts

```bash
# Verify no containers run as root
kubectl get pods -n f1-analytics -o jsonpath='{range .items[*]}{.metadata.name}{"\t"}{.spec.containers[*].securityContext.runAsUser}{"\n"}{end}'

# Verify PostgreSQL authentication
kubectl exec -it postgres-0 -n f1-analytics -- psql -h localhost -U f1_analytics -c "\conninfo"
```

### Verify Network Security

```bash
# Check PostgreSQL connections are encrypted
kubectl logs postgres-0 -n f1-analytics | grep -i ssl

# Verify Redis protected mode
kubectl exec -it redis-master-0 -n f1-analytics -- redis-cli CONFIG GET protected-mode
```

## 🚨 Troubleshooting

### External Secrets Issues

```bash
# Check operator logs
kubectl logs -n external-secrets deployment/external-secrets

# Check specific ExternalSecret
kubectl describe externalsecret postgres-secret -n f1-analytics

# Verify IAM permissions
aws sts assume-role --role-arn arn:aws:iam::ACCOUNT_ID:role/ExternalSecretsRole --role-session-name test
```

### PostgreSQL Connection Issues

```bash
# Check PostgreSQL logs
kubectl logs postgres-0 -n f1-analytics

# Test connection
kubectl exec -it postgres-0 -n f1-analytics -- psql -h localhost -U f1_analytics -c "SELECT version();"
```

### Certificate Issues

```bash
# Check cert-manager logs
kubectl logs -n cert-manager deployment/cert-manager

# Check certificate status
kubectl describe certificate f1-analytics-tls -n f1-analytics
```

## 📖 Post-Deployment

### Initial Access

1. **Get Grafana Admin Password**:
   ```bash
   kubectl get secret monitoring-secrets -n f1-analytics -o jsonpath='{.data.grafana-admin-password}' | base64 -d
   ```

2. **Get Airflow Admin Password**:
   ```bash
   kubectl get secret airflow-secrets -n f1-analytics -o jsonpath='{.data.admin-password}' | base64 -d
   ```

3. **Access Application**:
   - Frontend: https://your-domain.com
   - API: https://api.your-domain.com
   - Airflow: https://airflow.your-domain.com

### Monitoring and Maintenance

- **Monitor secret rotation** via AWS CloudWatch/CloudTrail
- **Review security logs** in Prometheus/Grafana
- **Update image tags** regularly in production configuration
- **Rotate secrets** according to your security policy

## 🔐 Security Compliance

This deployment meets the following security standards:

- ✅ **Zero Trust Secret Management**: No secrets in version control
- ✅ **Principle of Least Privilege**: Minimal IAM and RBAC permissions
- ✅ **Defense in Depth**: Multiple layers of security controls
- ✅ **Secure by Default**: All services configured securely
- ✅ **Audit Logging**: Complete audit trail via AWS CloudTrail
- ✅ **Encryption**: TLS/SSL for all communications
- ✅ **Network Segmentation**: Restricted network policies
- ✅ **Regular Updates**: Versioned image tags for reproducibility

For additional security requirements, consult your organization's security team and compliance requirements.

## 📞 Support

For deployment issues:
1. Check the troubleshooting section above
2. Review External Secrets Operator documentation
3. Consult AWS Secrets Manager documentation
4. Review Kubernetes security best practices