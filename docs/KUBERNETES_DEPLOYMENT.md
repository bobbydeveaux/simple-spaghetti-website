# F1 Analytics Kubernetes Deployment Guide

**Created:** 2026-02-12
**Status:** Production Ready
**Issue:** #142 - F1 Prediction Analytics Infrastructure Implementation

## Overview

This guide provides comprehensive instructions for deploying the F1 Analytics platform to Kubernetes. The implementation includes all microservices, databases, caching, monitoring, and observability components required for production operation.

## Architecture Summary

The F1 Analytics platform is deployed as a cloud-native microservices architecture on Kubernetes with the following components:

### Core Services
- **API Gateway**: FastAPI service handling authentication, rate limiting, and request routing
- **Prediction Service**: ML inference engine with trained models for race predictions
- **Frontend**: React 18 SPA with nginx serving static assets
- **PostgreSQL**: Primary database with read replicas for analytics workloads
- **Redis**: Multi-instance cache cluster with sentinel for high availability
- **Apache Airflow**: ML pipeline orchestration for data ingestion and model training

### Infrastructure Services
- **Ingress Controller**: Nginx ingress with TLS termination and Let's Encrypt certificates
- **Monitoring**: Prometheus, Grafana, and AlertManager stack
- **Exporters**: PostgreSQL, Redis, Node, and Blackbox exporters for metrics collection

## Prerequisites

### Required Software
- Kubernetes 1.25+ cluster with at least 3 nodes
- kubectl configured for cluster access
- cert-manager installed for TLS certificate management
- nginx-ingress-controller deployed
- StorageClass `fast-ssd` available for persistent volumes

### Required Resources
- **Minimum**: 8 vCPU, 32GB RAM, 500GB storage
- **Recommended**: 16 vCPU, 64GB RAM, 1TB SSD storage
- **Networking**: Load balancer service support for ingress

### External Dependencies
- Domain name with DNS control (for TLS certificates)
- OpenWeatherMap API key
- AWS S3 access for ML model storage (or compatible object storage)

## Installation Steps

### Step 1: Create Namespaces

```bash
kubectl apply -f infrastructure/kubernetes/namespace.yaml
```

This creates three namespaces:
- `f1-analytics` (production)
- `f1-analytics-staging` (staging)
- `f1-analytics-development` (development)

### Step 2: Configure Secrets

⚠️ **Important**: Update all secret values before deployment!

1. **Generate secure passwords and keys**:
```bash
# PostgreSQL passwords
export POSTGRES_PASSWORD=$(openssl rand -base64 32)
export POSTGRES_REPLICATION_PASSWORD=$(openssl rand -base64 32)

# Redis password
export REDIS_PASSWORD=$(openssl rand -base64 32)

# JWT secret (must be consistent across API services)
export JWT_SECRET=$(openssl rand -base64 64)

# Airflow fernet key
python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
```

2. **Update secrets file**:
Edit `infrastructure/kubernetes/secrets.yaml` and replace all placeholder values:
- Base64 encode all sensitive values: `echo -n "your-password" | base64`
- Add your OpenWeatherMap API key
- Configure AWS credentials for S3 model storage
- Set proper Slack webhook URLs for alerting

3. **Apply secrets**:
```bash
kubectl apply -f infrastructure/kubernetes/secrets.yaml
```

### Step 3: Apply Configuration Maps

```bash
kubectl apply -f infrastructure/kubernetes/configmaps.yaml
kubectl apply -f infrastructure/kubernetes/postgres-config.yaml
kubectl apply -f infrastructure/kubernetes/redis-config.yaml
```

### Step 4: Deploy Database Layer

```bash
# Deploy PostgreSQL StatefulSet with clustering
kubectl apply -f infrastructure/kubernetes/postgres-statefulset.yaml

# Wait for PostgreSQL to be ready
kubectl wait --for=condition=ready pod -l app=postgres --timeout=300s -n f1-analytics

# Deploy Redis cluster
kubectl apply -f infrastructure/kubernetes/redis-deployment.yaml

# Wait for Redis to be ready
kubectl wait --for=condition=ready pod -l app=redis --timeout=180s -n f1-analytics
```

