# Outputs for F1 Prediction Analytics Infrastructure

# VPC Outputs
output "vpc_id" {
  description = "ID of the VPC"
  value       = module.vpc.vpc_id
}

output "vpc_cidr_block" {
  description = "CIDR block of the VPC"
  value       = module.vpc.vpc_cidr_block
}

output "private_subnet_ids" {
  description = "IDs of the private subnets"
  value       = module.vpc.private_subnet_ids
}

output "public_subnet_ids" {
  description = "IDs of the public subnets"
  value       = module.vpc.public_subnet_ids
}

# EKS Outputs
output "eks_cluster_id" {
  description = "EKS cluster ID"
  value       = module.eks.cluster_id
}

output "eks_cluster_arn" {
  description = "EKS cluster ARN"
  value       = module.eks.cluster_arn
}

output "eks_cluster_endpoint" {
  description = "EKS cluster endpoint"
  value       = module.eks.cluster_endpoint
}

output "eks_cluster_security_group_id" {
  description = "Security group ID attached to the EKS cluster"
  value       = module.eks.cluster_security_group_id
}

output "eks_node_groups" {
  description = "EKS node group configurations"
  value       = module.eks.node_groups
}

output "eks_cluster_certificate_authority_data" {
  description = "Base64 encoded certificate data required to communicate with the cluster"
  value       = module.eks.cluster_certificate_authority_data
}

# RDS Outputs
output "rds_instance_endpoint" {
  description = "RDS instance endpoint"
  value       = module.rds.db_instance_endpoint
  sensitive   = true
}

output "rds_instance_port" {
  description = "RDS instance port"
  value       = module.rds.db_instance_port
}

output "rds_database_name" {
  description = "Name of the database"
  value       = module.rds.db_instance_name
}

output "rds_security_group_id" {
  description = "Security group ID for RDS instance"
  value       = module.rds.security_group_id
}

# Redis Outputs
output "redis_cluster_id" {
  description = "Redis cluster ID"
  value       = module.redis.cluster_id
}

output "redis_primary_endpoint" {
  description = "Redis primary endpoint"
  value       = module.redis.primary_endpoint
  sensitive   = true
}

output "redis_configuration_endpoint" {
  description = "Redis configuration endpoint"
  value       = module.redis.configuration_endpoint
  sensitive   = true
}

output "redis_security_group_id" {
  description = "Security group ID for Redis cluster"
  value       = module.redis.security_group_id
}

# S3 Outputs
output "s3_model_storage_bucket_name" {
  description = "Name of the S3 bucket for ML model storage"
  value       = module.s3.model_storage_bucket_name
}

output "s3_data_backup_bucket_name" {
  description = "Name of the S3 bucket for data backups"
  value       = module.s3.data_backup_bucket_name
}

output "s3_logs_bucket_name" {
  description = "Name of the S3 bucket for application logs"
  value       = module.s3.logs_bucket_name
}

# Monitoring Outputs
output "cloudwatch_log_group_name" {
  description = "CloudWatch log group name"
  value       = module.monitoring.cloudwatch_log_group_name
}

output "application_load_balancer_arn" {
  description = "ARN of the Application Load Balancer"
  value       = module.monitoring.alb_arn
}

output "application_load_balancer_dns_name" {
  description = "DNS name of the Application Load Balancer"
  value       = module.monitoring.alb_dns_name
}

output "application_load_balancer_zone_id" {
  description = "Zone ID of the Application Load Balancer"
  value       = module.monitoring.alb_zone_id
}

# Connection Information
output "database_connection_string" {
  description = "Database connection string template"
  value       = "postgresql://${var.rds_database_username}:[PASSWORD]@${module.rds.db_instance_endpoint}:${module.rds.db_instance_port}/${module.rds.db_instance_name}"
  sensitive   = true
}

output "redis_connection_string" {
  description = "Redis connection string template"
  value       = "redis://${module.redis.primary_endpoint}"
  sensitive   = true
}

# Kubernetes Configuration
output "kubectl_config" {
  description = "kubectl configuration command"
  value       = "aws eks update-kubeconfig --region ${var.aws_region} --name ${module.eks.cluster_id}"
}

# Environment Information
output "environment_info" {
  description = "Environment configuration summary"
  value = {
    environment = var.environment
    region      = var.aws_region
    vpc_id      = module.vpc.vpc_id
    cluster_id  = module.eks.cluster_id
  }
}