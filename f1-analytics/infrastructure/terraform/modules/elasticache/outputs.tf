# Outputs for ElastiCache Module

# Cluster Information
output "cluster_id" {
  description = "ElastiCache replication group ID"
  value       = aws_elasticache_replication_group.main.id
}

output "cluster_arn" {
  description = "ElastiCache replication group ARN"
  value       = aws_elasticache_replication_group.main.arn
}

output "primary_endpoint_address" {
  description = "Address of the primary endpoint for the replication group"
  value       = aws_elasticache_replication_group.main.primary_endpoint_address
  sensitive   = true
}

output "reader_endpoint_address" {
  description = "Address of the reader endpoint for the replication group"
  value       = aws_elasticache_replication_group.main.reader_endpoint_address
  sensitive   = true
}

output "configuration_endpoint_address" {
  description = "Address of the configuration endpoint (for cluster mode)"
  value       = aws_elasticache_replication_group.main.configuration_endpoint_address
  sensitive   = true
}

# Connection Information
output "port" {
  description = "Redis port"
  value       = aws_elasticache_replication_group.main.port
}

output "auth_token" {
  description = "Redis auth token"
  value       = var.transit_encryption_enabled ? (var.auth_token != null ? var.auth_token : random_password.auth_token[0].result) : null
  sensitive   = true
}

# Security
output "security_group_id" {
  description = "ID of the ElastiCache security group"
  value       = aws_security_group.redis.id
}

output "security_group_arn" {
  description = "ARN of the ElastiCache security group"
  value       = aws_security_group.redis.arn
}

# Subnet Group
output "subnet_group_name" {
  description = "Name of the ElastiCache subnet group"
  value       = aws_elasticache_subnet_group.main.name
}

output "subnet_group_id" {
  description = "ID of the ElastiCache subnet group"
  value       = aws_elasticache_subnet_group.main.id
}

# Parameter Group
output "parameter_group_name" {
  description = "Name of the ElastiCache parameter group"
  value       = aws_elasticache_parameter_group.main.name
}

output "parameter_group_id" {
  description = "ID of the ElastiCache parameter group"
  value       = aws_elasticache_parameter_group.main.id
}

# User and User Group (if created)
output "redis_user_id" {
  description = "ID of the Redis user"
  value       = var.create_redis_user && var.transit_encryption_enabled ? aws_elasticache_user.default[0].user_id : null
}

output "redis_user_group_id" {
  description = "ID of the Redis user group"
  value       = var.create_redis_user && var.transit_encryption_enabled ? aws_elasticache_user_group.main[0].user_group_id : null
}

# Cluster Configuration
output "engine" {
  description = "Redis engine"
  value       = aws_elasticache_replication_group.main.engine
}

output "engine_version" {
  description = "Redis engine version"
  value       = aws_elasticache_replication_group.main.engine_version
}

output "node_type" {
  description = "ElastiCache node type"
  value       = aws_elasticache_replication_group.main.node_type
}

output "num_cache_clusters" {
  description = "Number of cache clusters"
  value       = aws_elasticache_replication_group.main.num_cache_clusters
}

output "member_clusters" {
  description = "List of cluster IDs that are part of this replication group"
  value       = aws_elasticache_replication_group.main.member_clusters
}

# High Availability
output "automatic_failover_enabled" {
  description = "Whether automatic failover is enabled"
  value       = aws_elasticache_replication_group.main.automatic_failover_enabled
}

output "multi_az_enabled" {
  description = "Whether Multi-AZ is enabled"
  value       = aws_elasticache_replication_group.main.multi_az_enabled
}

# Encryption
output "at_rest_encryption_enabled" {
  description = "Whether encryption at rest is enabled"
  value       = aws_elasticache_replication_group.main.at_rest_encryption_enabled
}

output "transit_encryption_enabled" {
  description = "Whether encryption in transit is enabled"
  value       = aws_elasticache_replication_group.main.transit_encryption_enabled
}

