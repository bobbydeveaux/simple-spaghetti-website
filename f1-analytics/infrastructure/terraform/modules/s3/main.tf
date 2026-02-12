# S3 Module for F1 Prediction Analytics Infrastructure
# Creates S3 buckets for ML model storage, data backups, and application logs

# Random suffix for bucket names to ensure uniqueness
resource "random_id" "bucket_suffix" {
  byte_length = 8
}

locals {
  bucket_suffix = lower(random_id.bucket_suffix.hex)
}

# S3 Bucket for ML Model Storage
resource "aws_s3_bucket" "model_storage" {
  bucket = "${var.name_prefix}-ml-models-${local.bucket_suffix}"

  tags = merge(var.tags, {
    Name        = "${var.name_prefix}-ml-models"
    Type        = "model-storage"
    Environment = var.environment
  })
}

# S3 Bucket for Data Backups
resource "aws_s3_bucket" "data_backup" {
  bucket = "${var.name_prefix}-data-backup-${local.bucket_suffix}"

  tags = merge(var.tags, {
    Name        = "${var.name_prefix}-data-backup"
    Type        = "data-backup"
    Environment = var.environment
  })
}

# S3 Bucket for Application Logs
resource "aws_s3_bucket" "logs" {
  bucket = "${var.name_prefix}-logs-${local.bucket_suffix}"

  tags = merge(var.tags, {
    Name        = "${var.name_prefix}-logs"
    Type        = "logs"
    Environment = var.environment
  })
}

# S3 Bucket for Terraform State (optional)
resource "aws_s3_bucket" "terraform_state" {
  count = var.create_terraform_state_bucket ? 1 : 0

  bucket = "${var.name_prefix}-terraform-state-${local.bucket_suffix}"

  tags = merge(var.tags, {
    Name        = "${var.name_prefix}-terraform-state"
    Type        = "terraform-state"
    Environment = var.environment
  })
}

# Versioning Configuration
resource "aws_s3_bucket_versioning" "model_storage" {
  bucket = aws_s3_bucket.model_storage.id
  versioning_configuration {
    status = var.enable_versioning ? "Enabled" : "Disabled"
  }
}

resource "aws_s3_bucket_versioning" "data_backup" {
  bucket = aws_s3_bucket.data_backup.id
  versioning_configuration {
    status = var.enable_versioning ? "Enabled" : "Disabled"
  }
}

resource "aws_s3_bucket_versioning" "logs" {
  bucket = aws_s3_bucket.logs.id
  versioning_configuration {
    status = "Enabled" # Always enable versioning for logs
  }
}

resource "aws_s3_bucket_versioning" "terraform_state" {
  count = var.create_terraform_state_bucket ? 1 : 0

  bucket = aws_s3_bucket.terraform_state[0].id
  versioning_configuration {
    status = "Enabled" # Always enable versioning for Terraform state
  }
}

# Server-Side Encryption Configuration
resource "aws_s3_bucket_server_side_encryption_configuration" "model_storage" {
  bucket = aws_s3_bucket.model_storage.id

  rule {
    apply_server_side_encryption_by_default {
      sse_algorithm     = var.kms_key_id != null ? "aws:kms" : "AES256"
      kms_master_key_id = var.kms_key_id
    }
    bucket_key_enabled = var.kms_key_id != null
  }
}

resource "aws_s3_bucket_server_side_encryption_configuration" "data_backup" {
  bucket = aws_s3_bucket.data_backup.id

  rule {
    apply_server_side_encryption_by_default {
      sse_algorithm     = var.kms_key_id != null ? "aws:kms" : "AES256"
      kms_master_key_id = var.kms_key_id
    }
    bucket_key_enabled = var.kms_key_id != null
  }
}

resource "aws_s3_bucket_server_side_encryption_configuration" "logs" {
  bucket = aws_s3_bucket.logs.id

  rule {
    apply_server_side_encryption_by_default {
      sse_algorithm     = var.kms_key_id != null ? "aws:kms" : "AES256"
      kms_master_key_id = var.kms_key_id
    }
    bucket_key_enabled = var.kms_key_id != null
  }
}

resource "aws_s3_bucket_server_side_encryption_configuration" "terraform_state" {
  count = var.create_terraform_state_bucket ? 1 : 0

  bucket = aws_s3_bucket.terraform_state[0].id

  rule {
    apply_server_side_encryption_by_default {
      sse_algorithm     = "AES256"
    }
  }
}

