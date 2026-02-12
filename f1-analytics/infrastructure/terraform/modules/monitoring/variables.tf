# Variables for Monitoring Module

variable "name_prefix" {
  description = "Name prefix for resources"
  type        = string
}

variable "cluster_name" {
  description = "Name of the EKS cluster for monitoring"
  type        = string
}

variable "vpc_id" {
  description = "VPC ID where monitoring resources will be created"
  type        = string
}

variable "subnet_ids" {
  description = "List of subnet IDs for the Application Load Balancer"
  type        = list(string)

  validation {
    condition     = length(var.subnet_ids) >= 2
    error_message = "At least 2 subnet IDs must be provided for high availability."
  }
}

# Load Balancer Configuration
variable "enable_deletion_protection" {
  description = "Enable deletion protection for the ALB"
  type        = bool
  default     = true
}

variable "certificate_arn" {
  description = "ARN of the SSL certificate for HTTPS listener (if null, HTTPS listener won't be created)"
  type        = string
  default     = null
}

variable "access_logs_bucket" {
  description = "S3 bucket name for ALB access logs (if null, access logs won't be enabled)"
  type        = string
  default     = null
}

# CloudWatch Configuration
variable "log_retention_days" {
  description = "CloudWatch logs retention period in days"
  type        = number
  default     = 30

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

# SNS Configuration
variable "create_sns_topic" {
  description = "Create SNS topic for alerts"
  type        = bool
  default     = false
}

variable "alert_email_addresses" {
  description = "List of email addresses to receive alerts"
  type        = list(string)
  default     = []

  validation {
    condition = alltrue([
      for email in var.alert_email_addresses :
      can(regex("^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\\.[a-zA-Z]{2,}$", email))
    ])
    error_message = "All email addresses must be valid."
  }
}

# Custom Metrics Configuration
variable "enable_custom_metrics" {
  description = "Enable custom metrics for ML pipeline and data ingestion"
  type        = bool
  default     = true
}

# Dashboard Configuration
variable "enable_dashboard" {
  description = "Create CloudWatch dashboard"
  type        = bool
  default     = true
}

# Automation Configuration
variable "enable_automated_training" {
  description = "Enable automated model training schedule"
  type        = bool
  default     = false
}

variable "model_training_lambda_arn" {
  description = "ARN of the Lambda function for model training (required if automated training is enabled)"
  type        = string
  default     = null
}

variable "training_schedule_expression" {
  description = "Cron expression for automated training schedule"
  type        = string
  default     = "cron(0 6 ? * MON *)" # Every Monday at 6 AM UTC

  validation {
    condition     = can(regex("^cron\\(", var.training_schedule_expression))
    error_message = "Training schedule expression must be a valid cron expression."
  }
}

# Health Check Configuration
variable "api_health_check_path" {
  description = "Health check path for API target group"
  type        = string
  default     = "/health"
}

variable "frontend_health_check_path" {
  description = "Health check path for frontend target group"
  type        = string
  default     = "/"
}

variable "health_check_timeout" {
  description = "Health check timeout in seconds"
  type        = number
  default     = 5

  validation {
    condition     = var.health_check_timeout >= 2 && var.health_check_timeout <= 120
    error_message = "Health check timeout must be between 2 and 120 seconds."
  }
}

variable "health_check_interval" {
  description = "Health check interval in seconds"
  type        = number
  default     = 30

  validation {
    condition     = var.health_check_interval >= 5 && var.health_check_interval <= 300
    error_message = "Health check interval must be between 5 and 300 seconds."
  }
}

variable "healthy_threshold" {
  description = "Number of consecutive successful health checks to consider target healthy"
  type        = number
  default     = 2

  validation {
    condition     = var.healthy_threshold >= 2 && var.healthy_threshold <= 10
    error_message = "Healthy threshold must be between 2 and 10."
  }
}

variable "unhealthy_threshold" {
  description = "Number of consecutive failed health checks to consider target unhealthy"
  type        = number
  default     = 3

  validation {
    condition     = var.unhealthy_threshold >= 2 && var.unhealthy_threshold <= 10
    error_message = "Unhealthy threshold must be between 2 and 10."
  }
}

# Alarm Thresholds
variable "response_time_threshold" {
  description = "Response time threshold in seconds for ALB alarm"
  type        = number
  default     = 2.0

  validation {
    condition     = var.response_time_threshold > 0
    error_message = "Response time threshold must be greater than 0."
  }
}

variable "error_4xx_threshold" {
  description = "Threshold for 4XX errors count alarm"
  type        = number
  default     = 50

  validation {
    condition     = var.error_4xx_threshold > 0
    error_message = "4XX error threshold must be greater than 0."
  }
}

variable "error_5xx_threshold" {
  description = "Threshold for 5XX errors count alarm"
  type        = number
  default     = 10

  validation {
    condition     = var.error_5xx_threshold > 0
    error_message = "5XX error threshold must be greater than 0."
  }
}

# Security Configuration
variable "enable_waf" {
  description = "Enable AWS WAF for the Application Load Balancer"
  type        = bool
  default     = false
}

variable "waf_web_acl_arn" {
  description = "ARN of the WAF Web ACL to associate with the ALB"
  type        = string
  default     = null
}

# Performance Configuration
variable "enable_stickiness" {
  description = "Enable session stickiness for target groups"
  type        = bool
  default     = false
}

variable "stickiness_duration" {
  description = "Duration of session stickiness in seconds"
  type        = number
  default     = 86400 # 24 hours

  validation {
    condition     = var.stickiness_duration >= 1 && var.stickiness_duration <= 604800
    error_message = "Stickiness duration must be between 1 and 604800 seconds (7 days)."
  }
}

# Cross-Zone Load Balancing
variable "enable_cross_zone_load_balancing" {
  description = "Enable cross-zone load balancing"
  type        = bool
  default     = true
}

# HTTP/2 Configuration
variable "enable_http2" {
  description = "Enable HTTP/2 on the load balancer"
  type        = bool
  default     = true
}

# Access Logs Configuration
variable "access_logs_prefix" {
  description = "S3 prefix for ALB access logs"
  type        = string
  default     = "alb-logs"
}

variable "tags" {
  description = "Additional tags to apply to resources"
  type        = map(string)
  default     = {}
}