# Backup
output "snapshot_retention_limit" {
  description = "Snapshot retention limit in days"
  value       = aws_elasticache_replication_group.main.snapshot_retention_limit
}

output "snapshot_window" {
  description = "Daily snapshot window"
  value       = aws_elasticache_replication_group.main.snapshot_window
}

output "maintenance_window" {
  description = "Weekly maintenance window"
  value       = aws_elasticache_replication_group.main.maintenance_window
}

# CloudWatch Logs
output "cloudwatch_log_group_name" {
  description = "Name of the CloudWatch log group for Redis slow logs"
  value       = aws_cloudwatch_log_group.redis_slow_log.name
}

output "cloudwatch_log_group_arn" {
  description = "ARN of the CloudWatch log group for Redis slow logs"
  value       = aws_cloudwatch_log_group.redis_slow_log.arn
}

# CloudWatch Alarms
output "cloudwatch_alarm_arns" {
  description = "ARNs of CloudWatch alarms"
  value = {
    cpu_utilization = aws_cloudwatch_metric_alarm.redis_cpu.arn
    memory_usage    = aws_cloudwatch_metric_alarm.redis_memory.arn
    connections     = aws_cloudwatch_metric_alarm.redis_connections.arn
    evictions       = aws_cloudwatch_metric_alarm.redis_evictions.arn
  }
}

# Global Replication (if enabled)
output "global_replication_group_id" {
  description = "ID of the global replication group"
  value       = var.enable_global_replication ? aws_elasticache_global_replication_group.main[0].global_replication_group_id : null
}

# Connection Strings
output "connection_string" {
  description = "Redis connection string"
  value       = var.transit_encryption_enabled ?
    "rediss://${aws_elasticache_replication_group.main.primary_endpoint_address}:${aws_elasticache_replication_group.main.port}" :
    "redis://${aws_elasticache_replication_group.main.primary_endpoint_address}:${aws_elasticache_replication_group.main.port}"
  sensitive   = true
}

output "connection_string_with_auth" {
  description = "Redis connection string with auth token"
  value       = var.transit_encryption_enabled ?
    "rediss://default:${var.auth_token != null ? var.auth_token : random_password.auth_token[0].result}@${aws_elasticache_replication_group.main.primary_endpoint_address}:${aws_elasticache_replication_group.main.port}" :
    "redis://${aws_elasticache_replication_group.main.primary_endpoint_address}:${aws_elasticache_replication_group.main.port}"
  sensitive   = true
}

# Environment Variables for Application Configuration
output "redis_config_env" {
  description = "Redis configuration as environment variables"
  value = {
    REDIS_HOST     = aws_elasticache_replication_group.main.primary_endpoint_address
    REDIS_PORT     = tostring(aws_elasticache_replication_group.main.port)
    REDIS_AUTH     = var.transit_encryption_enabled ? (var.auth_token != null ? var.auth_token : random_password.auth_token[0].result) : null
    REDIS_TLS      = var.transit_encryption_enabled ? "true" : "false"
    REDIS_URL      = var.transit_encryption_enabled ?
      "rediss://${aws_elasticache_replication_group.main.primary_endpoint_address}:${aws_elasticache_replication_group.main.port}" :
      "redis://${aws_elasticache_replication_group.main.primary_endpoint_address}:${aws_elasticache_replication_group.main.port}"
  }
  sensitive = true
}

# Cluster Status
output "cluster_status" {
  description = "Status of the replication group"
  value       = aws_elasticache_replication_group.main.status
}

# Additional endpoints for read operations
output "all_endpoints" {
  description = "All available endpoints for the replication group"
  value = {
    primary       = aws_elasticache_replication_group.main.primary_endpoint_address
    reader        = aws_elasticache_replication_group.main.reader_endpoint_address
    configuration = aws_elasticache_replication_group.main.configuration_endpoint_address
  }
  sensitive = true
}