# Outputs for S3 Module

# Model Storage Bucket
output "model_storage_bucket_id" {
  description = "ID of the model storage bucket"
  value       = aws_s3_bucket.model_storage.id
}

output "model_storage_bucket_name" {
  description = "Name of the model storage bucket"
  value       = aws_s3_bucket.model_storage.bucket
}

output "model_storage_bucket_arn" {
  description = "ARN of the model storage bucket"
  value       = aws_s3_bucket.model_storage.arn
}

output "model_storage_bucket_domain_name" {
  description = "Domain name of the model storage bucket"
  value       = aws_s3_bucket.model_storage.bucket_domain_name
}

output "model_storage_bucket_regional_domain_name" {
  description = "Regional domain name of the model storage bucket"
  value       = aws_s3_bucket.model_storage.bucket_regional_domain_name
}

# Data Backup Bucket
output "data_backup_bucket_id" {
  description = "ID of the data backup bucket"
  value       = aws_s3_bucket.data_backup.id
}

output "data_backup_bucket_name" {
  description = "Name of the data backup bucket"
  value       = aws_s3_bucket.data_backup.bucket
}

output "data_backup_bucket_arn" {
  description = "ARN of the data backup bucket"
  value       = aws_s3_bucket.data_backup.arn
}

output "data_backup_bucket_domain_name" {
  description = "Domain name of the data backup bucket"
  value       = aws_s3_bucket.data_backup.bucket_domain_name
}

output "data_backup_bucket_regional_domain_name" {
  description = "Regional domain name of the data backup bucket"
  value       = aws_s3_bucket.data_backup.bucket_regional_domain_name
}

# Logs Bucket
output "logs_bucket_id" {
  description = "ID of the logs bucket"
  value       = aws_s3_bucket.logs.id
}

output "logs_bucket_name" {
  description = "Name of the logs bucket"
  value       = aws_s3_bucket.logs.bucket
}

output "logs_bucket_arn" {
  description = "ARN of the logs bucket"
  value       = aws_s3_bucket.logs.arn
}

output "logs_bucket_domain_name" {
  description = "Domain name of the logs bucket"
  value       = aws_s3_bucket.logs.bucket_domain_name
}

output "logs_bucket_regional_domain_name" {
  description = "Regional domain name of the logs bucket"
  value       = aws_s3_bucket.logs.bucket_regional_domain_name
}

# Terraform State Bucket (if created)
output "terraform_state_bucket_id" {
  description = "ID of the Terraform state bucket"
  value       = var.create_terraform_state_bucket ? aws_s3_bucket.terraform_state[0].id : null
}

output "terraform_state_bucket_name" {
  description = "Name of the Terraform state bucket"
  value       = var.create_terraform_state_bucket ? aws_s3_bucket.terraform_state[0].bucket : null
}

output "terraform_state_bucket_arn" {
  description = "ARN of the Terraform state bucket"
  value       = var.create_terraform_state_bucket ? aws_s3_bucket.terraform_state[0].arn : null
}

# All Bucket Names (for convenience)
output "all_bucket_names" {
  description = "List of all S3 bucket names created"
  value = compact([
    aws_s3_bucket.model_storage.bucket,
    aws_s3_bucket.data_backup.bucket,
    aws_s3_bucket.logs.bucket,
    var.create_terraform_state_bucket ? aws_s3_bucket.terraform_state[0].bucket : null
  ])
}

output "all_bucket_arns" {
  description = "List of all S3 bucket ARNs created"
  value = compact([
    aws_s3_bucket.model_storage.arn,
    aws_s3_bucket.data_backup.arn,
    aws_s3_bucket.logs.arn,
    var.create_terraform_state_bucket ? aws_s3_bucket.terraform_state[0].arn : null
  ])
}

# Environment Variables for Application Configuration
output "s3_config_env" {
  description = "S3 configuration as environment variables"
  value = {
    S3_MODEL_BUCKET   = aws_s3_bucket.model_storage.bucket
    S3_BACKUP_BUCKET  = aws_s3_bucket.data_backup.bucket
    S3_LOGS_BUCKET    = aws_s3_bucket.logs.bucket
    S3_REGION         = aws_s3_bucket.model_storage.region
  }
}

