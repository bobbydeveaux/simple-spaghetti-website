"""
Unit tests for F1 Analytics Prometheus monitoring module.

Tests the metrics collection, middleware, and services to ensure proper
functionality of the Prometheus integration.
"""

import pytest
import asyncio
import time
from unittest.mock import Mock, patch, AsyncMock
from fastapi import FastAPI
from fastapi.testclient import TestClient
from prometheus_client import REGISTRY, CollectorRegistry

# Import the monitoring modules to test
from app.monitoring.metrics import (
    metrics_registry,
    http_requests_total,
    http_request_duration_seconds,
    f1_predictions_generated_total,
    f1_prediction_accuracy_gauge,
    track_prediction_generated,
    track_prediction_accuracy,
    get_metrics_summary,
    initialize_metrics,
    instrument_fastapi_app
)

from app.monitoring.middleware import PrometheusMiddleware
from app.monitoring.services import F1MetricsService, F1DataFreshnessTracker


class TestMetricsModule:
    """Test the core metrics functionality."""

    def setup_method(self):
        """Set up test fixtures."""
        # Create a fresh registry for each test to avoid interference
        self.test_registry = CollectorRegistry()

    def test_metrics_registry_creation(self):
        """Test that the metrics registry is properly created."""
        assert metrics_registry is not None
        assert hasattr(metrics_registry, '_collector_to_names')

    def test_http_metrics_creation(self):
        """Test that HTTP metrics are properly created."""
        assert http_requests_total is not None
        assert http_request_duration_seconds is not None

        # Test metric labels
        assert hasattr(http_requests_total, '_labelnames')
        assert 'method' in http_requests_total._labelnames
        assert 'endpoint' in http_requests_total._labelnames
        assert 'status' in http_requests_total._labelnames

    def test_f1_specific_metrics_creation(self):
        """Test that F1-specific metrics are properly created."""
        assert f1_predictions_generated_total is not None
        assert f1_prediction_accuracy_gauge is not None

        # Test F1 metric labels
        assert 'model_type' in f1_predictions_generated_total._labelnames
        assert 'race_type' in f1_predictions_generated_total._labelnames
        assert 'success' in f1_predictions_generated_total._labelnames

    def test_track_prediction_generated(self):
        """Test the prediction tracking functionality."""
        initial_value = f1_predictions_generated_total.labels(
            model_type="random_forest",
            race_type="grand_prix",
            success="success"
        )._value._value

        # Track a successful prediction
        track_prediction_generated("random_forest", "grand_prix", True)

        # Verify the counter increased
        new_value = f1_predictions_generated_total.labels(
            model_type="random_forest",
            race_type="grand_prix",
            success="success"
        )._value._value

        assert new_value > initial_value

    def test_track_prediction_accuracy(self):
        """Test prediction accuracy tracking."""
        accuracy_value = 0.85

        track_prediction_accuracy("xgboost", "sprint", "last_5_races", accuracy_value)

        # Verify the gauge was set correctly
        current_value = f1_prediction_accuracy_gauge.labels(
            model_type="xgboost",
            race_type="sprint",
            timeframe="last_5_races"
        )._value._value

        assert current_value == accuracy_value

    def test_metrics_summary(self):
        """Test the metrics summary function."""
        summary = get_metrics_summary()

        assert isinstance(summary, dict)
        assert 'metrics_enabled' in summary
        assert 'last_updated' in summary
        assert summary['metrics_enabled'] is True

    def test_initialize_metrics(self):
        """Test metrics initialization."""
        # This should not raise any exceptions
        initialize_metrics()


