# Monitoring Module for F1 Prediction Analytics Infrastructure
# Creates Application Load Balancer, CloudWatch resources, and monitoring infrastructure

# Application Load Balancer for EKS services
resource "aws_lb" "main" {
  name               = "${var.name_prefix}-alb"
  internal           = false
  load_balancer_type = "application"
  security_groups    = [aws_security_group.alb.id]
  subnets           = var.subnet_ids

  enable_deletion_protection = var.enable_deletion_protection

  access_logs {
    bucket  = var.access_logs_bucket
    prefix  = "alb-logs"
    enabled = var.access_logs_bucket != null
  }

  tags = merge(var.tags, {
    Name = "${var.name_prefix}-alb"
    Type = "application"
  })
}

# Security Group for ALB
resource "aws_security_group" "alb" {
  name        = "${var.name_prefix}-alb-sg"
  description = "Security group for Application Load Balancer"
  vpc_id      = var.vpc_id

  ingress {
    description = "HTTP"
    from_port   = 80
    to_port     = 80
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
  }

  ingress {
    description = "HTTPS"
    from_port   = 443
    to_port     = 443
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
  }

  egress {
    description = "All outbound traffic"
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }

  tags = merge(var.tags, {
    Name = "${var.name_prefix}-alb-sg"
  })
}

# Target Groups for different services
resource "aws_lb_target_group" "api" {
  name     = "${var.name_prefix}-api-tg"
  port     = 8000
  protocol = "HTTP"
  vpc_id   = var.vpc_id
  target_type = "ip"

  health_check {
    enabled             = true
    healthy_threshold   = 2
    unhealthy_threshold = 3
    timeout             = 5
    interval            = 30
    path                = "/health"
    matcher             = "200"
    port                = "traffic-port"
    protocol            = "HTTP"
  }

  tags = merge(var.tags, {
    Name = "${var.name_prefix}-api-tg"
    Type = "api"
  })
}

resource "aws_lb_target_group" "frontend" {
  name     = "${var.name_prefix}-frontend-tg"
  port     = 80
  protocol = "HTTP"
  vpc_id   = var.vpc_id
  target_type = "ip"

  health_check {
    enabled             = true
    healthy_threshold   = 2
    unhealthy_threshold = 3
    timeout             = 5
    interval            = 30
    path                = "/"
    matcher             = "200"
    port                = "traffic-port"
    protocol            = "HTTP"
  }

  tags = merge(var.tags, {
    Name = "${var.name_prefix}-frontend-tg"
    Type = "frontend"
  })
}

# ALB Listeners
resource "aws_lb_listener" "http" {
  load_balancer_arn = aws_lb.main.arn
  port              = "80"
  protocol          = "HTTP"

  default_action {
    type = "redirect"

    redirect {
      port        = "443"
      protocol    = "HTTPS"
      status_code = "HTTP_301"
    }
  }

  tags = var.tags
}

resource "aws_lb_listener" "https" {
  count = var.certificate_arn != null ? 1 : 0

  load_balancer_arn = aws_lb.main.arn
  port              = "443"
  protocol          = "HTTPS"
  ssl_policy        = "ELBSecurityPolicy-TLS-1-2-2017-01"
  certificate_arn   = var.certificate_arn

  default_action {
    type             = "forward"
    target_group_arn = aws_lb_target_group.frontend.arn
  }

  tags = var.tags
}

# Listener Rules for API routing
resource "aws_lb_listener_rule" "api" {
  count = var.certificate_arn != null ? 1 : 0

  listener_arn = aws_lb_listener.https[0].arn
  priority     = 100

  action {
    type             = "forward"
    target_group_arn = aws_lb_target_group.api.arn
  }

  condition {
    path_pattern {
      values = ["/api/*"]
    }
  }

  tags = var.tags
}

# CloudWatch Log Groups
resource "aws_cloudwatch_log_group" "application" {
  name              = "/aws/application/${var.name_prefix}"
  retention_in_days = var.log_retention_days

  tags = merge(var.tags, {
    Name = "${var.name_prefix}-application-logs"
    Type = "application"
  })
}

resource "aws_cloudwatch_log_group" "api" {
  name              = "/aws/api/${var.name_prefix}"
  retention_in_days = var.log_retention_days

  tags = merge(var.tags, {
    Name = "${var.name_prefix}-api-logs"
    Type = "api"
  })
}

