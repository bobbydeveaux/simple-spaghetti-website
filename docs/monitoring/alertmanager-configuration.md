# F1 Prediction Analytics - Alertmanager Configuration

This document provides comprehensive information about the Alertmanager rules and configuration for the F1 Prediction Analytics monitoring system.

## Overview

The monitoring system consists of:
- **Prometheus** - Metrics collection and alerting engine
- **Alertmanager** - Alert routing, grouping, and notification handling
- **Grafana** - Visualization and dashboards
- **Custom Exporters** - PostgreSQL, Redis, Node, and Blackbox exporters

## Architecture

```
┌─────────────┐    ┌─────────────┐    ┌─────────────┐
│  Prometheus │    │ Alertmanager│    │   Grafana   │
│             │───▶│             │───▶│             │
│ • Rules     │    │ • Routing   │    │ • Dashboards│
│ • Scraping  │    │ • Grouping  │    │ • Alerts UI │
│ • Alerting  │    │ • Silencing │    │             │
└─────────────┘    └─────────────┘    └─────────────┘
       │                   │
       ▼                   ▼
┌─────────────┐    ┌─────────────┐
│  Exporters  │    │ Notification│
│             │    │  Channels   │
│ • PostgreSQL│    │ • Slack     │
│ • Redis     │    │ • Email     │
│ • Node      │    │ • PagerDuty │
│ • Blackbox  │    │ • Webhooks  │
└─────────────┘    └─────────────┘
```

## Alert Rules Categories

### 1. System Health (`system-health`)
- **HighCPUUsage** - CPU usage > 80% for 5 minutes
- **HighMemoryUsage** - Available memory < 15% for 5 minutes
- **DiskSpaceCritical** - Available disk space < 10%

### 2. API Health (`api-health`)
- **APIHighErrorRate** - 5XX error rate > 5% for 2 minutes
- **APIHighLatency** - 95th percentile latency > 2 seconds
- **PredictionServiceDown** - Prediction service unavailable

### 3. F1 Prediction Analytics (`f1-prediction-analytics`)
- **MLInferenceHighLatency** - ML inference > 5 seconds (95th percentile)
- **PredictionAccuracyDegraded** - Accuracy < 65% over 24 hours
- **LowPredictionVolume** - < 5 predictions per hour
- **HighBrierScore** - Brier score > 0.3 (poor model performance)
- **ModelTrainingFailed** - Model training failures detected
- **FeatureEngineeringHighLatency** - Feature processing > 5 minutes

### 4. Data Pipeline (`data-pipeline`)
- **F1DataStaleness** - Data not updated for 24+ hours
- **F1DataStalenessCritical** - Data not updated for 2+ hours (race weekend)
- **ErgastAPIUnavailable** - External F1 API health check failed
- **DataIngestionFailures** - Multiple ingestion failures

### 5. Database & Storage (`database-storage`)
- **DatabaseConnectionHigh** - DB connections > 80% capacity
- **DatabaseSlowQueries** - Query efficiency ratio < 80%
- **RedisHighMemoryUsage** - Redis memory > 90%
- **RedisCacheHitRateLow** - Cache hit rate < 70%

### 6. Airflow & Scheduling (`airflow-scheduling`)
- **AirflowDAGFailing** - DAG execution failures
- **AirflowTaskBacklog** - > 10 tasks queued for 30+ minutes
- **AirflowSchedulerDown** - Scheduler unreachable for 2+ minutes

### 7. Security & Anomalies (`security-anomalies`)
- **UnusualAPIAccessPattern** - Request rate > 100 req/sec
- **HighClientErrorRate** - 4XX error rate > 30%
- **HighFailedAuthAttempts** - > 5 failed auth attempts per second

## Notification Routing

### Route Configuration

```yaml
route:
  group_by: ['cluster', 'service', 'alertname']
  group_wait: 10s
  group_interval: 5m
  repeat_interval: 12h
  receiver: 'default-receiver'
```

### Routing Tree

