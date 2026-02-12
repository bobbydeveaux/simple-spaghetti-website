# Outputs for RDS Module

# Database Instance Information
output "db_instance_id" {
  description = "RDS instance ID"
  value       = aws_db_instance.main.id
}

output "db_instance_arn" {
  description = "ARN of the RDS instance"
  value       = aws_db_instance.main.arn
}

output "db_instance_endpoint" {
  description = "RDS instance endpoint"
  value       = aws_db_instance.main.endpoint
  sensitive   = true
}

output "db_instance_hosted_zone_id" {
  description = "Hosted zone ID of the RDS instance"
  value       = aws_db_instance.main.hosted_zone_id
}

output "db_instance_port" {
  description = "RDS instance port"
  value       = aws_db_instance.main.port
}

output "db_instance_name" {
  description = "Database name"
  value       = aws_db_instance.main.db_name
}

output "db_instance_username" {
  description = "Database admin username"
  value       = aws_db_instance.main.username
  sensitive   = true
}

output "db_instance_password" {
  description = "Database admin password"
  value       = var.database_password != null ? var.database_password : random_password.database_password[0].result
  sensitive   = true
}

# Read Replicas (if created)
output "read_replica_endpoints" {
  description = "Endpoints of read replicas"
  value       = var.create_read_replica ? aws_db_instance.read_replica[*].endpoint : []
  sensitive   = true
}

output "read_replica_ids" {
  description = "IDs of read replicas"
  value       = var.create_read_replica ? aws_db_instance.read_replica[*].id : []
}

output "read_replica_arns" {
  description = "ARNs of read replicas"
  value       = var.create_read_replica ? aws_db_instance.read_replica[*].arn : []
}

# Security
output "security_group_id" {
  description = "ID of the RDS security group"
  value       = aws_security_group.rds.id
}

output "security_group_arn" {
  description = "ARN of the RDS security group"
  value       = aws_security_group.rds.arn
}

# Subnet Group
output "db_subnet_group_id" {
  description = "ID of the DB subnet group"
  value       = aws_db_subnet_group.main.id
}

output "db_subnet_group_name" {
  description = "Name of the DB subnet group"
  value       = aws_db_subnet_group.main.name
}

# Parameter and Option Groups
output "parameter_group_id" {
  description = "ID of the DB parameter group"
  value       = aws_db_parameter_group.main.id
}

output "parameter_group_name" {
  description = "Name of the DB parameter group"
  value       = aws_db_parameter_group.main.name
}

output "option_group_id" {
  description = "ID of the DB option group"
  value       = aws_db_option_group.main.id
}

output "option_group_name" {
  description = "Name of the DB option group"
  value       = aws_db_option_group.main.name
}

# Monitoring
output "enhanced_monitoring_iam_role_arn" {
  description = "ARN of the enhanced monitoring IAM role"
  value       = var.monitoring_interval > 0 ? aws_iam_role.enhanced_monitoring[0].arn : null
}

output "cloudwatch_log_groups" {
  description = "CloudWatch log groups for RDS logs"
  value = {
    postgresql = aws_cloudwatch_log_group.postgresql.name
    upgrade    = aws_cloudwatch_log_group.upgrade.name
  }
}

# CloudWatch Alarms
output "cloudwatch_alarm_arns" {
  description = "ARNs of CloudWatch alarms"
  value = {
    cpu_utilization      = aws_cloudwatch_metric_alarm.database_cpu.arn
    database_connections = aws_cloudwatch_metric_alarm.database_connections.arn
    freeable_memory     = aws_cloudwatch_metric_alarm.database_freeable_memory.arn
    free_storage_space  = aws_cloudwatch_metric_alarm.database_free_storage_space.arn
  }
}

# Connection Information
output "connection_string" {
  description = "PostgreSQL connection string"
  value       = "postgresql://${aws_db_instance.main.username}:[PASSWORD]@${aws_db_instance.main.endpoint}:${aws_db_instance.main.port}/${aws_db_instance.main.db_name}"
  sensitive   = true
}

output "jdbc_connection_string" {
  description = "JDBC connection string"
  value       = "jdbc:postgresql://${aws_db_instance.main.endpoint}:${aws_db_instance.main.port}/${aws_db_instance.main.db_name}"
  sensitive   = true
}

# Environment Variables for Application Configuration
output "database_url_env" {
  description = "Database URL in format suitable for environment variable"
  value       = "postgresql://${aws_db_instance.main.username}:${var.database_password != null ? var.database_password : random_password.database_password[0].result}@${aws_db_instance.main.endpoint}:${aws_db_instance.main.port}/${aws_db_instance.main.db_name}"
  sensitive   = true
}

output "database_config_env" {
  description = "Database configuration as environment variables"
  value = {
    DB_HOST     = aws_db_instance.main.endpoint
    DB_PORT     = tostring(aws_db_instance.main.port)
    DB_NAME     = aws_db_instance.main.db_name
    DB_USERNAME = aws_db_instance.main.username
    DB_PASSWORD = var.database_password != null ? var.database_password : random_password.database_password[0].result
  }
  sensitive = true
}

# Instance Status and Configuration
output "db_instance_status" {
  description = "RDS instance status"
  value       = aws_db_instance.main.status
}

output "db_instance_class" {
  description = "RDS instance class"
  value       = aws_db_instance.main.instance_class
}

output "db_instance_engine" {
  description = "RDS instance engine"
  value       = aws_db_instance.main.engine
}

output "db_instance_engine_version" {
  description = "RDS instance engine version"
  value       = aws_db_instance.main.engine_version
}

output "db_instance_storage_type" {
  description = "RDS instance storage type"
  value       = aws_db_instance.main.storage_type
}

output "db_instance_allocated_storage" {
  description = "RDS instance allocated storage in GB"
  value       = aws_db_instance.main.allocated_storage
}

output "db_instance_max_allocated_storage" {
  description = "RDS instance max allocated storage in GB"
  value       = aws_db_instance.main.max_allocated_storage
}

output "db_instance_multi_az" {
  description = "Whether RDS instance is Multi-AZ"
  value       = aws_db_instance.main.multi_az
}

output "db_instance_storage_encrypted" {
  description = "Whether RDS instance storage is encrypted"
  value       = aws_db_instance.main.storage_encrypted
}

# Performance and Monitoring
output "performance_insights_enabled" {
  description = "Whether Performance Insights is enabled"
  value       = aws_db_instance.main.performance_insights_enabled
}

output "monitoring_interval" {
  description = "Enhanced monitoring interval in seconds"
  value       = aws_db_instance.main.monitoring_interval
}

# Backup Configuration
output "backup_retention_period" {
  description = "Backup retention period in days"
  value       = aws_db_instance.main.backup_retention_period
}

output "backup_window" {
  description = "Daily backup window"
  value       = aws_db_instance.main.backup_window
}

output "maintenance_window" {
  description = "Weekly maintenance window"
  value       = aws_db_instance.main.maintenance_window
}