resource "aws_cloudwatch_log_group" "ml_pipeline" {
  name              = "/aws/ml/${var.name_prefix}"
  retention_in_days = var.log_retention_days

  tags = merge(var.tags, {
    Name = "${var.name_prefix}-ml-logs"
    Type = "ml"
  })
}

resource "aws_cloudwatch_log_group" "ingestion" {
  name              = "/aws/ingestion/${var.name_prefix}"
  retention_in_days = var.log_retention_days

  tags = merge(var.tags, {
    Name = "${var.name_prefix}-ingestion-logs"
    Type = "ingestion"
  })
}

# CloudWatch Dashboards
resource "aws_cloudwatch_dashboard" "main" {
  dashboard_name = "${var.name_prefix}-dashboard"

  dashboard_body = jsonencode({
    widgets = [
      {
        type   = "metric"
        x      = 0
        y      = 0
        width  = 12
        height = 6

        properties = {
          metrics = [
            ["AWS/ApplicationELB", "RequestCount", "LoadBalancer", aws_lb.main.arn_suffix],
            [".", "TargetResponseTime", ".", "."],
            [".", "HTTPCode_Target_2XX_Count", ".", "."],
            [".", "HTTPCode_Target_4XX_Count", ".", "."],
            [".", "HTTPCode_Target_5XX_Count", ".", "."]
          ]
          view    = "timeSeries"
          stacked = false
          region  = data.aws_region.current.name
          title   = "Application Load Balancer Metrics"
          period  = 300
        }
      },
      {
        type   = "metric"
        x      = 0
        y      = 6
        width  = 12
        height = 6

        properties = {
          metrics = [
            ["AWS/EKS", "cluster_failed_request_count", "ClusterName", var.cluster_name],
            [".", "cluster_request_total", ".", "."]
          ]
          view    = "timeSeries"
          stacked = false
          region  = data.aws_region.current.name
          title   = "EKS Cluster Metrics"
          period  = 300
        }
      },
      {
        type   = "log"
        x      = 0
        y      = 12
        width  = 24
        height = 6

        properties = {
          query = "SOURCE '${aws_cloudwatch_log_group.application.name}' | fields @timestamp, @message | sort @timestamp desc | limit 20"
          region = data.aws_region.current.name
          title = "Recent Application Logs"
        }
      }
    ]
  })

  tags = var.tags
}

# CloudWatch Alarms for ALB
resource "aws_cloudwatch_metric_alarm" "alb_high_response_time" {
  alarm_name          = "${var.name_prefix}-alb-high-response-time"
  comparison_operator = "GreaterThanThreshold"
  evaluation_periods  = "2"
  metric_name         = "TargetResponseTime"
  namespace           = "AWS/ApplicationELB"
  period              = "120"
  statistic           = "Average"
  threshold           = "2.0"
  alarm_description   = "This metric monitors ALB response time"
  alarm_actions       = var.alarm_actions

  dimensions = {
    LoadBalancer = aws_lb.main.arn_suffix
  }

  tags = var.tags
}

resource "aws_cloudwatch_metric_alarm" "alb_high_4xx_errors" {
  alarm_name          = "${var.name_prefix}-alb-high-4xx-errors"
  comparison_operator = "GreaterThanThreshold"
  evaluation_periods  = "2"
  metric_name         = "HTTPCode_Target_4XX_Count"
  namespace           = "AWS/ApplicationELB"
  period              = "300"
  statistic           = "Sum"
  threshold           = "50"
  alarm_description   = "This metric monitors ALB 4XX errors"
  alarm_actions       = var.alarm_actions

  dimensions = {
    LoadBalancer = aws_lb.main.arn_suffix
  }

  tags = var.tags
}

resource "aws_cloudwatch_metric_alarm" "alb_high_5xx_errors" {
  alarm_name          = "${var.name_prefix}-alb-high-5xx-errors"
  comparison_operator = "GreaterThanThreshold"
  evaluation_periods  = "2"
  metric_name         = "HTTPCode_Target_5XX_Count"
  namespace           = "AWS/ApplicationELB"
  period              = "300"
  statistic           = "Sum"
  threshold           = "10"
  alarm_description   = "This metric monitors ALB 5XX errors"
  alarm_actions       = var.alarm_actions

  dimensions = {
    LoadBalancer = aws_lb.main.arn_suffix
  }

  tags = var.tags
}

