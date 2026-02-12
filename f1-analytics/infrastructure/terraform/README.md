# F1 Prediction Analytics Terraform Infrastructure

This directory contains the Terraform infrastructure code for the F1 Prediction Analytics platform.

## Architecture Overview

The infrastructure consists of:

- **VPC**: Multi-AZ VPC with public, private, and database subnets
- **EKS**: Managed Kubernetes cluster with multiple node groups
- **RDS**: PostgreSQL database with Multi-AZ support and read replicas
- **ElastiCache**: Redis cluster for caching and session management
- **S3**: Buckets for ML model storage, data backups, and logs
- **Monitoring**: Application Load Balancer, CloudWatch dashboards, and alerts

## Prerequisites

- [Terraform](https://www.terraform.io/downloads.html) >= 1.0
- [AWS CLI](https://aws.amazon.com/cli/) configured with appropriate permissions
- [kubectl](https://kubernetes.io/docs/tasks/tools/install-kubectl/) for Kubernetes management

## Required AWS Permissions

The AWS user/role executing Terraform needs permissions for:

- EC2 (VPC, Security Groups, Subnets)
- EKS (Cluster, Node Groups)
- RDS (Database instances, Subnet groups, Parameter groups)
- ElastiCache (Replication groups, Subnet groups)
- S3 (Buckets, Policies)
- CloudWatch (Log groups, Alarms, Dashboards)
- Application Load Balancer
- IAM (Roles, Policies for EKS and other services)

## Quick Start

1. **Clone the repository** and navigate to the Terraform directory:
   ```bash
   cd f1-analytics/infrastructure/terraform
   ```

2. **Copy and customize the variables file**:
   ```bash
   cp terraform.tfvars.example terraform.tfvars
   # Edit terraform.tfvars with your desired configuration
   ```

3. **Initialize Terraform**:
   ```bash
   terraform init
   ```

4. **Plan the infrastructure**:
   ```bash
   terraform plan
   ```

5. **Apply the infrastructure**:
   ```bash
   terraform apply
   ```

6. **Configure kubectl** (after EKS cluster is created):
   ```bash
   aws eks update-kubeconfig --region <region> --name <cluster-name>
   ```

## Configuration

### Required Variables

- `rds_database_password`: Database password (use AWS Secrets Manager in production)

### Environment-Specific Configurations

The infrastructure supports different environments (dev, staging, prod) through variables:

```hcl
# Development
environment = "dev"
rds_multi_az = false
rds_instance_class = "db.r5.large"

# Production
environment = "prod"
rds_multi_az = true
rds_instance_class = "db.r5.2xlarge"
```

### Node Groups

Configure EKS node groups for different workloads:

```hcl
eks_node_groups = {
  general = {
    instance_types = ["t3.medium"]
    scaling_config = {
      desired_size = 2
      max_size     = 5
      min_size     = 1
    }
    disk_size     = 50
    capacity_type = "ON_DEMAND"
  }
  ml_workload = {
    instance_types = ["c5.large"]
    scaling_config = {
      desired_size = 1
      max_size     = 5
      min_size     = 0
    }
    disk_size     = 100
    capacity_type = "SPOT"
  }
}
```

## Modules

The infrastructure is organized into modules:

- **`modules/vpc`**: VPC, subnets, NAT gateways, route tables
- **`modules/eks`**: EKS cluster, node groups, add-ons
- **`modules/rds`**: PostgreSQL database, parameter groups, monitoring
- **`modules/elasticache`**: Redis cluster, security groups, monitoring
- **`modules/s3`**: S3 buckets, lifecycle policies, IAM policies
- **`modules/monitoring`**: ALB, CloudWatch, dashboards, alarms

## Outputs

After applying, Terraform provides outputs for:

- Database connection strings
- Redis connection information
- EKS cluster details
- S3 bucket names
- Application Load Balancer DNS name
- Monitoring dashboard URLs

## Security Considerations

### Production Hardening

For production deployments:

1. **Enable Multi-AZ**: Set `rds_multi_az = true` and `redis_multi_az_enabled = true`
2. **Use Secrets Manager**: Store database passwords in AWS Secrets Manager
3. **Enable encryption**: All modules enable encryption by default
4. **Network isolation**: Database resources are in private subnets
5. **Security groups**: Restrictive security group rules
6. **Backup configuration**: Automated backups with configurable retention

### Access Control

- Database access restricted to VPC CIDR blocks
- S3 buckets have public access blocked
- EKS cluster endpoints can be configured for private access
- IAM roles follow principle of least privilege

## Monitoring and Observability

The infrastructure includes comprehensive monitoring:

- **CloudWatch Dashboards**: System overview, performance metrics
- **CloudWatch Alarms**: Response time, error rates, resource utilization
- **Log Groups**: Application logs, API logs, ML pipeline logs
- **Custom Metrics**: Prediction accuracy, training duration, ingestion metrics

## Disaster Recovery

### Backup Strategy

- **RDS**: Automated daily backups with point-in-time recovery
- **S3**: Cross-region replication for critical data
- **EKS**: Configuration stored in version control

### Recovery Procedures

1. **Database recovery**: Restore from automated backups or snapshots
2. **Cluster recovery**: Recreate EKS cluster from Terraform configuration
3. **Application recovery**: Redeploy applications using CI/CD pipeline

## Scaling

### Horizontal Scaling

- **EKS**: Cluster Autoscaler for automatic node scaling
- **RDS**: Read replicas for read-heavy workloads
- **Redis**: Multiple cache nodes for high availability

### Vertical Scaling

Modify instance types in `terraform.tfvars`:

```hcl
rds_instance_class = "db.r5.2xlarge"
redis_node_type = "cache.r5.2xlarge"
```

## Cost Optimization

### Development Environment

- Use smaller instance types
- Disable Multi-AZ deployment
- Use Spot instances for non-critical workloads
- Shorter backup retention periods

### Production Environment

- Reserved Instances for predictable workloads
- S3 Intelligent Tiering for cost optimization
- CloudWatch cost monitoring alarms

## Troubleshooting

### Common Issues

1. **Permission errors**: Verify AWS IAM permissions
2. **Resource limits**: Check AWS service quotas
3. **Network connectivity**: Verify security group rules
4. **DNS resolution**: Check VPC DNS settings

### Debugging Commands

```bash
# Check Terraform state
terraform show

# View detailed logs
export TF_LOG=DEBUG
terraform plan

# Check EKS cluster status
aws eks describe-cluster --name <cluster-name>

# Test database connectivity
psql -h <endpoint> -U <username> -d <database>
```

## Maintenance

### Regular Tasks

1. **Update Terraform**: Keep Terraform and providers up to date
2. **Patch management**: Update EKS node groups regularly
3. **Security updates**: Monitor and apply security patches
4. **Backup verification**: Test backup and restore procedures

### Monitoring Alerts

Configure alerts for:

- High error rates
- Resource utilization thresholds
- Database connection limits
- Cache memory usage

## Support

For issues with the infrastructure:

1. Check CloudWatch logs and metrics
2. Review Terraform plan before applying changes
3. Test changes in development environment first
4. Follow the troubleshooting guide above