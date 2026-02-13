"""
F1 Analytics Monitoring Module

This module provides comprehensive Prometheus metrics collection for the F1 Analytics application.
It includes application-level metrics, custom F1 business metrics, and performance monitoring.
"""

from .metrics import (
    metrics_registry,
    http_requests_total,
    http_request_duration_seconds,
    f1_predictions_generated_total,
    f1_prediction_accuracy_gauge,
    f1_ml_inference_duration_seconds,
    f1_feature_engineering_duration_seconds,
    f1_cache_operations_total,
    f1_database_query_duration_seconds,
    f1_race_data_freshness_gauge,
    f1_active_users_gauge,
    instrument_fastapi_app,
    track_prediction_generated,
    track_prediction_accuracy,
    track_ml_inference,
    track_feature_engineering,
    track_cache_operation,
    track_database_query,
    update_race_data_freshness,
    update_active_users
)

from .middleware import PrometheusMiddleware

__all__ = [
    "metrics_registry",
    "http_requests_total",
    "http_request_duration_seconds",
    "f1_predictions_generated_total",
    "f1_prediction_accuracy_gauge",
    "f1_ml_inference_duration_seconds",
    "f1_feature_engineering_duration_seconds",
    "f1_cache_operations_total",
    "f1_database_query_duration_seconds",
    "f1_race_data_freshness_gauge",
    "f1_active_users_gauge",
    "instrument_fastapi_app",
    "track_prediction_generated",
    "track_prediction_accuracy",
    "track_ml_inference",
    "track_feature_engineering",
    "track_cache_operation",
    "track_database_query",
    "update_race_data_freshness",
    "update_active_users",
    "PrometheusMiddleware"
]