# ElastiCache Redis Module for F1 Prediction Analytics Infrastructure
# Creates ElastiCache Redis cluster with replication for caching and session management

# Security Group for ElastiCache
resource "aws_security_group" "redis" {
  name        = "${var.name_prefix}-redis-sg"
  description = "Security group for ElastiCache Redis cluster"
  vpc_id      = var.vpc_id

  ingress {
    description = "Redis access from VPC"
    from_port   = 6379
    to_port     = 6379
    protocol    = "tcp"
    cidr_blocks = var.allowed_cidr_blocks
  }

  egress {
    description = "All outbound traffic"
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }

  tags = merge(var.tags, {
    Name = "${var.name_prefix}-redis-sg"
  })
}

# ElastiCache Subnet Group
resource "aws_elasticache_subnet_group" "main" {
  name       = "${var.name_prefix}-redis-subnet-group"
  subnet_ids = var.subnet_ids

  tags = merge(var.tags, {
    Name = "${var.name_prefix}-redis-subnet-group"
  })
}

# Parameter Group for Redis optimization
resource "aws_elasticache_parameter_group" "main" {
  family = "redis7.x"
  name   = "${var.name_prefix}-redis-params"

  # Memory and performance optimizations
  parameter {
    name  = "maxmemory-policy"
    value = var.maxmemory_policy
  }

  parameter {
    name  = "timeout"
    value = "300"
  }

  parameter {
    name  = "tcp-keepalive"
    value = "300"
  }

  parameter {
    name  = "maxmemory-samples"
    value = "5"
  }

  # Enable keyspace notifications for pub/sub
  parameter {
    name  = "notify-keyspace-events"
    value = "Ex"
  }

  # Slow log configuration
  parameter {
    name  = "slowlog-log-slower-than"
    value = "10000" # 10ms
  }

  parameter {
    name  = "slowlog-max-len"
    value = "128"
  }

  tags = merge(var.tags, {
    Name = "${var.name_prefix}-redis-params"
  })
}

# ElastiCache Replication Group (Redis with replication)
resource "aws_elasticache_replication_group" "main" {
  replication_group_id       = "${var.name_prefix}-redis"
  description                = "Redis cluster for F1 Analytics application"

  # Node configuration
  node_type                  = var.node_type
  port                      = 6379
  parameter_group_name      = aws_elasticache_parameter_group.main.name

  # Cluster configuration
  num_cache_clusters        = var.num_cache_clusters
  replicas_per_node_group   = var.replicas_per_node_group

  # Network configuration
  subnet_group_name         = aws_elasticache_subnet_group.main.name
  security_group_ids        = [aws_security_group.redis.id]

  # Engine configuration
  engine                    = "redis"
  engine_version           = var.engine_version

  # Security and encryption
  at_rest_encryption_enabled = var.at_rest_encryption_enabled
  transit_encryption_enabled = var.transit_encryption_enabled
  auth_token_update_strategy = var.transit_encryption_enabled ? "ROTATE" : null
  auth_token                 = var.transit_encryption_enabled ? var.auth_token : null

  # Backup configuration
  snapshot_retention_limit = var.snapshot_retention_limit
  snapshot_window         = var.snapshot_window

  # Maintenance
  maintenance_window      = var.maintenance_window
  notification_topic_arn  = var.notification_topic_arn

  # High availability
  automatic_failover_enabled = var.automatic_failover_enabled
  multi_az_enabled          = var.multi_az_enabled

  # Logging
  log_delivery_configuration {
    destination      = aws_cloudwatch_log_group.redis_slow_log.name
    destination_type = "cloudwatch-logs"
    log_format      = "text"
    log_type        = "slow-log"
  }

  tags = merge(var.tags, {
    Name = "${var.name_prefix}-redis"
  })

  depends_on = [
    aws_elasticache_subnet_group.main,
    aws_elasticache_parameter_group.main
  ]
}

# CloudWatch Log Group for Redis slow log
resource "aws_cloudwatch_log_group" "redis_slow_log" {
  name              = "/aws/elasticache/redis/${var.name_prefix}/slow-log"
  retention_in_days = var.log_retention_days

  tags = merge(var.tags, {
    Name = "${var.name_prefix}-redis-slow-log"
  })
}

# Random auth token generation (if encryption in transit is enabled)
resource "random_password" "auth_token" {
  count = var.transit_encryption_enabled && var.auth_token == null ? 1 : 0

  length  = 32
  special = false # Redis auth tokens cannot contain special characters
}

