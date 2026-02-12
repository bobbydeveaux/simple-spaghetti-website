# Outputs for Monitoring Module

# Application Load Balancer
output "alb_id" {
  description = "ID of the Application Load Balancer"
  value       = aws_lb.main.id
}

output "alb_arn" {
  description = "ARN of the Application Load Balancer"
  value       = aws_lb.main.arn
}

output "alb_arn_suffix" {
  description = "ARN suffix of the Application Load Balancer (for CloudWatch metrics)"
  value       = aws_lb.main.arn_suffix
}

output "alb_dns_name" {
  description = "DNS name of the Application Load Balancer"
  value       = aws_lb.main.dns_name
}

output "alb_zone_id" {
  description = "Zone ID of the Application Load Balancer"
  value       = aws_lb.main.zone_id
}

output "alb_hosted_zone_id" {
  description = "Hosted zone ID of the Application Load Balancer"
  value       = aws_lb.main.zone_id
}

# Security Groups
output "alb_security_group_id" {
  description = "ID of the ALB security group"
  value       = aws_security_group.alb.id
}

output "alb_security_group_arn" {
  description = "ARN of the ALB security group"
  value       = aws_security_group.alb.arn
}

# Target Groups
output "api_target_group_arn" {
  description = "ARN of the API target group"
  value       = aws_lb_target_group.api.arn
}

output "api_target_group_name" {
  description = "Name of the API target group"
  value       = aws_lb_target_group.api.name
}

output "frontend_target_group_arn" {
  description = "ARN of the frontend target group"
  value       = aws_lb_target_group.frontend.arn
}

output "frontend_target_group_name" {
  description = "Name of the frontend target group"
  value       = aws_lb_target_group.frontend.name
}

# Listeners
output "http_listener_arn" {
  description = "ARN of the HTTP listener"
  value       = aws_lb_listener.http.arn
}

output "https_listener_arn" {
  description = "ARN of the HTTPS listener"
  value       = var.certificate_arn != null ? aws_lb_listener.https[0].arn : null
}

# CloudWatch Log Groups
output "cloudwatch_log_group_names" {
  description = "Names of CloudWatch log groups"
  value = {
    application = aws_cloudwatch_log_group.application.name
    api         = aws_cloudwatch_log_group.api.name
    ml_pipeline = aws_cloudwatch_log_group.ml_pipeline.name
    ingestion   = aws_cloudwatch_log_group.ingestion.name
  }
}

output "cloudwatch_log_group_arns" {
  description = "ARNs of CloudWatch log groups"
  value = {
    application = aws_cloudwatch_log_group.application.arn
    api         = aws_cloudwatch_log_group.api.arn
    ml_pipeline = aws_cloudwatch_log_group.ml_pipeline.arn
    ingestion   = aws_cloudwatch_log_group.ingestion.arn
  }
}

# CloudWatch Dashboard
output "cloudwatch_dashboard_name" {
  description = "Name of the CloudWatch dashboard"
  value       = aws_cloudwatch_dashboard.main.dashboard_name
}

output "cloudwatch_dashboard_url" {
  description = "URL to access the CloudWatch dashboard"
  value       = "https://${data.aws_region.current.name}.console.aws.amazon.com/cloudwatch/home?region=${data.aws_region.current.name}#dashboards:name=${aws_cloudwatch_dashboard.main.dashboard_name}"
}

# CloudWatch Alarms
output "cloudwatch_alarm_arns" {
  description = "ARNs of CloudWatch alarms"
  value = {
    alb_high_response_time = aws_cloudwatch_metric_alarm.alb_high_response_time.arn
    alb_high_4xx_errors    = aws_cloudwatch_metric_alarm.alb_high_4xx_errors.arn
    alb_high_5xx_errors    = aws_cloudwatch_metric_alarm.alb_high_5xx_errors.arn
    system_health          = aws_cloudwatch_composite_alarm.system_health.arn
  }
}

output "cloudwatch_alarm_names" {
  description = "Names of CloudWatch alarms"
  value = {
    alb_high_response_time = aws_cloudwatch_metric_alarm.alb_high_response_time.alarm_name
    alb_high_4xx_errors    = aws_cloudwatch_metric_alarm.alb_high_4xx_errors.alarm_name
    alb_high_5xx_errors    = aws_cloudwatch_metric_alarm.alb_high_5xx_errors.alarm_name
    system_health          = aws_cloudwatch_composite_alarm.system_health.alarm_name
  }
}

# SNS Topic (if created)
output "sns_topic_arn" {
  description = "ARN of the SNS topic for alerts"
  value       = var.create_sns_topic ? aws_sns_topic.alerts[0].arn : null
}

