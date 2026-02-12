# F1 Prediction Analytics Infrastructure
# Main Terraform configuration for AWS resources

terraform {
  required_version = ">= 1.0"
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
    random = {
      source  = "hashicorp/random"
      version = "~> 3.1"
    }
  }

  # Uncomment and configure for production use
  # backend "s3" {
  #   bucket = "f1-analytics-terraform-state"
  #   key    = "infrastructure/terraform.tfstate"
  #   region = "us-west-2"
  #   encrypt = true
  #   dynamodb_table = "f1-analytics-terraform-locks"
  # }
}

# Configure the AWS Provider
provider "aws" {
  region = var.aws_region

  default_tags {
    tags = {
      Project     = "f1-prediction-analytics"
      Environment = var.environment
      ManagedBy   = "terraform"
      Owner       = "f1-analytics-team"
    }
  }
}

# Local values for resource naming
locals {
  name_prefix = "f1-analytics-${var.environment}"

  common_tags = {
    Project     = "f1-prediction-analytics"
    Environment = var.environment
    ManagedBy   = "terraform"
  }
}

# VPC Module
module "vpc" {
  source = "./modules/vpc"

  name_prefix        = local.name_prefix
  cidr_block        = var.vpc_cidr_block
  availability_zones = var.availability_zones

  tags = local.common_tags
}

# EKS Cluster Module
module "eks" {
  source = "./modules/eks"

  name_prefix    = local.name_prefix
  cluster_name   = "${local.name_prefix}-cluster"
  cluster_version = var.eks_cluster_version

  vpc_id           = module.vpc.vpc_id
  subnet_ids       = module.vpc.private_subnet_ids
  public_subnet_ids = module.vpc.public_subnet_ids

  node_groups = var.eks_node_groups

  tags = local.common_tags
}

# RDS PostgreSQL Module
module "rds" {
  source = "./modules/rds"

  name_prefix = local.name_prefix

  vpc_id            = module.vpc.vpc_id
  subnet_ids        = module.vpc.private_subnet_ids
  allowed_cidr_blocks = [var.vpc_cidr_block]

  instance_class    = var.rds_instance_class
  allocated_storage = var.rds_allocated_storage
  max_allocated_storage = var.rds_max_allocated_storage

  database_name     = var.rds_database_name
  database_username = var.rds_database_username
  database_password = var.rds_database_password

  backup_retention_period = var.rds_backup_retention_period
  multi_az               = var.rds_multi_az

  tags = local.common_tags
}

# ElastiCache Redis Module
module "redis" {
  source = "./modules/elasticache"

  name_prefix = local.name_prefix

  vpc_id            = module.vpc.vpc_id
  subnet_ids        = module.vpc.private_subnet_ids
  allowed_cidr_blocks = [var.vpc_cidr_block]

  node_type           = var.redis_node_type
  num_cache_clusters  = var.redis_num_cache_clusters
  parameter_group_name = var.redis_parameter_group_name

  tags = local.common_tags
}

# S3 Buckets Module
module "s3" {
  source = "./modules/s3"

  name_prefix = local.name_prefix
  environment = var.environment

  enable_versioning = var.s3_enable_versioning

  tags = local.common_tags
}

# Monitoring Module
module "monitoring" {
  source = "./modules/monitoring"

  name_prefix  = local.name_prefix
  cluster_name = module.eks.cluster_name

  vpc_id     = module.vpc.vpc_id
  subnet_ids = module.vpc.public_subnet_ids

  tags = local.common_tags
}