# CloudWatch Alarms for monitoring
resource "aws_cloudwatch_metric_alarm" "redis_cpu" {
  alarm_name          = "${var.name_prefix}-redis-high-cpu"
  comparison_operator = "GreaterThanThreshold"
  evaluation_periods  = "2"
  metric_name         = "CPUUtilization"
  namespace           = "AWS/ElastiCache"
  period              = "120"
  statistic           = "Average"
  threshold           = "75"
  alarm_description   = "This metric monitors Redis CPU utilization"
  alarm_actions       = var.alarm_actions

  dimensions = {
    CacheClusterId = aws_elasticache_replication_group.main.configuration_endpoint_address != null ?
      aws_elasticache_replication_group.main.configuration_endpoint_address :
      aws_elasticache_replication_group.main.primary_endpoint_address
  }

  tags = var.tags
}

resource "aws_cloudwatch_metric_alarm" "redis_memory" {
  alarm_name          = "${var.name_prefix}-redis-high-memory"
  comparison_operator = "GreaterThanThreshold"
  evaluation_periods  = "2"
  metric_name         = "DatabaseMemoryUsagePercentage"
  namespace           = "AWS/ElastiCache"
  period              = "120"
  statistic           = "Average"
  threshold           = "80"
  alarm_description   = "This metric monitors Redis memory usage"
  alarm_actions       = var.alarm_actions

  dimensions = {
    CacheClusterId = aws_elasticache_replication_group.main.configuration_endpoint_address != null ?
      aws_elasticache_replication_group.main.configuration_endpoint_address :
      aws_elasticache_replication_group.main.primary_endpoint_address
  }

  tags = var.tags
}

resource "aws_cloudwatch_metric_alarm" "redis_connections" {
  alarm_name          = "${var.name_prefix}-redis-high-connections"
  comparison_operator = "GreaterThanThreshold"
  evaluation_periods  = "2"
  metric_name         = "CurrConnections"
  namespace           = "AWS/ElastiCache"
  period              = "120"
  statistic           = "Average"
  threshold           = var.connection_threshold
  alarm_description   = "This metric monitors Redis connection count"
  alarm_actions       = var.alarm_actions

  dimensions = {
    CacheClusterId = aws_elasticache_replication_group.main.configuration_endpoint_address != null ?
      aws_elasticache_replication_group.main.configuration_endpoint_address :
      aws_elasticache_replication_group.main.primary_endpoint_address
  }

  tags = var.tags
}

resource "aws_cloudwatch_metric_alarm" "redis_evictions" {
  alarm_name          = "${var.name_prefix}-redis-evictions"
  comparison_operator = "GreaterThanThreshold"
  evaluation_periods  = "2"
  metric_name         = "Evictions"
  namespace           = "AWS/ElastiCache"
  period              = "300"
  statistic           = "Sum"
  threshold           = "0"
  alarm_description   = "This metric monitors Redis evictions"
  alarm_actions       = var.alarm_actions

  dimensions = {
    CacheClusterId = aws_elasticache_replication_group.main.configuration_endpoint_address != null ?
      aws_elasticache_replication_group.main.configuration_endpoint_address :
      aws_elasticache_replication_group.main.primary_endpoint_address
  }

  tags = var.tags
}

# User and User Group for Redis authentication (if using Redis 6.0+)
resource "aws_elasticache_user" "default" {
  count = var.create_redis_user && var.transit_encryption_enabled ? 1 : 0

  user_id       = "${var.name_prefix}-redis-user"
  user_name     = var.redis_username
  access_string = "on ~* &* +@all"
  engine        = "REDIS"
  passwords     = [var.auth_token != null ? var.auth_token : random_password.auth_token[0].result]

  tags = var.tags
}

resource "aws_elasticache_user_group" "main" {
  count = var.create_redis_user && var.transit_encryption_enabled ? 1 : 0

  engine          = "REDIS"
  user_group_id   = "${var.name_prefix}-redis-group"
  user_ids        = ["default", aws_elasticache_user.default[0].user_id]

  tags = var.tags
}

# Global replication group (for cross-region replication if needed)
resource "aws_elasticache_global_replication_group" "main" {
  count = var.enable_global_replication ? 1 : 0

  global_replication_group_id_suffix = var.name_prefix
  description                        = "Global replication group for F1 Analytics Redis"
  primary_replication_group_id       = aws_elasticache_replication_group.main.id

  tags = var.tags
}