output "sns_topic_name" {
  description = "Name of the SNS topic for alerts"
  value       = var.create_sns_topic ? aws_sns_topic.alerts[0].name : null
}

# Custom Metrics
output "custom_metric_filters" {
  description = "Custom CloudWatch metric filters"
  value = {
    prediction_accuracy       = aws_cloudwatch_log_metric_filter.prediction_accuracy.name
    model_training_duration   = aws_cloudwatch_log_metric_filter.model_training_duration.name
    data_ingestion_records    = aws_cloudwatch_log_metric_filter.data_ingestion_records.name
  }
}

# CloudWatch Insights Queries
output "cloudwatch_insights_queries" {
  description = "CloudWatch Insights saved queries"
  value = {
    error_analysis   = aws_cloudwatch_query_definition.error_analysis.name
    api_performance  = aws_cloudwatch_query_definition.api_performance.name
  }
}

# EventBridge Rules (if created)
output "eventbridge_rule_arns" {
  description = "ARNs of EventBridge rules"
  value = var.enable_automated_training ? {
    model_training_schedule = aws_cloudwatch_event_rule.model_training_schedule[0].arn
  } : {}
}

# Load Balancer Configuration
output "load_balancer_config" {
  description = "Load balancer configuration summary"
  value = {
    name               = aws_lb.main.name
    type               = aws_lb.main.load_balancer_type
    scheme             = aws_lb.main.internal ? "internal" : "internet-facing"
    ip_address_type    = aws_lb.main.ip_address_type
    deletion_protection = aws_lb.main.enable_deletion_protection
    cross_zone_load_balancing = aws_lb.main.enable_cross_zone_load_balancing
  }
}

# Health Check Configuration
output "health_check_config" {
  description = "Health check configuration for target groups"
  value = {
    api = {
      path                = aws_lb_target_group.api.health_check[0].path
      port                = aws_lb_target_group.api.health_check[0].port
      protocol            = aws_lb_target_group.api.health_check[0].protocol
      timeout             = aws_lb_target_group.api.health_check[0].timeout
      interval            = aws_lb_target_group.api.health_check[0].interval
      healthy_threshold   = aws_lb_target_group.api.health_check[0].healthy_threshold
      unhealthy_threshold = aws_lb_target_group.api.health_check[0].unhealthy_threshold
    }
    frontend = {
      path                = aws_lb_target_group.frontend.health_check[0].path
      port                = aws_lb_target_group.frontend.health_check[0].port
      protocol            = aws_lb_target_group.frontend.health_check[0].protocol
      timeout             = aws_lb_target_group.frontend.health_check[0].timeout
      interval            = aws_lb_target_group.frontend.health_check[0].interval
      healthy_threshold   = aws_lb_target_group.frontend.health_check[0].healthy_threshold
      unhealthy_threshold = aws_lb_target_group.frontend.health_check[0].unhealthy_threshold
    }
  }
}

# Monitoring URLs
output "monitoring_urls" {
  description = "URLs for accessing monitoring resources"
  value = {
    alb_console = "https://${data.aws_region.current.name}.console.aws.amazon.com/ec2/v2/home?region=${data.aws_region.current.name}#LoadBalancers:search=${aws_lb.main.name}"
    cloudwatch_dashboard = "https://${data.aws_region.current.name}.console.aws.amazon.com/cloudwatch/home?region=${data.aws_region.current.name}#dashboards:name=${aws_cloudwatch_dashboard.main.dashboard_name}"
    cloudwatch_alarms = "https://${data.aws_region.current.name}.console.aws.amazon.com/cloudwatch/home?region=${data.aws_region.current.name}#alarmsV2:search=${var.name_prefix}"
    cloudwatch_logs = "https://${data.aws_region.current.name}.console.aws.amazon.com/cloudwatch/home?region=${data.aws_region.current.name}#logsV2:log-groups"
  }
}

# Application URLs
output "application_urls" {
  description = "URLs for accessing the application"
  value = {
    load_balancer_dns = aws_lb.main.dns_name
    http_url         = "http://${aws_lb.main.dns_name}"
    https_url        = var.certificate_arn != null ? "https://${aws_lb.main.dns_name}" : null
    api_health_check = "http://${aws_lb.main.dns_name}/api/health"
  }
}

# Metric Namespaces
output "custom_metric_namespaces" {
  description = "Custom CloudWatch metric namespaces"
  value = {
    ml_metrics        = "F1Analytics/ML"
    ingestion_metrics = "F1Analytics/Ingestion"
  }
}