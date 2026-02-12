# Infrastructure Documentation: F1 Prediction Analytics Platform

**Created:** 2026-02-12
**Status:** Implemented

## Overview

This document describes the complete infrastructure implementation for the F1 Prediction Analytics platform using Terraform on AWS. The infrastructure is designed to support a production-ready machine learning platform with high availability, scalability, and security.

## Architecture Summary

The F1 Prediction Analytics platform is deployed on AWS using a microservices architecture with the following components:

- **Compute**: Amazon EKS (Kubernetes) for container orchestration
- **Database**: Amazon RDS PostgreSQL for primary data storage
- **Cache**: Amazon ElastiCache Redis for session management and caching
- **Storage**: Amazon S3 for ML model artifacts, data backups, and logs
- **Networking**: VPC with public/private subnets across multiple AZs
- **Load Balancing**: Application Load Balancer for high availability
- **Monitoring**: CloudWatch for metrics, logs, and dashboards

## Infrastructure Components

### 1. Networking (VPC Module)

**Location:** `f1-analytics/infrastructure/terraform/modules/vpc/`

- **VPC**: 10.0.0.0/16 CIDR block with DNS hostnames enabled
- **Public Subnets**: 3 subnets across AZs for load balancers and NAT gateways
- **Private Subnets**: 3 subnets across AZs for EKS nodes and applications
- **Database Subnets**: 3 subnets across AZs for RDS instances
- **NAT Gateways**: One per AZ for high availability internet access
- **VPC Flow Logs**: Enabled for security monitoring

**Key Features:**
- Multi-AZ deployment for high availability
- Network segmentation for security
- Automatic subnet CIDR calculation
- Kubernetes-ready subnet tagging

### 2. Container Platform (EKS Module)

**Location:** `f1-analytics/infrastructure/terraform/modules/eks/`

- **EKS Cluster**: Kubernetes 1.28 with public/private endpoint access
- **Node Groups**:
  - `general`: t3.medium instances for API services
  - `ml_workload`: m5.large instances for ML training (with Spot pricing)
- **Add-ons**: VPC CNI, CoreDNS, kube-proxy, EBS CSI driver
- **IRSA**: IAM Roles for Service Accounts enabled
- **Cluster Autoscaler**: Support for automatic node scaling

**Security Features:**
- Private cluster endpoint access
- Network policies support
- Security groups with restrictive rules
- OIDC provider for service account authentication

### 3. Database (RDS Module)

**Location:** `f1-analytics/infrastructure/terraform/modules/rds/`

- **Engine**: PostgreSQL 15.4 with optimized parameter group
- **Instance Class**: db.r5.large (configurable by environment)
- **Storage**: 100GB with auto-scaling up to 1TB
- **Backup**: 7-day retention with automated backups
- **Read Replicas**: Optional for read scaling
- **Encryption**: At-rest encryption enabled by default

**Performance Optimizations:**
- Custom parameter group with tuned settings
- Connection pooling configuration
- Enhanced monitoring enabled
- Performance Insights enabled

**Monitoring:**
- CPU utilization alarms
- Connection count monitoring
- Memory usage tracking
- Storage space monitoring

### 4. Caching (ElastiCache Module)

**Location:** `f1-analytics/infrastructure/terraform/modules/elasticache/`

- **Engine**: Redis 7.0 with cluster mode
- **Configuration**: 3 nodes with 1 replica per node group
- **Instance Type**: cache.r7g.large (memory optimized)
- **Security**: Encryption at-rest and in-transit
- **Authentication**: Redis AUTH with generated tokens

**Features:**
- Automatic failover enabled
- Multi-AZ deployment
- Parameter group optimization
- Backup snapshots (5-day retention)

### 5. Storage (S3 Module)

**Location:** `f1-analytics/infrastructure/terraform/modules/s3/`

Three S3 buckets with specific purposes:

1. **Model Storage** (`f1-analytics-{env}-ml-models-{suffix}`)
   - ML model artifacts and versions
   - Lifecycle: Standard → Standard-IA (30d) → Glacier (90d) → Deep Archive (365d)
   - Versioning enabled for model tracking

