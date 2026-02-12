# F1 Prediction Analytics Platform

A comprehensive Formula One race prediction system built with modern microservices architecture and machine learning. This platform aggregates F1 data from multiple sources, applies statistical models, and provides real-time race winner predictions through an interactive web dashboard.

## 🏎️ Features

### Core Functionality
- **Real-time Predictions**: ML-powered race winner probability calculations
- **Interactive Dashboard**: React-based web interface with live data visualizations
- **Historical Analysis**: Track prediction accuracy and model performance over time
- **Data Export**: CSV/JSON export functionality for analysis
- **Multi-Model Ensemble**: Random Forest, XGBoost, and ELO rating systems

### Technical Capabilities
- **Cloud-Native Architecture**: Kubernetes-ready microservices deployment
- **High Availability**: Redis clustering, PostgreSQL replication, auto-scaling
- **Real-time Analytics**: Live prediction updates and performance monitoring
- **ML Pipeline**: Apache Airflow orchestration for automated model training
- **Comprehensive Monitoring**: Prometheus, Grafana, and custom metrics

## 🏗️ Architecture

### Microservices Components
- **API Gateway**: FastAPI service with authentication and rate limiting
- **Prediction Service**: ML inference engine with model ensemble capabilities
- **Data Ingestion**: Automated ETL pipeline for F1 and weather data
- **Web Dashboard**: React 18 SPA with real-time updates
- **ML Training**: Scheduled model training and feature engineering

### Infrastructure
- **Database**: PostgreSQL with read replicas for analytics workloads
- **Cache**: Redis cluster with sentinel for high availability
- **Orchestration**: Apache Airflow for ML pipeline automation
- **Monitoring**: Full observability stack with custom dashboards
- **Security**: TLS termination, JWT authentication, network policies

## 🚀 Quick Start

### Prerequisites
- Kubernetes 1.25+ cluster
- kubectl configured
- cert-manager installed
- nginx-ingress-controller deployed

### Secure Production Deployment

**⚠️ Important:** This platform now uses secure external secret management. Before deployment:

1. **Configure AWS Secrets Manager** (see [External Secrets Setup](infrastructure/kubernetes/external-secrets/README.md))
2. **Set up environment-specific domains** (see [Environment Configuration](infrastructure/kubernetes/environments/))
3. **Deploy with proper security configurations**

```bash
# Clone repository
git clone <repository-url>
cd simple-spaghetti-website

# 1. Configure secrets in AWS Secrets Manager
# See infrastructure/kubernetes/external-secrets/README.md

# 2. Update domain configuration
# Edit infrastructure/kubernetes/environments/production/domains.yaml

# 3. Deploy External Secrets Operator first
kubectl apply -f infrastructure/kubernetes/external-secrets/

# 4. Deploy application with environment-specific config
kubectl apply -f infrastructure/kubernetes/environments/production/
kubectl apply -f infrastructure/kubernetes/
```

### Local Development

```bash
# Deploy to development environment
./scripts/deploy.sh development

# Port forward services for local access
kubectl port-forward svc/frontend-service 8080:80 -n f1-analytics-development
kubectl port-forward svc/api-gateway-service 8000:8000 -n f1-analytics-development
```

Visit http://localhost:8080 to access the application.

## 📖 Documentation

### Deployment Guides
- [**🔒 Secure Kubernetes Deployment**](docs/SECURE_DEPLOYMENT.md) - Complete production deployment with enterprise security
- [**📋 Security Implementation Checklist**](docs/SECURITY_CHECKLIST.md) - Verification and compliance guide
- [**🔐 External Secrets Setup**](infrastructure/kubernetes/external-secrets/README.md) - AWS Secrets Manager integration
- [**🛡️ Security Validation**](scripts/validate-security.sh) - Automated security compliance checking
- [**💻 Local Development Setup**](docs/concepts/f1-prediction-analytics/LLD.md) - Development environment configuration

### Architecture Documentation
- [**Product Requirements**](docs/concepts/f1-prediction-analytics/PRD.md) - Business requirements and feature specifications
- [**High-Level Design**](docs/concepts/f1-prediction-analytics/HLD.md) - System architecture and component design
- [**Low-Level Design**](docs/concepts/f1-prediction-analytics/LLD.md) - Implementation details and database schema
- [**Project Timeline**](docs/concepts/f1-prediction-analytics/timeline.md) - Development milestones and sprint planning

## 🔒 Security Features

### Enterprise Security Standards
- **🔐 External Secret Management**: AWS Secrets Manager integration with External Secrets Operator
- **🛡️ Zero Hardcoded Secrets**: No credentials stored in version control
- **🔑 Modern Authentication**: SCRAM-SHA-256 PostgreSQL authentication
- **🌐 Environment-Specific Configuration**: Separate configs for production/staging/development
- **🚫 Non-Root Containers**: All services run with minimal privileges
- **🛂 Network Security**: Comprehensive network policies with micro-segmentation and default-deny-all
- **📜 SSL/TLS**: Encrypted connections for all database and Redis communications
- **🔄 Secret Rotation**: Automated secret rotation support via AWS

