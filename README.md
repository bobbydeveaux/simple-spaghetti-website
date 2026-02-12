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

### One-Click Deployment

```bash
# Clone repository
git clone <repository-url>
cd simple-spaghetti-website

# Deploy to Kubernetes
./scripts/deploy.sh production
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
- [**Kubernetes Deployment Guide**](docs/KUBERNETES_DEPLOYMENT.md) - Complete production deployment instructions
- [**Local Development Setup**](docs/concepts/f1-prediction-analytics/LLD.md) - Development environment configuration
- [**Production Checklist**](docs/concepts/f1-prediction-analytics/ROAM.md) - Security and performance considerations

### Architecture Documentation
- [**Product Requirements**](docs/concepts/f1-prediction-analytics/PRD.md) - Business requirements and feature specifications
- [**High-Level Design**](docs/concepts/f1-prediction-analytics/HLD.md) - System architecture and component design
- [**Low-Level Design**](docs/concepts/f1-prediction-analytics/LLD.md) - Implementation details and database schema
- [**Project Timeline**](docs/concepts/f1-prediction-analytics/timeline.md) - Development milestones and sprint planning

## 🔧 Configuration

### Required Environment Variables

```yaml
# External API Keys
OPENWEATHER_API_KEY: your_openweather_api_key

# Database Configuration
DATABASE_URL: postgresql://user:pass@host:5432/f1_analytics

# Redis Configuration
REDIS_URL: redis://host:6379/0

# JWT Configuration
JWT_SECRET_KEY: your_secure_jwt_secret

# AWS Configuration (for model storage)
AWS_ACCESS_KEY_ID: your_aws_access_key
AWS_SECRET_ACCESS_KEY: your_aws_secret_key
```

### Secrets Management

All secrets are managed through Kubernetes secrets. Update `infrastructure/kubernetes/secrets.yaml` with your values:

```bash
# Generate secure passwords
export POSTGRES_PASSWORD=$(openssl rand -base64 32)
export JWT_SECRET=$(openssl rand -base64 64)

# Base64 encode for Kubernetes
echo -n "$POSTGRES_PASSWORD" | base64
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