2. **Data Backup** (`f1-analytics-{env}-data-backup-{suffix}`)
   - Database backups and exports
   - Lifecycle: Standard → Standard-IA (7d) → Glacier (30d) → Deep Archive (90d)
   - 7-year retention policy

3. **Logs** (`f1-analytics-{env}-logs-{suffix}`)
   - Application and system logs
   - Lifecycle: Standard → Standard-IA (7d) → Glacier (30d)
   - 1-year retention policy

**Security Features:**
- Server-side encryption (AES256/KMS)
- Public access blocked
- IAM policies for service access
- Bucket notifications for automation

### 6. Monitoring (Monitoring Module)

**Location:** `f1-analytics/infrastructure/terraform/modules/monitoring/`

#### Application Load Balancer
- **Type**: Application Load Balancer (internet-facing)
- **Listeners**: HTTP (redirects to HTTPS) and HTTPS
- **Target Groups**: Separate groups for API and frontend services
- **Health Checks**: Configurable endpoints with proper timeouts

#### CloudWatch Resources
- **Log Groups**: Application, API, ML Pipeline, and Ingestion logs
- **Dashboard**: System overview with key metrics and log insights
- **Alarms**: Response time, error rates, and system health monitoring
- **Custom Metrics**: Prediction accuracy, training duration, ingestion metrics

#### Alerting
- **SNS Topic**: Optional email notifications
- **Composite Alarms**: Overall system health monitoring
- **EventBridge**: Automated triggers for ML training schedules

## Deployment

### Prerequisites

1. **AWS CLI**: Configured with appropriate permissions
2. **Terraform**: Version 1.0 or later
3. **kubectl**: For Kubernetes cluster management

### Quick Start

```bash
# Navigate to infrastructure directory
cd f1-analytics/infrastructure/terraform

# Copy and customize variables
cp terraform.tfvars.example terraform.tfvars
# Edit terraform.tfvars with your configuration

# Deploy infrastructure
./scripts/deploy.sh -e dev -a apply --auto-approve
```

### Environment-Specific Deployments

**Development:**
```bash
./scripts/deploy.sh -e dev -a apply
```

**Staging:**
```bash
./scripts/deploy.sh -e staging -a apply
```

**Production:**
```bash
./scripts/deploy.sh -e prod -a apply
```

## Configuration

### Required Variables

```hcl
# terraform.tfvars
aws_region = "us-west-2"
environment = "dev"
rds_database_password = "your-secure-password"

# Optional overrides for production
eks_node_groups = {
  general = {
    instance_types = ["m5.xlarge"]
    scaling_config = {
      desired_size = 3
      max_size     = 10
      min_size     = 2
    }
    disk_size     = 100
    capacity_type = "ON_DEMAND"
  }
}
```

### Environment Differences

| Component | Development | Production |
|-----------|-------------|------------|
| RDS Instance | db.r5.large | db.r5.2xlarge |
| RDS Multi-AZ | Disabled | Enabled |
| EKS Nodes | t3.medium | m5.xlarge |
| Node Count | 2-5 | 3-10 |
| Spot Instances | ML workloads | Limited use |
| Backups | 7 days | 30 days |

## Security

### Network Security
- VPC with private subnets for compute resources
- Security groups with least-privilege access
- NAT gateways for outbound internet access
- VPC flow logs for network monitoring

### Data Security
- Encryption at-rest for all storage (RDS, ElastiCache, S3)
- Encryption in-transit with TLS 1.2+
- IAM roles with minimal required permissions
- AWS Secrets Manager integration (recommended)

### Application Security
- EKS cluster with private endpoint access
- RBAC for Kubernetes resources
- Service mesh ready (Istio/Linkerd compatible)
- Container image scanning (recommended)

## Monitoring and Observability

### Key Metrics Tracked
- **Infrastructure**: CPU, memory, disk, network utilization
- **Application**: Request rates, response times, error rates
- **Business**: Prediction accuracy, model training duration
- **Database**: Connection counts, query performance, storage usage