```
Default Receiver (webhook)
├── Critical Alerts
│   ├── ML Critical (prediction-service)
│   ├── Data Critical (data-ingestion)
│   └── General Critical (Slack + Email + PagerDuty)
├── Warning Alerts
│   ├── Infrastructure Warnings (email)
│   ├── API Warnings (Slack)
│   └── General Warnings (Slack)
├── Service-Specific
│   ├── Database Alerts (Slack)
│   └── Pipeline Alerts (Slack)
└── Security Alerts (immediate notification)
```

## Notification Channels

### Slack Integration
- **Critical Alerts**: `#f1-analytics-critical`
- **ML Service**: `#f1-analytics-ml`
- **Data Pipeline**: `#f1-analytics-data`
- **Warnings**: `#f1-analytics-warnings`
- **API Issues**: `#f1-analytics-api`
- **Database**: `#f1-analytics-database`
- **Security**: `#f1-analytics-security`

### Email Notifications
- **Critical**: `oncall@f1-analytics.com`
- **Infrastructure**: `infrastructure@f1-analytics.com`
- **Security**: `security@f1-analytics.com`

### PagerDuty
- Critical alerts trigger PagerDuty incidents
- Integration key stored in Kubernetes secrets

## Configuration Files

### Core Files
- `alertmanager-rules.yaml` - Alert rule definitions
- `prometheus.yaml` - Prometheus configuration with rules references
- `grafana.yaml` - Updated Alertmanager config with enhanced routing
- `alertmanager-secrets.yaml` - Secret templates and configurations

### Secrets Management

```yaml
apiVersion: v1
kind: Secret
metadata:
  name: alertmanager-secrets
type: Opaque
stringData:
  smtp-password: "your-smtp-app-password"
  slack-webhook-url: "https://hooks.slack.com/services/..."
  pagerduty-routing-key: "your-pagerduty-key"
  webhook-token: "your-webhook-token"
```

## Deployment Instructions

### Prerequisites
- Kubernetes cluster with `f1-analytics` namespace
- `kubectl` access to the cluster
- Prometheus and Alertmanager already deployed

### Step 1: Deploy Alert Rules
```bash
kubectl apply -f infrastructure/monitoring/alertmanager-rules.yaml
```

### Step 2: Update Secrets (IMPORTANT)
```bash
# Edit the secrets file with real values
kubectl apply -f infrastructure/monitoring/alertmanager-secrets.yaml
```

### Step 3: Update Prometheus Configuration
```bash
kubectl apply -f infrastructure/monitoring/prometheus.yaml
```

### Step 4: Update Alertmanager Configuration
```bash
kubectl apply -f infrastructure/monitoring/grafana.yaml
```

### Step 5: Restart Services
```bash
kubectl rollout restart deployment/prometheus -n f1-analytics
kubectl rollout restart deployment/alertmanager -n f1-analytics
```

### Step 6: Validation
```bash
# Run validation script
./infrastructure/monitoring/validate-alerts.sh

# Check pod status
kubectl get pods -n f1-analytics

# Check logs
kubectl logs -f deployment/prometheus -n f1-analytics
kubectl logs -f deployment/alertmanager -n f1-analytics
```

## Alert Severity Levels

### Critical (Immediate Response Required)
- Service completely down
- Data loss risk
- Prediction accuracy severely degraded
- Security incidents
- External API failures during race weekend

**Response Time**: < 5 minutes
**Notification**: Slack + Email + PagerDuty

### Warning (Response Within Business Hours)
- Performance degradation
- Resource utilization high
- Non-critical component issues
- Data staleness (non-race weekend)

**Response Time**: < 2 hours
**Notification**: Slack + Email

## Metrics Reference

### Custom F1 Metrics
```promql
# Prediction accuracy
f1_prediction_accuracy

# Brier score (lower is better)
f1_brier_score

# Prediction volume
f1_predictions_total

# Data freshness
f1_last_data_update_timestamp

# Model training
f1_model_training_failures_total

# Feature engineering duration
f1_feature_engineering_duration_seconds

# Authentication failures
f1_auth_failures_total
```