class TestPrometheusMiddleware:
    """Test the Prometheus middleware functionality."""

    def setup_method(self):
        """Set up test fixtures."""
        self.app = FastAPI()
        self.middleware = PrometheusMiddleware(
            app=self.app,
            app_name="test-f1-api",
            skip_paths=["/health", "/metrics"]
        )

    def test_middleware_initialization(self):
        """Test middleware initialization."""
        assert self.middleware.app_name == "test-f1-api"
        assert "/health" in self.middleware.skip_paths
        assert "/metrics" in self.middleware.skip_paths

    def test_normalize_path(self):
        """Test URL path normalization."""
        # Test driver ID normalization
        normalized = self.middleware._normalize_path("/api/v1/drivers/123")
        assert "drivers/{id}" in normalized

        # Test race ID normalization
        normalized = self.middleware._normalize_path("/api/v1/races/456")
        assert "races/{id}" in normalized

        # Test path that doesn't need normalization
        normalized = self.middleware._normalize_path("/api/v1/predictions/next-race")
        assert normalized == "/api/v1/predictions/next-race"

    def test_should_skip_path(self):
        """Test path skipping logic."""
        assert self.middleware._should_skip_path("/health") is True
        assert self.middleware._should_skip_path("/metrics") is True
        assert self.middleware._should_skip_path("/api/v1/predictions") is False

    def test_is_f1_api_endpoint(self):
        """Test F1 API endpoint detection."""
        assert self.middleware._is_f1_api_endpoint("/api/v1/predictions/next-race") is True
        assert self.middleware._is_f1_api_endpoint("/api/v1/drivers/rankings") is True
        assert self.middleware._is_f1_api_endpoint("/health") is False
        assert self.middleware._is_f1_api_endpoint("/metrics") is False

    def test_extract_user_type(self):
        """Test user type extraction."""
        # Mock request with auth header
        mock_request = Mock()
        mock_request.headers = {"authorization": "Bearer token123"}
        mock_request.query_params = {}

        user_type = self.middleware._extract_user_type(mock_request)
        assert user_type == "authenticated"

        # Mock request with API key
        mock_request.headers = {}
        mock_request.query_params = {"api_key": "key123"}

        user_type = self.middleware._extract_user_type(mock_request)
        assert user_type == "api_user"

        # Mock anonymous request
        mock_request.headers = {}
        mock_request.query_params = {}

        user_type = self.middleware._extract_user_type(mock_request)
        assert user_type == "anonymous"


class TestF1MetricsService:
    """Test the F1 metrics service functionality."""

    def setup_method(self):
        """Set up test fixtures."""
        self.service = F1MetricsService()

    def test_service_initialization(self):
        """Test service initialization."""
        assert self.service.last_accuracy_update == {}
        assert self.service.active_user_cache == {}
        assert self.service.prediction_batch_cache == []

    @pytest.mark.asyncio
    async def test_track_prediction_batch(self):
        """Test prediction batch tracking."""
        predictions = [
            {"driver_id": 1, "win_probability": 0.35},
            {"driver_id": 2, "win_probability": 0.28},
            {"driver_id": 3, "win_probability": 0.22}
        ]

        await self.service.track_prediction_batch(
            predictions=predictions,
            model_type="random_forest",
            race_id=1,
            race_type="grand_prix"
        )

        # Verify batch was cached
        assert len(self.service.prediction_batch_cache) == 1
        batch = self.service.prediction_batch_cache[0]
        assert batch["model_type"] == "random_forest"
        assert batch["race_id"] == 1
        assert len(batch["predictions"]) == 3

    @pytest.mark.asyncio
    async def test_update_model_accuracy(self):
        """Test model accuracy updating."""
        # First add some prediction batches
        predictions = [{"driver_id": 1, "win_probability": 0.35}]
        await self.service.track_prediction_batch(
            predictions=predictions,
            model_type="xgboost",
            race_id=1
        )

        # Test accuracy update
        actual_results = [{"driver_id": 1, "position": 1}]
        accuracy = await self.service.update_model_accuracy(
            model_type="xgboost",
            actual_results=actual_results,
            validation_type="live_race"
        )

        assert isinstance(accuracy, float)
        assert 0.0 <= accuracy <= 1.0
        assert "xgboost_live_race" in self.service.last_accuracy_update

    @pytest.mark.asyncio
    async def test_track_elo_calculation(self):
        """Test ELO calculation tracking."""
        race_results = [
            {"driver_id": 1, "position": 1},
            {"driver_id": 2, "position": 2}
        ]

        duration = await self.service.track_elo_calculation(
            calculation_type="post_race",
            driver_count=2,
            race_results=race_results
        )

        assert isinstance(duration, float)
        assert duration > 0

    @pytest.mark.asyncio
    async def test_update_user_activity_metrics(self):
        """Test user activity metrics updating."""
        await self.service.update_user_activity_metrics()

        assert 'last_hour' in self.service.active_user_cache
        assert 'last_day' in self.service.active_user_cache
        assert self.service.active_user_cache['last_hour'] > 0
        assert self.service.active_user_cache['last_day'] > 0

    def test_get_metrics_summary(self):
        """Test metrics summary generation."""
        summary = self.service.get_metrics_summary()

        assert isinstance(summary, dict)
        assert 'prediction_batches_cached' in summary
        assert 'service_healthy' in summary
        assert summary['service_healthy'] is True


