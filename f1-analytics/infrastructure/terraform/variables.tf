# Variables for F1 Prediction Analytics Infrastructure

variable "aws_region" {
  description = "AWS region to deploy infrastructure"
  type        = string
  default     = "us-west-2"
}

variable "environment" {
  description = "Environment name (dev, staging, prod)"
  type        = string
  default     = "dev"

  validation {
    condition     = contains(["dev", "staging", "prod"], var.environment)
    error_message = "Environment must be one of: dev, staging, prod."
  }
}

# VPC Configuration
variable "vpc_cidr_block" {
  description = "CIDR block for the VPC"
  type        = string
  default     = "10.0.0.0/16"
}

variable "availability_zones" {
  description = "List of availability zones"
  type        = list(string)
  default     = ["us-west-2a", "us-west-2b", "us-west-2c"]
}

# EKS Configuration
variable "eks_cluster_version" {
  description = "Kubernetes version for EKS cluster"
  type        = string
  default     = "1.28"
}

variable "eks_node_groups" {
  description = "EKS node group configurations"
  type = map(object({
    instance_types = list(string)
    scaling_config = object({
      desired_size = number
      max_size     = number
      min_size     = number
    })
    disk_size = number
    capacity_type = string
  }))
  default = {
    general = {
      instance_types = ["t3.medium"]
      scaling_config = {
        desired_size = 2
        max_size     = 10
        min_size     = 1
      }
      disk_size = 50
      capacity_type = "ON_DEMAND"
    }
    ml_workload = {
      instance_types = ["m5.large"]
      scaling_config = {
        desired_size = 1
        max_size     = 5
        min_size     = 0
      }
      disk_size = 100
      capacity_type = "SPOT"
    }
  }
}

# RDS Configuration
variable "rds_instance_class" {
  description = "RDS instance class"
  type        = string
  default     = "db.r5.large"
}

variable "rds_allocated_storage" {
  description = "Initial allocated storage for RDS instance (GB)"
  type        = number
  default     = 100
}

variable "rds_max_allocated_storage" {
  description = "Maximum allocated storage for RDS auto-scaling (GB)"
  type        = number
  default     = 1000
}

variable "rds_database_name" {
  description = "Name of the F1 analytics database"
  type        = string
  default     = "f1_analytics"
}

variable "rds_database_username" {
  description = "Database admin username"
  type        = string
  default     = "f1admin"
}

variable "rds_database_password" {
  description = "Database admin password (use environment variable or secrets manager)"
  type        = string
  sensitive   = true
}

variable "rds_backup_retention_period" {
  description = "Backup retention period in days"
  type        = number
  default     = 7
}

variable "rds_multi_az" {
  description = "Enable multi-AZ for RDS (for production)"
  type        = bool
  default     = false
}

# Redis Configuration
variable "redis_node_type" {
  description = "ElastiCache Redis node type"
  type        = string
  default     = "cache.r5.large"
}

variable "redis_num_cache_clusters" {
  description = "Number of Redis cache clusters"
  type        = number
  default     = 3
}

variable "redis_parameter_group_name" {
  description = "Redis parameter group name"
  type        = string
  default     = "default.redis7"
}

# S3 Configuration
variable "s3_enable_versioning" {
  description = "Enable versioning on S3 buckets"
  type        = bool
  default     = true
}

# Optional: Environment-specific overrides
variable "environment_overrides" {
  description = "Environment-specific configuration overrides"
  type = object({
    rds_instance_class = optional(string)
    redis_node_type   = optional(string)
    eks_node_groups   = optional(map(object({
      instance_types = list(string)
      scaling_config = object({
        desired_size = number
        max_size     = number
        min_size     = number
      })
      disk_size = number
      capacity_type = string
    })))
  })
  default = {}
}