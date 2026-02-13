"""
Prometheus Metrics for F1 Analytics Application

This module defines all Prometheus metrics used throughout the F1 Analytics application,
including both standard application metrics and F1-specific business metrics.
"""

import time
from typing import Dict, Any, Optional, List
from contextlib import contextmanager
from prometheus_client import (
    CollectorRegistry,
    Counter,
    Histogram,
    Gauge,
    generate_latest,
    CONTENT_TYPE_LATEST,
    multiprocess,
    REGISTRY
)
import structlog
from fastapi import FastAPI, Request, Response

# Configure structured logging
logger = structlog.get_logger(__name__)

# Create custom registry for F1 Analytics metrics
metrics_registry = CollectorRegistry()

# =============================================================================
# Standard Application Metrics
# =============================================================================

# HTTP Request metrics
http_requests_total = Counter(
    'http_requests_total',
    'Total number of HTTP requests',
    ['method', 'endpoint', 'status'],
    registry=metrics_registry
)

http_request_duration_seconds = Histogram(
    'http_request_duration_seconds',
    'HTTP request duration in seconds',
    ['method', 'endpoint'],
    buckets=[0.005, 0.01, 0.025, 0.05, 0.075, 0.1, 0.25, 0.5, 0.75, 1.0, 2.5, 5.0, 7.5, 10.0],
    registry=metrics_registry
)

# Application health metrics
app_info = Gauge(
    'app_info',
    'Application information',
    ['version', 'environment'],
    registry=metrics_registry
)

# =============================================================================
# F1 Analytics Business Metrics
# =============================================================================

# Prediction Generation Metrics
f1_predictions_generated_total = Counter(
    'f1_predictions_generated_total',
    'Total number of F1 race predictions generated',
    ['model_type', 'race_type', 'success'],
    registry=metrics_registry
)

f1_prediction_accuracy_gauge = Gauge(
    'f1_prediction_accuracy',
    'Current accuracy rate of F1 predictions',
    ['model_type', 'race_type', 'timeframe'],
    registry=metrics_registry
)

# Machine Learning Pipeline Metrics
f1_ml_inference_duration_seconds = Histogram(
    'f1_ml_inference_duration_seconds',
    'Duration of ML model inference in seconds',
    ['model_type', 'stage'],
    buckets=[0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0, 30.0, 60.0],
    registry=metrics_registry
)

f1_feature_engineering_duration_seconds = Histogram(
    'f1_feature_engineering_duration_seconds',
    'Duration of feature engineering pipeline in seconds',
    ['feature_type', 'data_source'],
    buckets=[0.01, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0],
    registry=metrics_registry
)

f1_model_accuracy_score = Gauge(
    'f1_model_accuracy_score',
    'Current accuracy score of ML models',
    ['model_type', 'validation_type'],
    registry=metrics_registry
)

# Data Processing Metrics
f1_cache_operations_total = Counter(
    'f1_cache_operations_total',
    'Total cache operations for F1 data',
    ['operation', 'cache_type', 'status'],
    registry=metrics_registry
)

f1_database_query_duration_seconds = Histogram(
    'f1_database_query_duration_seconds',
    'Duration of database queries in seconds',
    ['query_type', 'table'],
    buckets=[0.001, 0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5],
    registry=metrics_registry
)

f1_race_data_freshness_gauge = Gauge(
    'f1_race_data_freshness_seconds',
    'Seconds since last race data update',
    ['data_type'],
    registry=metrics_registry
)

# User Activity Metrics
f1_active_users_gauge = Gauge(
    'f1_active_users',
    'Number of active users',
    ['timeframe'],
    registry=metrics_registry
)

f1_api_endpoint_usage_total = Counter(
    'f1_api_endpoint_usage_total',
    'Total API endpoint usage',
    ['endpoint', 'user_type'],
    registry=metrics_registry
)

# ELO Rating System Metrics
f1_elo_calculation_duration_seconds = Histogram(
    'f1_elo_calculation_duration_seconds',
    'Duration of ELO rating calculations in seconds',
    ['calculation_type'],
    buckets=[0.001, 0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5],
    registry=metrics_registry
)

f1_driver_elo_rating_gauge = Gauge(
    'f1_driver_elo_rating',
    'Current ELO rating of drivers',
    ['driver_name', 'driver_code', 'team'],
    registry=metrics_registry
)

# =============================================================================
# Utility Functions for Tracking Metrics
# =============================================================================

def track_prediction_generated(model_type: str, race_type: str, success: bool) -> None:
    """Track a prediction generation event."""
    f1_predictions_generated_total.labels(
        model_type=model_type,
        race_type=race_type,
        success="success" if success else "failure"
    ).inc()
    logger.info(
        "Prediction generated",
        model_type=model_type,
        race_type=race_type,
        success=success
    )


def track_prediction_accuracy(model_type: str, race_type: str, timeframe: str, accuracy: float) -> None:
    """Update prediction accuracy gauge."""
    f1_prediction_accuracy_gauge.labels(
        model_type=model_type,
        race_type=race_type,
        timeframe=timeframe
    ).set(accuracy)
    logger.info(
        "Prediction accuracy updated",
        model_type=model_type,
        race_type=race_type,
        timeframe=timeframe,
        accuracy=accuracy
    )