### Dashboards
- **System Health**: Overall platform status and performance
- **Application Performance**: API metrics and user experience
- **ML Pipeline**: Training metrics and prediction accuracy
- **Cost Monitoring**: Resource utilization and optimization opportunities

### Alerting Strategy
- **Critical**: Service outages, high error rates, security events
- **Warning**: Performance degradation, resource thresholds
- **Info**: Deployment notifications, backup completions

## Scaling Strategy

### Horizontal Scaling
- **EKS**: Cluster Autoscaler based on pod resource requests
- **Database**: Read replicas for read-heavy workloads
- **Cache**: Additional Redis nodes for memory scaling
- **Storage**: S3 scales automatically

### Vertical Scaling
- **Compute**: Larger instance types for EKS nodes
- **Database**: Higher performance instance classes
- **Cache**: Memory-optimized instance types

## Disaster Recovery

### Backup Strategy
- **Database**: Automated daily backups with point-in-time recovery
- **Configuration**: Infrastructure as Code in version control
- **Application**: Container images in ECR with versioning
- **Data**: Cross-region S3 replication for critical data

### Recovery Procedures
1. **Infrastructure**: Redeploy using Terraform
2. **Database**: Restore from latest backup or snapshot
3. **Applications**: Redeploy from CI/CD pipeline
4. **Data**: Restore from S3 backups

### RTO/RPO Targets
- **Recovery Time Objective (RTO)**: 4 hours
- **Recovery Point Objective (RPO)**: 1 hour (database), 24 hours (other data)

## Cost Optimization

### Development Environment
- Spot instances for non-critical workloads
- Smaller instance sizes
- Shorter backup retention periods
- Single AZ deployment for non-critical resources

### Production Environment
- Reserved Instances for predictable workloads
- S3 Intelligent Tiering for automatic cost optimization
- CloudWatch cost monitoring and budgets
- Regular rightsizing reviews

### Cost Monitoring
- CloudWatch billing alarms
- AWS Cost Explorer integration
- Monthly cost optimization reviews
- Resource tagging for cost allocation

## Maintenance

### Regular Tasks
- **Weekly**: Review monitoring alerts and performance metrics
- **Monthly**: Apply security patches to EKS node groups
- **Quarterly**: Review and update Terraform modules
- **Annually**: Conduct disaster recovery testing

### Automated Maintenance
- EKS node group rolling updates
- RDS maintenance windows (configured)
- S3 lifecycle policy execution
- CloudWatch log retention management

## Troubleshooting

### Common Issues

1. **EKS Node Connectivity**
   ```bash
   # Check node status
   kubectl get nodes

   # Check node group health
   aws eks describe-nodegroup --cluster-name <cluster> --nodegroup-name <nodegroup>
   ```

2. **Database Connection Issues**
   ```bash
   # Test connectivity
   telnet <rds-endpoint> 5432

   # Check security groups
   aws ec2 describe-security-groups --group-ids <sg-id>
   ```

3. **Application Load Balancer Issues**
   ```bash
   # Check target health
   aws elbv2 describe-target-health --target-group-arn <tg-arn>

   # View ALB logs
   aws logs filter-log-events --log-group-name <alb-log-group>
   ```

### Debug Commands

```bash
# Terraform debugging
export TF_LOG=DEBUG
terraform plan

# AWS resource inspection
aws eks describe-cluster --name <cluster-name>
aws rds describe-db-instances --db-instance-identifier <instance-id>
aws elasticache describe-replication-groups --replication-group-id <group-id>

# CloudWatch metrics
aws cloudwatch get-metric-statistics --namespace AWS/EKS --metric-name cluster_request_total
```

## Support and Documentation

### Additional Resources
- **Terraform Registry**: Module documentation and examples
- **AWS Documentation**: Service-specific configuration guides
- **Kubernetes Documentation**: EKS best practices and troubleshooting
- **Monitoring**: CloudWatch and Prometheus integration guides

### Contact Information
- **Infrastructure Team**: DevOps engineers responsible for platform
- **Security Team**: For security-related questions and compliance
- **Development Team**: For application-specific infrastructure needs

---

*This documentation is maintained alongside the infrastructure code and updated with each major release.*