### Step 5: Deploy Application Services

```bash
# Deploy API Gateway
kubectl apply -f infrastructure/kubernetes/api-gateway-deployment.yaml

# Deploy ML Prediction Service
kubectl apply -f infrastructure/kubernetes/prediction-service-deployment.yaml

# Deploy Frontend
kubectl apply -f infrastructure/kubernetes/frontend-deployment.yaml

# Deploy Airflow orchestration
kubectl apply -f infrastructure/kubernetes/airflow-deployment.yaml
```

### Step 6: Configure Ingress and TLS

1. **Update domain names** in `infrastructure/kubernetes/ingress.yaml`:
   - Replace `f1-analytics.example.com` with your actual domain
   - Update email in ClusterIssuer configurations

2. **Deploy ingress**:
```bash
kubectl apply -f infrastructure/kubernetes/ingress.yaml
```

3. **Verify TLS certificates**:
```bash
kubectl get certificates -n f1-analytics
kubectl describe certificate f1-analytics-tls -n f1-analytics
```

### Step 7: Deploy Monitoring Stack

```bash
# Deploy Prometheus
kubectl apply -f infrastructure/monitoring/prometheus.yaml

# Deploy Grafana and AlertManager
kubectl apply -f infrastructure/monitoring/grafana.yaml

# Deploy metrics exporters
kubectl apply -f infrastructure/monitoring/exporters.yaml
```

### Step 8: Initialize Database

```bash
# Get API Gateway pod name
API_POD=$(kubectl get pods -n f1-analytics -l app=api-gateway -o jsonpath='{.items[0].metadata.name}')

# Run database migrations
kubectl exec -n f1-analytics $API_POD -- python -m alembic upgrade head

# Verify database schema
kubectl exec -n f1-analytics $API_POD -- python -c "
from sqlalchemy import create_engine, text
import os
engine = create_engine(os.environ['DATABASE_URL'])
with engine.connect() as conn:
    result = conn.execute(text('SELECT tablename FROM pg_tables WHERE schemaname = \'public\''))
    print('Tables:', [row[0] for row in result])
"
```

## Verification

### Health Checks

1. **Check pod status**:
```bash
kubectl get pods -n f1-analytics
# All pods should be Running or Completed
```

2. **Check service endpoints**:
```bash
kubectl get svc -n f1-analytics
# Verify ClusterIP services have endpoints
```

3. **Test API Gateway**:
```bash
# Port forward to test locally
kubectl port-forward svc/api-gateway-service 8080:8000 -n f1-analytics

# Test health endpoint
curl http://localhost:8080/health
# Expected: {"status": "healthy"}
```

4. **Test Prediction Service**:
```bash
kubectl port-forward svc/prediction-service 8081:8001 -n f1-analytics
curl http://localhost:8081/health
```

5. **Access Grafana dashboard**:
```bash
# Get Grafana admin password
kubectl get secret monitoring-secrets -n f1-analytics -o jsonpath='{.data.grafana-admin-password}' | base64 -d

# Port forward to access locally
kubectl port-forward svc/grafana-service 3000:3000 -n f1-analytics
# Visit http://localhost:3000
```

### External Access

After DNS propagation (5-60 minutes):

- **Main Application**: https://f1-analytics.example.com
- **API Documentation**: https://api.f1-analytics.example.com/docs
- **Airflow UI**: https://airflow.f1-analytics.example.com
- **Grafana Dashboard**: https://grafana.f1-analytics.example.com

## Scaling Configuration

### Horizontal Pod Autoscaler (HPA)

The deployment includes HPA configurations for auto-scaling based on resource utilization:

- **API Gateway**: 3-10 replicas (CPU: 70%, Memory: 80%)
- **Prediction Service**: 2-6 replicas (CPU: 75%, Memory: 85%)
- **Frontend**: 3-10 replicas (CPU: 70%, Memory: 80%)