### Compliance & Auditing
- **📊 Audit Logging**: AWS CloudTrail integration for secret access
- **🎯 Fine-Grained Access Control**: IAM roles with minimal permissions
- **📋 Security Monitoring**: Prometheus metrics for security events

## 🔧 Configuration

### Secure Secret Management

**No longer using environment variables!** All secrets are managed through AWS Secrets Manager:

```bash
# Create secrets in AWS (see external-secrets/README.md for full guide)
aws secretsmanager create-secret --name f1-analytics/postgres --secret-string '{
  "username": "f1_analytics",
  "password": "GENERATED_SECURE_PASSWORD",
  "replication_password": "GENERATED_REPLICATION_PASSWORD"
}'
```

### Domain Configuration

Update environment-specific domain configuration:

```yaml
# infrastructure/kubernetes/environments/production/domains.yaml
data:
  PRIMARY_DOMAIN: "your-domain.com"              # REPLACE with actual domain
  FRONTEND_DOMAIN: "your-domain.com"
  API_DOMAIN: "api.your-domain.com"
  CONTACT_EMAIL: "admin@your-domain.com"         # REPLACE with actual email
```

```

## 📊 Monitoring

### Dashboards
- **System Overview**: Infrastructure health and performance metrics
- **ML Performance**: Model accuracy, inference latency, prediction trends
- **Business Metrics**: User engagement, prediction accuracy, data quality

### Key Metrics
- API response time (p95 < 2s)
- Prediction accuracy (target >70%)
- Database query performance
- Cache hit rates (target >80%)
- ML inference latency (<5s)

### Alerting
- Critical: Service downtime, high error rates
- Warning: Performance degradation, data staleness
- Notification channels: Slack, PagerDuty, email

## 🔐 Security

### Production Security Features
- TLS encryption for all external communications
- JWT-based authentication with role-based access
- Network policies for pod-to-pod communication
- Pod security contexts with minimal privileges
- Secrets encrypted at rest in etcd
- Regular security scanning of container images

### Compliance
- GDPR-compliant user data handling
- SOC 2 Type II security controls
- Regular penetration testing
- Audit logging for all administrative actions

## 🧪 Testing

### Test Coverage
- Unit tests: >90% coverage for core logic
- Integration tests: API endpoints and database operations
- Load tests: 1000+ concurrent users, <2s response time
- ML model validation: Cross-validation, backtesting

### Quality Assurance
- Automated testing in CI/CD pipeline
- Code quality gates with SonarQube
- Performance regression testing
- Security vulnerability scanning

## 🚢 Deployment Environments

### Development
- Local Kubernetes cluster (minikube/kind)
- Reduced resource requirements
- Debug logging enabled
- Hot reloading for development

### Staging
- Production-like environment
- Basic authentication for access control
- Automated testing against real data
- Performance monitoring

### Production
- Multi-zone deployment for high availability
- Auto-scaling based on demand
- Full monitoring and alerting
- Disaster recovery procedures

## 📈 Performance

### Scalability
- **Horizontal scaling**: 3-10 replicas per service
- **Database**: Read replicas for analytics queries
- **Cache**: Redis clustering for high throughput
- **Load testing**: Validated for 10,000+ concurrent users

### Optimization
- CDN for static asset delivery
- Database query optimization with indexes
- Model caching for fast inference
- Connection pooling for database efficiency

## 🤝 Contributing

### Development Workflow
1. Fork the repository
2. Create feature branch: `git checkout -b feature/amazing-feature`
3. Run tests: `./scripts/test.sh`
4. Commit changes: `git commit -m 'Add amazing feature'`
5. Push branch: `git push origin feature/amazing-feature`
6. Create Pull Request

### Code Standards
- Python: Black formatting, flake8 linting, type hints
- JavaScript: ESLint, Prettier, TypeScript
- Documentation: Comprehensive README and inline comments
- Testing: Minimum 90% test coverage required

## 📧 Support

### Contact Information
- **Issues**: GitHub Issues for bug reports and feature requests
- **Documentation**: Comprehensive guides in `/docs` directory
- **DevOps Support**: devops@f1-analytics.example.com
- **Security Issues**: security@f1-analytics.example.com

### Community
- **Discussions**: GitHub Discussions for questions and ideas
- **Slack**: #f1-analytics for real-time chat
- **Office Hours**: Weekly Thursday 2-3 PM PST

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 🙏 Acknowledgments

- **Ergast API**: Historical F1 data source
- **OpenWeatherMap**: Weather data for race predictions
- **Formula 1**: Inspiration and data standards
- **Open Source Community**: Libraries and frameworks used

---

**Built with ❤️ for Formula 1 fans and data enthusiasts**