@contextmanager
def track_ml_inference(model_type: str, stage: str):
    """Context manager to track ML inference duration."""
    start_time = time.time()
    try:
        yield
    finally:
        duration = time.time() - start_time
        f1_ml_inference_duration_seconds.labels(
            model_type=model_type,
            stage=stage
        ).observe(duration)
        logger.info(
            "ML inference completed",
            model_type=model_type,
            stage=stage,
            duration=duration
        )


@contextmanager
def track_feature_engineering(feature_type: str, data_source: str):
    """Context manager to track feature engineering duration."""
    start_time = time.time()
    try:
        yield
    finally:
        duration = time.time() - start_time
        f1_feature_engineering_duration_seconds.labels(
            feature_type=feature_type,
            data_source=data_source
        ).observe(duration)
        logger.info(
            "Feature engineering completed",
            feature_type=feature_type,
            data_source=data_source,
            duration=duration
        )


def track_cache_operation(operation: str, cache_type: str, status: str) -> None:
    """Track cache operations."""
    f1_cache_operations_total.labels(
        operation=operation,
        cache_type=cache_type,
        status=status
    ).inc()
    logger.debug(
        "Cache operation tracked",
        operation=operation,
        cache_type=cache_type,
        status=status
    )


@contextmanager
def track_database_query(query_type: str, table: str):
    """Context manager to track database query duration."""
    start_time = time.time()
    try:
        yield
    finally:
        duration = time.time() - start_time
        f1_database_query_duration_seconds.labels(
            query_type=query_type,
            table=table
        ).observe(duration)
        logger.debug(
            "Database query completed",
            query_type=query_type,
            table=table,
            duration=duration
        )


def update_race_data_freshness(data_type: str, seconds_since_update: float) -> None:
    """Update race data freshness gauge."""
    f1_race_data_freshness_gauge.labels(data_type=data_type).set(seconds_since_update)
    logger.debug(
        "Race data freshness updated",
        data_type=data_type,
        seconds_since_update=seconds_since_update
    )


def update_active_users(timeframe: str, count: int) -> None:
    """Update active users gauge."""
    f1_active_users_gauge.labels(timeframe=timeframe).set(count)
    logger.debug(
        "Active users count updated",
        timeframe=timeframe,
        count=count
    )


def update_driver_elo_rating(driver_name: str, driver_code: str, team: str, rating: float) -> None:
    """Update driver ELO rating gauge."""
    f1_driver_elo_rating_gauge.labels(
        driver_name=driver_name,
        driver_code=driver_code,
        team=team
    ).set(rating)
    logger.debug(
        "Driver ELO rating updated",
        driver_name=driver_name,
        driver_code=driver_code,
        team=team,
        rating=rating
    )


# =============================================================================
# FastAPI Integration
# =============================================================================

def instrument_fastapi_app(app: FastAPI) -> None:
    """
    Instrument a FastAPI application with Prometheus metrics.

    This function adds the /metrics endpoint and sets up application info.
    """

    @app.get("/metrics")
    async def metrics_endpoint():
        """Prometheus metrics endpoint."""
        return Response(
            content=generate_latest(metrics_registry),
            media_type=CONTENT_TYPE_LATEST
        )

    # Set application info
    import os
    from app.config import app_config

    app_info.labels(
        version="1.0.0",
        environment=os.getenv("ENVIRONMENT", "development")
    ).set(1)

    logger.info("FastAPI application instrumented with Prometheus metrics")


# =============================================================================
# Health Check Integration
# =============================================================================

def get_metrics_summary() -> Dict[str, Any]:
    """
    Get a summary of current metrics for health check purposes.

    Returns:
        Dictionary containing current metrics summary
    """
    try:
        # This is a simplified summary for health checks
        # In production, you might want to expose more detailed metrics
        return {
            "metrics_enabled": True,
            "registry_collectors": len(metrics_registry._collector_to_names),
            "last_updated": time.time()
        }
    except Exception as e:
        logger.error("Failed to generate metrics summary", error=str(e))
        return {
            "metrics_enabled": False,
            "error": str(e),
            "last_updated": time.time()
        }


# =============================================================================
# Initialization
# =============================================================================

def initialize_metrics() -> None:
    """Initialize default metric values."""
    logger.info("Initializing F1 Analytics Prometheus metrics")

    # Set initial values for key gauges
    f1_race_data_freshness_gauge.labels(data_type="race_results").set(0)
    f1_race_data_freshness_gauge.labels(data_type="driver_standings").set(0)
    f1_race_data_freshness_gauge.labels(data_type="weather_data").set(0)

    f1_active_users_gauge.labels(timeframe="last_hour").set(0)
    f1_active_users_gauge.labels(timeframe="last_day").set(0)

    logger.info("F1 Analytics metrics initialized successfully")


# Initialize metrics when module is imported
initialize_metrics()