# SNS Topic for alerts (if enabled)
resource "aws_sns_topic" "alerts" {
  count = var.create_sns_topic ? 1 : 0

  name = "${var.name_prefix}-alerts"

  tags = merge(var.tags, {
    Name = "${var.name_prefix}-alerts"
    Type = "monitoring"
  })
}

resource "aws_sns_topic_subscription" "email_alerts" {
  count = var.create_sns_topic && length(var.alert_email_addresses) > 0 ? length(var.alert_email_addresses) : 0

  topic_arn = aws_sns_topic.alerts[0].arn
  protocol  = "email"
  endpoint  = var.alert_email_addresses[count.index]
}

# CloudWatch Composite Alarm for overall system health
resource "aws_cloudwatch_composite_alarm" "system_health" {
  alarm_description = "Overall system health alarm for F1 Analytics"
  alarm_name        = "${var.name_prefix}-system-health"

  alarm_rule = "ALARM(${aws_cloudwatch_metric_alarm.alb_high_response_time.alarm_name}) OR ALARM(${aws_cloudwatch_metric_alarm.alb_high_5xx_errors.alarm_name})"

  actions_enabled = true
  alarm_actions   = var.create_sns_topic ? [aws_sns_topic.alerts[0].arn] : var.alarm_actions

  tags = var.tags
}

# Custom Metrics for ML Pipeline
resource "aws_cloudwatch_log_metric_filter" "prediction_accuracy" {
  name           = "${var.name_prefix}-prediction-accuracy"
  log_group_name = aws_cloudwatch_log_group.ml_pipeline.name
  pattern        = "[timestamp, level, message, accuracy_metric=*]"

  metric_transformation {
    name      = "PredictionAccuracy"
    namespace = "F1Analytics/ML"
    value     = "$accuracy_metric"
  }
}

resource "aws_cloudwatch_log_metric_filter" "model_training_duration" {
  name           = "${var.name_prefix}-model-training-duration"
  log_group_name = aws_cloudwatch_log_group.ml_pipeline.name
  pattern        = "[timestamp, level, message, training_duration=*]"

  metric_transformation {
    name      = "ModelTrainingDuration"
    namespace = "F1Analytics/ML"
    value     = "$training_duration"
  }
}

resource "aws_cloudwatch_log_metric_filter" "data_ingestion_records" {
  name           = "${var.name_prefix}-data-ingestion-records"
  log_group_name = aws_cloudwatch_log_group.ingestion.name
  pattern        = "[timestamp, level, message, records_processed=*]"

  metric_transformation {
    name      = "DataIngestionRecords"
    namespace = "F1Analytics/Ingestion"
    value     = "$records_processed"
  }
}

# CloudWatch Insights Saved Queries
resource "aws_cloudwatch_query_definition" "error_analysis" {
  name = "${var.name_prefix}-error-analysis"

  log_group_names = [
    aws_cloudwatch_log_group.application.name,
    aws_cloudwatch_log_group.api.name
  ]

  query_string = <<EOF
fields @timestamp, @message
| filter @message like /ERROR/
| sort @timestamp desc
| limit 20
EOF
}

resource "aws_cloudwatch_query_definition" "api_performance" {
  name = "${var.name_prefix}-api-performance"

  log_group_names = [
    aws_cloudwatch_log_group.api.name
  ]

  query_string = <<EOF
fields @timestamp, @message
| filter @message like /request_duration/
| sort @timestamp desc
| stats avg(request_duration) by bin(5m)
EOF
}

# EventBridge Rules for automation (optional)
resource "aws_cloudwatch_event_rule" "model_training_schedule" {
  count = var.enable_automated_training ? 1 : 0

  name                = "${var.name_prefix}-model-training-schedule"
  description         = "Trigger model training after race completion"
  schedule_expression = "cron(0 6 ? * MON *)" # Every Monday at 6 AM UTC

  tags = var.tags
}

resource "aws_cloudwatch_event_target" "model_training_target" {
  count = var.enable_automated_training ? 1 : 0

  rule      = aws_cloudwatch_event_rule.model_training_schedule[0].name
  target_id = "ModelTrainingTarget"
  arn       = var.model_training_lambda_arn

  input = jsonencode({
    action = "trigger_training"
    reason = "scheduled"
  })
}

# Data sources
data "aws_region" "current" {}