### Manual Scaling

```bash
# Scale API Gateway
kubectl scale deployment api-gateway --replicas=5 -n f1-analytics

# Scale Prediction Service for high load
kubectl scale deployment prediction-service --replicas=4 -n f1-analytics
```

### Database Scaling

**PostgreSQL Read Replicas**:
```bash
# Scale PostgreSQL StatefulSet (adds read replicas)
kubectl scale statefulset postgres --replicas=5 -n f1-analytics
```

**Redis Cluster Scaling**:
```bash
# Scale Redis replicas
kubectl scale deployment redis-replica --replicas=3 -n f1-analytics
```

## Monitoring and Observability

### Key Metrics

**Application Metrics** (available in Grafana):
- API request rate and latency (p95, p99)
- Prediction accuracy and inference time
- ML model performance by type
- Database query performance
- Cache hit rates

**Infrastructure Metrics**:
- CPU and memory utilization
- Network I/O and disk usage
- Kubernetes pod and node status
- Storage utilization and performance

**Business Metrics**:
- Prediction accuracy trends
- User engagement metrics
- Data freshness and quality scores
- Revenue and usage analytics

### Alerting Rules

Critical alerts are configured in Prometheus:
- Service downtime (>1 minute)
- High error rates (>5%)
- High latency (p95 >2 seconds)
- Database connection exhaustion (>80%)
- Data staleness (>24 hours)

Alerts route to:
- **Critical**: Slack #f1-analytics-alerts + PagerDuty
- **Warning**: Email to admin@f1-analytics.example.com

### Log Aggregation

Logs are collected via:
- **Container logs**: kubectl logs and Fluentd
- **Application logs**: Structured JSON logging
- **Access logs**: Nginx ingress controller
- **Database logs**: PostgreSQL query logs

## Backup and Disaster Recovery

### Automated Backups

**Database Backups**:
- **Schedule**: Daily at 2 AM UTC
- **Retention**: 30 days
- **Location**: S3 bucket `f1-analytics-backups-prod`
- **Verification**: Automated backup validation

**Model Artifacts**:
- **Schedule**: Weekly on Sunday at 4 AM UTC
- **Retention**: 90 days
- **Location**: S3 bucket `f1-analytics-models-prod`

### Recovery Procedures

**Database Recovery**:
```bash
# List available backups
aws s3 ls s3://f1-analytics-backups-prod/database-backups/

# Restore from backup (example)
kubectl exec -n f1-analytics postgres-0 -- pg_restore \
  --host=localhost --username=f1_analytics --dbname=f1_analytics \
  /path/to/backup.sql
```

**Application Recovery**:
- Kubernetes deployments automatically restart failed pods
- HPA ensures adequate replicas during load spikes
- Circuit breakers prevent cascade failures
- Graceful degradation serves cached predictions

## Security Configuration

### Network Security

**Network Policies**: Restrict inter-pod communication
```bash
kubectl apply -f infrastructure/kubernetes/network-policies.yaml
```

**TLS Encryption**:
- All external traffic encrypted with Let's Encrypt certificates
- Internal service communication via Kubernetes service mesh
- Database connections use TLS

### Pod Security

**Security Contexts**:
- Non-root containers with read-only root filesystems
- Dropped Linux capabilities (drop ALL, add specific only)
- seccomp and AppArmor profiles for additional hardening

**Image Security**:
- Container images scanned for vulnerabilities
- Private registry with image signing
- Minimal base images (Alpine Linux)

### Secrets Management

**Kubernetes Secrets**:
- All sensitive data stored in Kubernetes secrets
- Secrets encrypted at rest in etcd
- RBAC controls secret access per namespace

**External Secrets** (recommended for production):
```bash
# Install external-secrets-operator for AWS Secrets Manager integration
helm install external-secrets external-secrets/external-secrets -n external-secrets-system
```

## Troubleshooting

### Common Issues

