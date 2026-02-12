# Variables for S3 Module

variable "name_prefix" {
  description = "Name prefix for resources"
  type        = string
}

variable "environment" {
  description = "Environment name (dev, staging, prod)"
  type        = string
  default     = "dev"
}

# Versioning Configuration
variable "enable_versioning" {
  description = "Enable versioning on S3 buckets (except logs which always have versioning)"
  type        = bool
  default     = true
}

# Encryption Configuration
variable "kms_key_id" {
  description = "KMS key ID for S3 bucket encryption (if null, uses AWS managed encryption)"
  type        = string
  default     = null
}

# Terraform State Bucket
variable "create_terraform_state_bucket" {
  description = "Create S3 bucket for Terraform state storage"
  type        = bool
  default     = false
}

# Lifecycle Management
variable "backup_retention_days" {
  description = "Number of days to retain backup files"
  type        = number
  default     = 2555 # ~7 years

  validation {
    condition     = var.backup_retention_days > 0 && var.backup_retention_days <= 3650
    error_message = "Backup retention days must be between 1 and 3650 (10 years)."
  }
}

variable "log_retention_days" {
  description = "Number of days to retain log files"
  type        = number
  default     = 365 # 1 year

  validation {
    condition     = var.log_retention_days > 0 && var.log_retention_days <= 2555
    error_message = "Log retention days must be between 1 and 2555 (7 years)."
  }
}

# Access Control
variable "eks_node_role_arns" {
  description = "List of EKS node group IAM role ARNs that need access to model storage"
  type        = list(string)
  default     = []
}

variable "rds_backup_role_arns" {
  description = "List of RDS backup IAM role ARNs that need access to data backup bucket"
  type        = list(string)
  default     = []
}

# Notifications
variable "enable_model_notifications" {
  description = "Enable S3 bucket notifications for model storage"
  type        = bool
  default     = false
}

variable "notification_lambda_arns" {
  description = "List of Lambda function ARNs to notify on model upload"
  type        = list(string)
  default     = []
}

variable "notification_sns_topics" {
  description = "List of SNS topic ARNs to notify on model upload"
  type        = list(string)
  default     = []
}

# Monitoring
variable "enable_cloudwatch_metrics" {
  description = "Enable CloudWatch metrics and alarms for S3 buckets"
  type        = bool
  default     = true
}

variable "model_storage_size_threshold" {
  description = "Threshold in bytes for model storage size alarm"
  type        = number
  default     = 107374182400 # 100GB

  validation {
    condition     = var.model_storage_size_threshold > 0
    error_message = "Model storage size threshold must be greater than 0."
  }
}

variable "alarm_actions" {
  description = "List of ARNs to notify when CloudWatch alarms trigger"
  type        = list(string)
  default     = []
}

# CORS Configuration
variable "enable_cors" {
  description = "Enable CORS configuration for buckets"
  type        = bool
  default     = false
}

variable "cors_allowed_origins" {
  description = "List of allowed origins for CORS"
  type        = list(string)
  default     = ["*"]
}

variable "cors_allowed_methods" {
  description = "List of allowed HTTP methods for CORS"
  type        = list(string)
  default     = ["GET", "PUT", "POST", "DELETE", "HEAD"]
}

variable "cors_allowed_headers" {
  description = "List of allowed headers for CORS"
  type        = list(string)
  default     = ["*"]
}

variable "cors_max_age_seconds" {
  description = "Time in seconds that browser can cache the response for a preflight request"
  type        = number
  default     = 3000
}

# Transfer Acceleration
variable "enable_transfer_acceleration" {
  description = "Enable S3 Transfer Acceleration for faster uploads"
  type        = bool
  default     = false
}

# Request Payer
variable "request_payer" {
  description = "Who pays for requests (BucketOwner or Requester)"
  type        = string
  default     = "BucketOwner"

  validation {
    condition     = contains(["BucketOwner", "Requester"], var.request_payer)
    error_message = "Request payer must be either BucketOwner or Requester."
  }
}

# Replication (for cross-region backup)
variable "enable_replication" {
  description = "Enable cross-region replication for backup bucket"
  type        = bool
  default     = false
}

variable "replication_destination_bucket_arn" {
  description = "ARN of destination bucket for replication"
  type        = string
  default     = null
}

variable "replication_role_arn" {
  description = "IAM role ARN for S3 replication"
  type        = string
  default     = null
}

# Intelligent Tiering
variable "enable_intelligent_tiering" {
  description = "Enable S3 Intelligent Tiering for cost optimization"
  type        = bool
  default     = true
}

variable "intelligent_tiering_prefix" {
  description = "Prefix for objects to include in Intelligent Tiering"
  type        = string
  default     = ""
}

variable "tags" {
  description = "Additional tags to apply to resources"
  type        = map(string)
  default     = {}
}