# Block Public Access
resource "aws_s3_bucket_public_access_block" "model_storage" {
  bucket = aws_s3_bucket.model_storage.id

  block_public_acls       = true
  block_public_policy     = true
  ignore_public_acls      = true
  restrict_public_buckets = true
}

resource "aws_s3_bucket_public_access_block" "data_backup" {
  bucket = aws_s3_bucket.data_backup.id

  block_public_acls       = true
  block_public_policy     = true
  ignore_public_acls      = true
  restrict_public_buckets = true
}

resource "aws_s3_bucket_public_access_block" "logs" {
  bucket = aws_s3_bucket.logs.id

  block_public_acls       = true
  block_public_policy     = true
  ignore_public_acls      = true
  restrict_public_buckets = true
}

resource "aws_s3_bucket_public_access_block" "terraform_state" {
  count = var.create_terraform_state_bucket ? 1 : 0

  bucket = aws_s3_bucket.terraform_state[0].id

  block_public_acls       = true
  block_public_policy     = true
  ignore_public_acls      = true
  restrict_public_buckets = true
}

# Lifecycle Configuration
resource "aws_s3_bucket_lifecycle_configuration" "model_storage" {
  depends_on = [aws_s3_bucket_versioning.model_storage]
  bucket     = aws_s3_bucket.model_storage.id

  rule {
    id     = "ml_model_lifecycle"
    status = "Enabled"

    # Keep current version in Standard for 30 days, then move to Standard-IA
    transition {
      days          = 30
      storage_class = "STANDARD_IA"
    }

    # Move to Glacier after 90 days
    transition {
      days          = 90
      storage_class = "GLACIER"
    }

    # Move to Deep Archive after 365 days
    transition {
      days          = 365
      storage_class = "DEEP_ARCHIVE"
    }

    # Delete old versions after 2 years
    noncurrent_version_expiration {
      noncurrent_days = 730
    }

    # Clean up incomplete multipart uploads
    abort_incomplete_multipart_upload {
      days_after_initiation = 7
    }
  }
}

resource "aws_s3_bucket_lifecycle_configuration" "data_backup" {
  depends_on = [aws_s3_bucket_versioning.data_backup]
  bucket     = aws_s3_bucket.data_backup.id

  rule {
    id     = "backup_lifecycle"
    status = "Enabled"

    # Keep current version in Standard for 7 days, then move to Standard-IA
    transition {
      days          = 7
      storage_class = "STANDARD_IA"
    }

    # Move to Glacier after 30 days
    transition {
      days          = 30
      storage_class = "GLACIER"
    }

    # Move to Deep Archive after 90 days
    transition {
      days          = 90
      storage_class = "DEEP_ARCHIVE"
    }

    # Keep backups for specified retention period
    expiration {
      days = var.backup_retention_days
    }

    # Delete old versions after 90 days
    noncurrent_version_expiration {
      noncurrent_days = 90
    }

    # Clean up incomplete multipart uploads
    abort_incomplete_multipart_upload {
      days_after_initiation = 1
    }
  }
}

resource "aws_s3_bucket_lifecycle_configuration" "logs" {
  depends_on = [aws_s3_bucket_versioning.logs]
  bucket     = aws_s3_bucket.logs.id

  rule {
    id     = "log_lifecycle"
    status = "Enabled"

    # Keep logs in Standard for 7 days, then move to Standard-IA
    transition {
      days          = 7
      storage_class = "STANDARD_IA"
    }

    # Move to Glacier after 30 days
    transition {
      days          = 30
      storage_class = "GLACIER"
    }

    # Delete logs after retention period
    expiration {
      days = var.log_retention_days
    }

    # Delete old versions after 30 days
    noncurrent_version_expiration {
      noncurrent_days = 30
    }

    # Clean up incomplete multipart uploads
    abort_incomplete_multipart_upload {
      days_after_initiation = 1
    }
  }
}