# Bucket URLs
output "model_storage_s3_url" {
  description = "S3 URL for model storage bucket"
  value       = "s3://${aws_s3_bucket.model_storage.bucket}"
}

output "data_backup_s3_url" {
  description = "S3 URL for data backup bucket"
  value       = "s3://${aws_s3_bucket.data_backup.bucket}"
}

output "logs_s3_url" {
  description = "S3 URL for logs bucket"
  value       = "s3://${aws_s3_bucket.logs.bucket}"
}

# HTTPS URLs
output "model_storage_https_url" {
  description = "HTTPS URL for model storage bucket"
  value       = "https://${aws_s3_bucket.model_storage.bucket_regional_domain_name}"
}

output "data_backup_https_url" {
  description = "HTTPS URL for data backup bucket"
  value       = "https://${aws_s3_bucket.data_backup.bucket_regional_domain_name}"
}

output "logs_https_url" {
  description = "HTTPS URL for logs bucket"
  value       = "https://${aws_s3_bucket.logs.bucket_regional_domain_name}"
}

# Bucket Regions
output "bucket_region" {
  description = "AWS region where buckets are created"
  value       = aws_s3_bucket.model_storage.region
}

# Versioning Status
output "versioning_status" {
  description = "Versioning status for each bucket"
  value = {
    model_storage = aws_s3_bucket_versioning.model_storage.versioning_configuration[0].status
    data_backup   = aws_s3_bucket_versioning.data_backup.versioning_configuration[0].status
    logs          = aws_s3_bucket_versioning.logs.versioning_configuration[0].status
    terraform_state = var.create_terraform_state_bucket ? aws_s3_bucket_versioning.terraform_state[0].versioning_configuration[0].status : null
  }
}

# Encryption Status
output "encryption_status" {
  description = "Encryption configuration for each bucket"
  value = {
    model_storage = {
      algorithm = aws_s3_bucket_server_side_encryption_configuration.model_storage.rule[0].apply_server_side_encryption_by_default[0].sse_algorithm
      kms_key   = aws_s3_bucket_server_side_encryption_configuration.model_storage.rule[0].apply_server_side_encryption_by_default[0].kms_master_key_id
    }
    data_backup = {
      algorithm = aws_s3_bucket_server_side_encryption_configuration.data_backup.rule[0].apply_server_side_encryption_by_default[0].sse_algorithm
      kms_key   = aws_s3_bucket_server_side_encryption_configuration.data_backup.rule[0].apply_server_side_encryption_by_default[0].kms_master_key_id
    }
    logs = {
      algorithm = aws_s3_bucket_server_side_encryption_configuration.logs.rule[0].apply_server_side_encryption_by_default[0].sse_algorithm
      kms_key   = aws_s3_bucket_server_side_encryption_configuration.logs.rule[0].apply_server_side_encryption_by_default[0].kms_master_key_id
    }
  }
}

# CloudWatch Alarm ARNs (if created)
output "cloudwatch_alarm_arns" {
  description = "ARNs of CloudWatch alarms created"
  value = var.enable_cloudwatch_metrics ? {
    model_storage_size = aws_cloudwatch_metric_alarm.model_storage_size[0].arn
  } : {}
}

# Lifecycle Configuration Summary
output "lifecycle_policies" {
  description = "Summary of lifecycle policies applied to buckets"
  value = {
    model_storage = {
      standard_to_ia_days = 30
      ia_to_glacier_days  = 90
      glacier_to_deep_archive_days = 365
      noncurrent_version_expiration_days = 730
    }
    data_backup = {
      standard_to_ia_days = 7
      ia_to_glacier_days  = 30
      glacier_to_deep_archive_days = 90
      expiration_days = var.backup_retention_days
      noncurrent_version_expiration_days = 90
    }
    logs = {
      standard_to_ia_days = 7
      ia_to_glacier_days  = 30
      expiration_days     = var.log_retention_days
      noncurrent_version_expiration_days = 30
    }
  }
}

# Random suffix used for bucket naming
output "bucket_suffix" {
  description = "Random suffix used for bucket naming"
  value       = local.bucket_suffix
}