**Pod Stuck in Pending**:
```bash
# Check resource constraints
kubectl describe pod <pod-name> -n f1-analytics
kubectl top nodes
kubectl get pv,pvc -n f1-analytics
```

**Database Connection Errors**:
```bash
# Check PostgreSQL pods
kubectl logs postgres-0 -n f1-analytics
kubectl exec -n f1-analytics postgres-0 -- pg_isready

# Check connection from app pods
kubectl exec -n f1-analytics <api-gateway-pod> -- nc -zv postgres-service 5432
```

**High Memory Usage**:
```bash
# Check memory consumption
kubectl top pods -n f1-analytics --sort-by=memory
kubectl describe pod <pod-name> -n f1-analytics

# Scale down resource-intensive services temporarily
kubectl scale deployment prediction-service --replicas=1 -n f1-analytics
```

**TLS Certificate Issues**:
```bash
# Check cert-manager status
kubectl get certificates -n f1-analytics
kubectl describe certificaterequest <cert-request> -n f1-analytics
kubectl logs -n cert-manager deployment/cert-manager
```

### Debug Commands

**Get cluster information**:
```bash
kubectl cluster-info
kubectl get nodes -o wide
kubectl get ns
```

**Check application logs**:
```bash
# API Gateway logs
kubectl logs -l app=api-gateway -n f1-analytics --tail=100 -f

# Prediction service logs
kubectl logs -l app=prediction-service -n f1-analytics --tail=100 -f

# Database logs
kubectl logs postgres-0 -n f1-analytics --tail=100 -f
```

**Resource utilization**:
```bash
kubectl top nodes
kubectl top pods -n f1-analytics
kubectl get hpa -n f1-analytics
```

### Performance Tuning

**Database Optimization**:
- Tune PostgreSQL configuration for analytics workloads
- Monitor slow queries and add indexes
- Configure connection pooling (pgbouncer)
- Use read replicas for ML training queries

**Cache Optimization**:
- Monitor Redis memory usage and eviction rates
- Tune TTL values based on data access patterns
- Configure Redis clustering for high availability
- Use Redis pipelining for batch operations

**ML Service Optimization**:
- Profile model inference performance
- Use model quantization to reduce memory usage
- Implement model caching and batching
- Consider GPU acceleration for training workloads

## Deployment Environments

### Development Environment

```bash
# Switch to development namespace
kubectl config set-context --current --namespace=f1-analytics-development

# Deploy with development configs
kubectl apply -f infrastructure/kubernetes/ -n f1-analytics-development
kubectl apply -f configs/development/ -n f1-analytics-development
```

### Staging Environment

```bash
# Deploy to staging namespace with basic auth
kubectl apply -f infrastructure/kubernetes/ -n f1-analytics-staging

# Create basic auth secret for staging
htpasswd -c auth admin
kubectl create secret generic staging-basic-auth --from-file=auth -n f1-analytics-staging
```

### Production Environment

Use the main deployment instructions above with production-grade configurations:
- Multi-zone deployments for high availability
- Resource requests and limits properly configured
- Persistent volume snapshots enabled
- Monitoring and alerting fully configured
- Backup and disaster recovery tested

## Support and Maintenance

### Regular Maintenance Tasks

**Weekly**:
- Review application metrics and performance trends
- Check backup integrity and retention policies
- Update security patches for base images
- Monitor resource usage and scaling patterns

**Monthly**:
- Update Kubernetes cluster version (patch releases)
- Review and rotate secrets and credentials
- Audit access controls and RBAC policies
- Performance testing and capacity planning

**Quarterly**:
- Major version upgrades (Kubernetes, applications)
- Disaster recovery testing and validation
- Security audit and penetration testing
- Business continuity plan review

### Contact Information

- **DevOps Team**: devops@f1-analytics.example.com
- **On-call Engineer**: +1-555-ON-CALL
- **Documentation**: https://docs.f1-analytics.example.com
- **Issue Tracking**: GitHub Issues #142

---

*This document is maintained by the DevOps team and updated with each release. Last updated: 2026-02-12*