# Bucket Policies
data "aws_iam_policy_document" "model_storage_policy" {
  # Deny insecure connections
  statement {
    sid    = "DenyInsecureConnections"
    effect = "Deny"

    principals {
      type        = "*"
      identifiers = ["*"]
    }

    actions = ["s3:*"]

    resources = [
      aws_s3_bucket.model_storage.arn,
      "${aws_s3_bucket.model_storage.arn}/*",
    ]

    condition {
      test     = "Bool"
      variable = "aws:SecureTransport"
      values   = ["false"]
    }
  }

  # Allow EKS nodes to read/write ML models
  statement {
    sid    = "AllowEKSAccess"
    effect = "Allow"

    principals {
      type        = "AWS"
      identifiers = var.eks_node_role_arns
    }

    actions = [
      "s3:GetObject",
      "s3:PutObject",
      "s3:DeleteObject",
      "s3:ListBucket"
    ]

    resources = [
      aws_s3_bucket.model_storage.arn,
      "${aws_s3_bucket.model_storage.arn}/*",
    ]
  }
}

data "aws_iam_policy_document" "data_backup_policy" {
  # Deny insecure connections
  statement {
    sid    = "DenyInsecureConnections"
    effect = "Deny"

    principals {
      type        = "*"
      identifiers = ["*"]
    }

    actions = ["s3:*"]

    resources = [
      aws_s3_bucket.data_backup.arn,
      "${aws_s3_bucket.data_backup.arn}/*",
    ]

    condition {
      test     = "Bool"
      variable = "aws:SecureTransport"
      values   = ["false"]
    }
  }

  # Allow RDS backup access
  statement {
    sid    = "AllowRDSBackupAccess"
    effect = "Allow"

    principals {
      type        = "AWS"
      identifiers = var.rds_backup_role_arns
    }

    actions = [
      "s3:GetObject",
      "s3:PutObject",
      "s3:ListBucket"
    ]

    resources = [
      aws_s3_bucket.data_backup.arn,
      "${aws_s3_bucket.data_backup.arn}/*",
    ]
  }
}

# Apply bucket policies
resource "aws_s3_bucket_policy" "model_storage" {
  bucket = aws_s3_bucket.model_storage.id
  policy = data.aws_iam_policy_document.model_storage_policy.json
}

resource "aws_s3_bucket_policy" "data_backup" {
  bucket = aws_s3_bucket.data_backup.id
  policy = data.aws_iam_policy_document.data_backup_policy.json
}

# S3 Bucket Notifications (for triggering model retraining when new models are uploaded)
resource "aws_s3_bucket_notification" "model_storage_notification" {
  count = var.enable_model_notifications ? 1 : 0

  bucket = aws_s3_bucket.model_storage.id

  dynamic "lambda_function" {
    for_each = var.notification_lambda_arns

    content {
      lambda_function_arn = lambda_function.value
      events              = ["s3:ObjectCreated:*"]
      filter_prefix       = "models/"
      filter_suffix       = ".pkl"
    }
  }

  dynamic "topic" {
    for_each = var.notification_sns_topics

    content {
      topic_arn = topic.value
      events    = ["s3:ObjectCreated:*"]
      filter_prefix = "models/"
      filter_suffix = ".pkl"
    }
  }
}

# CloudWatch metrics for S3 buckets
resource "aws_cloudwatch_metric_alarm" "model_storage_size" {
  count = var.enable_cloudwatch_metrics ? 1 : 0

  alarm_name          = "${var.name_prefix}-model-storage-size"
  comparison_operator = "GreaterThanThreshold"
  evaluation_periods  = "2"
  metric_name         = "BucketSizeBytes"
  namespace           = "AWS/S3"
  period              = "86400" # Daily
  statistic           = "Average"
  threshold           = var.model_storage_size_threshold
  alarm_description   = "Model storage bucket size exceeded threshold"
  alarm_actions       = var.alarm_actions

  dimensions = {
    BucketName  = aws_s3_bucket.model_storage.bucket
    StorageType = "StandardStorage"
  }

  tags = var.tags
}

# Inventory configuration for cost optimization
resource "aws_s3_bucket_inventory" "model_storage" {
  bucket = aws_s3_bucket.model_storage.bucket
  name   = "${var.name_prefix}-model-inventory"

  included_object_versions = "Current"

  schedule {
    frequency = "Daily"
  }

  destination {
    bucket {
      format     = "CSV"
      bucket_arn = aws_s3_bucket.logs.arn
      prefix     = "inventory/models/"
    }
  }

  optional_fields = [
    "Size",
    "LastModifiedDate",
    "StorageClass",
    "ETag",
  ]
}