# Variables for ElastiCache Module

variable "name_prefix" {
  description = "Name prefix for resources"
  type        = string
}

variable "vpc_id" {
  description = "VPC ID where the ElastiCache cluster will be created"
  type        = string
}

variable "subnet_ids" {
  description = "List of subnet IDs for the ElastiCache subnet group"
  type        = list(string)

  validation {
    condition     = length(var.subnet_ids) >= 2
    error_message = "At least 2 subnet IDs must be provided for high availability."
  }
}

variable "allowed_cidr_blocks" {
  description = "List of CIDR blocks allowed to access the Redis cluster"
  type        = list(string)
  default     = []
}

# Engine Configuration
variable "engine_version" {
  description = "Redis engine version"
  type        = string
  default     = "7.0"

  validation {
    condition     = can(regex("^[67]\\.[0-9]$", var.engine_version))
    error_message = "Engine version must be 6.x or 7.x format."
  }
}

variable "node_type" {
  description = "ElastiCache node type"
  type        = string
  default     = "cache.r7g.large"

  validation {
    condition = can(regex("^cache\\.(t3|t4g|m5|m6i|m7g|r5|r6g|r7g|c5|c6g|c7g)\\.(micro|small|medium|large|xlarge|2xlarge|4xlarge|8xlarge|12xlarge|16xlarge|24xlarge)$", var.node_type))
    error_message = "Node type must be a valid ElastiCache node type."
  }
}

variable "num_cache_clusters" {
  description = "Number of cache clusters (nodes) in the replication group"
  type        = number
  default     = 3

  validation {
    condition     = var.num_cache_clusters >= 1 && var.num_cache_clusters <= 500
    error_message = "Number of cache clusters must be between 1 and 500."
  }
}

variable "replicas_per_node_group" {
  description = "Number of replica nodes in each node group"
  type        = number
  default     = 1

  validation {
    condition     = var.replicas_per_node_group >= 0 && var.replicas_per_node_group <= 5
    error_message = "Replicas per node group must be between 0 and 5."
  }
}

# Security Configuration
variable "at_rest_encryption_enabled" {
  description = "Enable encryption at rest"
  type        = bool
  default     = true
}

variable "transit_encryption_enabled" {
  description = "Enable encryption in transit (TLS)"
  type        = bool
  default     = true
}

variable "auth_token" {
  description = "Auth token for Redis authentication (if null, a random token will be generated when transit encryption is enabled)"
  type        = string
  sensitive   = true
  default     = null

  validation {
    condition = var.auth_token == null || (
      length(var.auth_token) >= 16 &&
      length(var.auth_token) <= 128 &&
      can(regex("^[a-zA-Z0-9]+$", var.auth_token))
    )
    error_message = "Auth token must be 16-128 characters long and contain only alphanumeric characters."
  }
}

# Redis User Configuration (for Redis 6.0+)
variable "create_redis_user" {
  description = "Create Redis user for authentication"
  type        = bool
  default     = false
}

variable "redis_username" {
  description = "Redis username for authentication"
  type        = string
  default     = "f1analytics"

  validation {
    condition     = can(regex("^[a-zA-Z][a-zA-Z0-9_]*$", var.redis_username))
    error_message = "Redis username must start with a letter and contain only alphanumeric characters and underscores."
  }
}

# Performance Configuration
variable "maxmemory_policy" {
  description = "Redis maxmemory policy"
  type        = string
  default     = "allkeys-lru"

  validation {
    condition = contains([
      "volatile-lru", "allkeys-lru", "volatile-lfu", "allkeys-lfu",
      "volatile-random", "allkeys-random", "volatile-ttl", "noeviction"
    ], var.maxmemory_policy)
    error_message = "Invalid maxmemory policy. Must be one of: volatile-lru, allkeys-lru, volatile-lfu, allkeys-lfu, volatile-random, allkeys-random, volatile-ttl, noeviction."
  }
}

# High Availability Configuration
variable "automatic_failover_enabled" {
  description = "Enable automatic failover for the replication group"
  type        = bool
  default     = true
}

variable "multi_az_enabled" {
  description = "Enable Multi-AZ deployment"
  type        = bool
  default     = true
}

# Backup Configuration
variable "snapshot_retention_limit" {
  description = "Number of days for which ElastiCache retains automatic snapshots"
  type        = number
  default     = 5

  validation {
    condition     = var.snapshot_retention_limit >= 0 && var.snapshot_retention_limit <= 35
    error_message = "Snapshot retention limit must be between 0 and 35 days."
  }
}

variable "snapshot_window" {
  description = "Daily snapshot window in UTC (format: HH:MM-HH:MM)"
  type        = string
  default     = "03:00-05:00"

  validation {
    condition = can(regex("^([0-1][0-9]|2[0-3]):[0-5][0-9]-([0-1][0-9]|2[0-3]):[0-5][0-9]$", var.snapshot_window))
    error_message = "Snapshot window must be in format HH:MM-HH:MM (24-hour UTC)."
  }
}

# Maintenance Configuration
variable "maintenance_window" {
  description = "Weekly maintenance window (format: ddd:HH:MM-ddd:HH:MM)"
  type        = string
  default     = "sun:05:00-sun:06:00"

  validation {
    condition = can(regex("^(sun|mon|tue|wed|thu|fri|sat):[0-2][0-9]:[0-5][0-9]-(sun|mon|tue|wed|thu|fri|sat):[0-2][0-9]:[0-5][0-9]$", var.maintenance_window))
    error_message = "Maintenance window must be in format ddd:HH:MM-ddd:HH:MM (UTC)."
  }
}

variable "notification_topic_arn" {
  description = "ARN of SNS topic for ElastiCache notifications"
  type        = string
  default     = null
}

# Monitoring Configuration
variable "log_retention_days" {
  description = "CloudWatch logs retention period in days"
  type        = number
  default     = 7

  validation {
    condition = contains([
      1, 3, 5, 7, 14, 30, 60, 90, 120, 150, 180, 365, 400, 545, 731, 1096, 1827, 2192, 2557, 2922, 3288, 3653
    ], var.log_retention_days)
    error_message = "Log retention days must be a valid CloudWatch log retention period."
  }
}

variable "alarm_actions" {
  description = "List of ARNs to notify when CloudWatch alarms trigger"
  type        = list(string)
  default     = []
}

variable "connection_threshold" {
  description = "Threshold for connection count alarm"
  type        = number
  default     = 1000

  validation {
    condition     = var.connection_threshold > 0
    error_message = "Connection threshold must be greater than 0."
  }
}

# Global Replication (Cross-Region)
variable "enable_global_replication" {
  description = "Enable global replication for cross-region deployment"
  type        = bool
  default     = false
}

# Parameter Group Configuration
variable "custom_parameters" {
  description = "Additional Redis parameters to set"
  type = list(object({
    name  = string
    value = string
  }))
  default = []
}

variable "tags" {
  description = "Additional tags to apply to resources"
  type        = map(string)
  default     = {}
}