### Standard Infrastructure Metrics
```promql
# CPU usage
node_cpu_seconds_total

# Memory usage
node_memory_MemAvailable_bytes
node_memory_MemTotal_bytes

# HTTP metrics
http_requests_total
http_request_duration_seconds_bucket

# Database metrics
pg_stat_database_numbackends
pg_settings_max_connections

# Redis metrics
redis_memory_used_bytes
redis_memory_max_bytes
```

## Troubleshooting

### Common Issues

#### 1. Alerts Not Firing
```bash
# Check Prometheus targets
kubectl port-forward svc/prometheus-service 9090:9090 -n f1-analytics
# Visit http://localhost:9090/targets

# Check rules evaluation
# Visit http://localhost:9090/alerts
```

#### 2. Notifications Not Sent
```bash
# Check Alertmanager configuration
kubectl port-forward svc/alertmanager-service 9093:9093 -n f1-analytics
# Visit http://localhost:9093

# Check secret values
kubectl get secret alertmanager-secrets -n f1-analytics -o yaml
```

#### 3. Rule Syntax Errors
```bash
# Validate rules
docker run --rm -v $(pwd):/workspace prom/prometheus:v2.45.0 \
  promtool check rules /workspace/infrastructure/monitoring/alertmanager-rules.yaml
```

### Log Locations
```bash
# Prometheus logs
kubectl logs deployment/prometheus -n f1-analytics

# Alertmanager logs
kubectl logs deployment/alertmanager -n f1-analytics

# Check ConfigMap contents
kubectl describe configmap alertmanager-rules -n f1-analytics
```

## Alert Tuning Guidelines

### Threshold Recommendations

| Metric | Warning | Critical | Rationale |
|--------|---------|----------|-----------|
| CPU Usage | 80% | 90% | Allow for burst capacity |
| Memory Usage | 85% | 95% | Prevent OOM conditions |
| API Latency | 2s (95th) | 5s (95th) | User experience impact |
| Prediction Accuracy | 65% | 50% | Model effectiveness |
| Data Staleness | 24h | 2h (race) | Business requirements |

### Frequency Guidelines
- **Critical alerts**: Check every 1-2 minutes
- **Performance alerts**: Check every 5 minutes
- **Resource alerts**: Check every 5-10 minutes
- **Data freshness**: Check every 10-30 minutes

## Runbook Links

All alerts include runbook URLs pointing to:
`https://docs.f1-analytics.com/runbooks/{alert-type}`

### Runbook Structure
- **Problem description**
- **Impact assessment**
- **Immediate actions**
- **Investigation steps**
- **Resolution procedures**
- **Prevention measures**

## Security Considerations

### Sensitive Information
- All webhook URLs, API keys, and passwords are stored in Kubernetes secrets
- SMTP credentials use app passwords, not account passwords
- Webhook tokens should be rotated regularly

### Access Control
- Alertmanager UI should be behind authentication
- ConfigMap changes should require code review
- Secret access should be limited to monitoring namespace

## Performance Impact

### Resource Usage
- **Prometheus**: ~2-4 GiB memory, 0.5-2 CPU cores
- **Alertmanager**: ~128-256 MiB memory, 50-200 milliCPU
- **Rule evaluation**: ~1-5ms per rule evaluation

### Storage Requirements
- **Alert history**: ~1-10 MiB per day
- **Configuration**: ~100 KiB
- **Templates**: ~10 KiB

## Future Enhancements

### Planned Improvements
1. **Dynamic thresholds** based on historical data
2. **ML-based anomaly detection** for unusual patterns
3. **Correlation analysis** between related alerts
4. **Auto-remediation** for common issues
5. **Enhanced dashboards** with alert context

### Integration Roadmap
- Microsoft Teams notifications
- JIRA ticket creation for critical alerts
- Splunk log correlation
- Custom mobile app notifications