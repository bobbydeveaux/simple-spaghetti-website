# External Secrets Management

This directory contains the configuration for secure external secret management using the External Secrets Operator (ESO) with AWS Secrets Manager.

## Overview

The External Secrets Operator replaces the previous hardcoded secrets approach with secure external secret management. Secrets are stored in AWS Secrets Manager and automatically synchronized to Kubernetes secrets.

## Security Benefits

- **No hardcoded secrets** in version control
- **Automatic secret rotation** support
- **Audit logging** via AWS CloudTrail
- **Fine-grained access control** via IAM
- **Encryption at rest** in AWS Secrets Manager
- **RBAC integration** with Kubernetes

## Components

### 1. External Secrets Operator (`external-secrets-operator.yaml`)
- Installs the External Secrets Operator via Helm
- Configured with security best practices
- Runs as non-root user (65532)
- Read-only root filesystem
- Resource limits enforced

### 2. AWS Secret Store (`aws-secret-store.yaml`)
- Configures connection to AWS Secrets Manager
- Separate stores for production, staging, and development
- Uses IAM roles instead of hardcoded credentials

### 3. External Secrets (`external-secrets.yaml`)
- Defines which secrets to pull from AWS Secrets Manager
- Automatic refresh every hour
- Maps AWS secret keys to Kubernetes secret keys

### 4. AWS IAM Role (`aws-iam-role.yaml`)
- ServiceAccount with IRSA (IAM Roles for Service Accounts)
- Minimal IAM permissions for secret access
- Reference IAM policies for AWS setup

## AWS Secrets Manager Structure

Secrets should be created in AWS Secrets Manager with the following structure:

```
f1-analytics/postgres
├── username: f1_analytics
├── password: <generated-strong-password>
└── replication_password: <generated-strong-password>

f1-analytics/redis
└── password: <generated-strong-password>

f1-analytics/app
├── jwt_secret: <generated-256-bit-secret>
├── app_secret_key: <generated-256-bit-secret>
└── db_encryption_key: <generated-256-bit-secret>

f1-analytics/external-apis
├── openweather_api_key: <your-api-key>
└── ergast_api_key: <your-api-key>

f1-analytics/airflow
├── db_password: <generated-strong-password>
├── fernet_key: <cryptography-fernet-generated-key>
├── admin_password: <generated-strong-password>
└── admin_username: admin

f1-analytics/monitoring
├── grafana_admin_user: admin
├── grafana_admin_password: <generated-strong-password>
├── prometheus_username: prometheus
├── prometheus_password: <generated-strong-password>
├── slack_webhook_url: <your-slack-webhook>
└── pagerduty_integration_key: <your-pagerduty-key>

f1-analytics/staging
└── basic_auth: <htpasswd-generated-auth-string>
```

## Deployment Instructions

### Prerequisites

1. **AWS EKS Cluster** with OIDC identity provider enabled
2. **AWS Secrets Manager** with secrets created
3. **IAM Role** with appropriate permissions
4. **Helm** installed in the cluster

### Step 1: Create AWS Secrets

```bash
# Create PostgreSQL secrets
aws secretsmanager create-secret \
  --name f1-analytics/postgres \
  --secret-string '{
    "username": "f1_analytics",
    "password": "<generate-secure-password>",
    "replication_password": "<generate-secure-password>"
  }'

# Create Redis secrets
aws secretsmanager create-secret \
  --name f1-analytics/redis \
  --secret-string '{"password": "<generate-secure-password>"}'

# ... repeat for other secrets
```

### Step 2: Create IAM Role

```bash
# Replace ACCOUNT_ID and OIDC_ID with your values
aws iam create-role \
  --role-name ExternalSecretsRole \
  --assume-role-policy-document file://trust-policy.json

aws iam attach-role-policy \
  --role-name ExternalSecretsRole \
  --policy-arn arn:aws:iam::ACCOUNT_ID:policy/ExternalSecretsPolicy
```

### Step 3: Update Configuration

1. Update `aws-iam-role.yaml` with your AWS account ID and IAM role ARN
2. Update `aws-secret-store.yaml` with your AWS region
3. Deploy the external secrets:

```bash
kubectl apply -f external-secrets-operator.yaml
kubectl apply -f aws-iam-role.yaml
kubectl apply -f aws-secret-store.yaml
kubectl apply -f external-secrets.yaml
```

### Step 4: Verify Deployment

```bash
# Check operator status
kubectl get pods -n external-secrets

# Check secret stores
kubectl get secretstore -n f1-analytics

# Check external secrets
kubectl get externalsecret -n f1-analytics

# Verify secrets are created
kubectl get secrets -n f1-analytics
```

## Migration from Hardcoded Secrets

1. **Delete old secrets.yaml**: Remove the hardcoded secrets file
2. **Apply external secrets**: Deploy the ESO configuration
3. **Verify secret sync**: Ensure all secrets are properly synchronized
4. **Update deployments**: If needed, restart deployments to pick up new secrets

## Security Best Practices

- **Rotate secrets regularly** using AWS Secrets Manager rotation
- **Monitor secret access** via AWS CloudTrail
- **Use least privilege IAM policies**
- **Enable AWS Config** for compliance monitoring
- **Set up alerts** for secret access anomalies
- **Regular security audits** of secret access patterns

## Troubleshooting

### Common Issues

1. **Secret not syncing**: Check IAM permissions and secret store configuration
2. **Invalid secret format**: Ensure AWS secret structure matches ExternalSecret spec
3. **Authentication errors**: Verify IRSA configuration and IAM role ARN

### Debug Commands

```bash
# Check operator logs
kubectl logs -n external-secrets deployment/external-secrets

# Check external secret status
kubectl describe externalsecret -n f1-analytics

# Check secret store status
kubectl describe secretstore -n f1-analytics aws-secrets-store
```

## References

- [External Secrets Operator Documentation](https://external-secrets.io/)
- [AWS Secrets Manager Integration](https://external-secrets.io/v0.9.11/provider/aws-secrets-manager/)
- [IAM Roles for Service Accounts](https://docs.aws.amazon.com/eks/latest/userguide/iam-roles-for-service-accounts.html)