class TestF1DataFreshnessTracker:
    """Test the data freshness tracker."""

    def setup_method(self):
        """Set up test fixtures."""
        self.tracker = F1DataFreshnessTracker()

    @pytest.mark.asyncio
    async def test_update_data_source_freshness(self):
        """Test data source freshness updating."""
        current_time = time.time()
        last_update = current_time - 300  # 5 minutes ago

        await self.tracker.update_data_source_freshness(
            data_source="race_results",
            last_update_timestamp=last_update
        )

        assert "race_results" in self.tracker.last_updates
        info = self.tracker.last_updates["race_results"]
        assert info["last_update"] == last_update
        assert info["seconds_since_update"] >= 300

    def test_get_stalest_data_sources(self):
        """Test identification of stale data sources."""
        # Manually add some data with different freshness
        current_time = time.time()

        self.tracker.last_updates = {
            "fresh_data": {
                "last_update": current_time - 100,  # 100 seconds ago
                "seconds_since_update": 100
            },
            "stale_data": {
                "last_update": current_time - 7200,  # 2 hours ago
                "seconds_since_update": 7200
            }
        }

        stale_sources = self.tracker.get_stalest_data_sources(threshold_seconds=3600)
        assert "stale_data" in stale_sources
        assert "fresh_data" not in stale_sources


class TestFastAPIIntegration:
    """Test FastAPI integration with monitoring."""

    def setup_method(self):
        """Set up test fixtures."""
        self.app = FastAPI()
        instrument_fastapi_app(self.app)
        self.client = TestClient(self.app)

    def test_metrics_endpoint_exists(self):
        """Test that the /metrics endpoint is created."""
        # Check if the endpoint exists in the app routes
        routes = [route.path for route in self.app.routes]
        assert "/metrics" in routes

    def test_metrics_endpoint_response(self):
        """Test that the /metrics endpoint returns Prometheus metrics."""
        response = self.client.get("/metrics")

        assert response.status_code == 200
        assert "text/plain" in response.headers.get("content-type", "")

        # Check for some expected metric names in the response
        content = response.text
        assert "http_requests_total" in content or "# HELP" in content


# Integration test with the actual main app
class TestMainAppIntegration:
    """Test integration with the main FastAPI application."""

    def test_monitoring_imports(self):
        """Test that monitoring modules can be imported."""
        # This test ensures all imports in main.py work correctly
        try:
            from app.monitoring import (
                instrument_fastapi_app,
                PrometheusMiddleware,
                get_metrics_summary,
                initialize_metrics,
                track_prediction_generated,
                track_ml_inference,
                track_cache_operation,
                update_race_data_freshness,
                update_driver_elo_rating
            )
            # If we get here, all imports succeeded
            assert True
        except ImportError as e:
            pytest.fail(f"Failed to import monitoring components: {e}")

    def test_metrics_middleware_configuration(self):
        """Test that metrics middleware can be configured."""
        app = FastAPI()

        # This should not raise any exceptions
        try:
            app.add_middleware(
                PrometheusMiddleware,
                app_name="test-f1-analytics",
                skip_paths=["/metrics", "/health"]
            )
            instrument_fastapi_app(app)
            assert True
        except Exception as e:
            pytest.fail(f"Failed to configure monitoring: {e}")


if __name__ == "__main__":
    # Simple test runner for basic validation
    print("Running basic monitoring tests...")

    # Test imports
    try:
        from app.monitoring import metrics, middleware, services
        print("✓ All monitoring modules imported successfully")
    except ImportError as e:
        print(f"✗ Import error: {e}")
        exit(1)

    # Test basic functionality
    try:
        initialize_metrics()
        track_prediction_generated("test_model", "test_race", True)
        summary = get_metrics_summary()
        print("✓ Basic metrics functionality works")
        print(f"✓ Metrics summary: {summary}")
    except Exception as e:
        print(f"✗ Metrics error: {e}")
        exit(1)

    print("✓ All basic tests passed!")