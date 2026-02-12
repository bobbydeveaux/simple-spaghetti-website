"""
Tests for health check functionality.
"""
import pytest
from unittest.mock import patch, Mock, MagicMock
import psycopg2
import redis
from app.main import check_database_connectivity, check_redis_connectivity


class TestDatabaseConnectivity:
    """Test database connectivity checks."""

    def test_check_database_connectivity_success(self):
        """Test successful database connectivity check."""
        # Mock successful database connection
        mock_conn = Mock()
        mock_cursor = Mock()
        mock_cursor.fetchone.return_value = (1,)
        mock_conn.cursor.return_value = mock_cursor

        with patch('psycopg2.connect', return_value=mock_conn), \
             patch.dict('os.environ', {'DATABASE_URL': 'postgresql://user:pass@host:5432/db'}):

            result = check_database_connectivity()

            assert result is True
            mock_conn.cursor.assert_called_once()
            mock_cursor.execute.assert_called_once_with("SELECT 1")
            mock_cursor.close.assert_called_once()
            mock_conn.close.assert_called_once()

    def test_check_database_connectivity_no_url(self):
        """Test database connectivity check with no DATABASE_URL."""
        with patch.dict('os.environ', {}, clear=True):
            result = check_database_connectivity()
            assert result is False

    def test_check_database_connectivity_connection_error(self):
        """Test database connectivity check with connection error."""
        with patch('psycopg2.connect', side_effect=psycopg2.OperationalError("Connection failed")), \
             patch.dict('os.environ', {'DATABASE_URL': 'postgresql://user:pass@host:5432/db'}):

            result = check_database_connectivity()
            assert result is False

    def test_check_database_connectivity_query_error(self):
        """Test database connectivity check with query error."""
        mock_conn = Mock()
        mock_cursor = Mock()
        mock_cursor.execute.side_effect = psycopg2.Error("Query failed")
        mock_conn.cursor.return_value = mock_cursor

        with patch('psycopg2.connect', return_value=mock_conn), \
             patch.dict('os.environ', {'DATABASE_URL': 'postgresql://user:pass@host:5432/db'}):

            result = check_database_connectivity()
            assert result is False

    def test_check_database_connectivity_url_parsing(self):
        """Test database connectivity with complex URL parsing."""
        test_url = 'postgresql://testuser:testpass@testhost:5433/testdb'

        mock_conn = Mock()
        mock_cursor = Mock()
        mock_cursor.fetchone.return_value = (1,)
        mock_conn.cursor.return_value = mock_cursor

        with patch('psycopg2.connect') as mock_connect, \
             patch.dict('os.environ', {'DATABASE_URL': test_url}):

            check_database_connectivity()

            # Verify connection was called with correct parameters
            mock_connect.assert_called_once_with(
                host='testhost',
                port=5433,
                database='testdb',
                user='testuser',
                password='testpass',
                connect_timeout=5
            )


class TestRedisConnectivity:
    """Test Redis connectivity checks."""

    def test_check_redis_connectivity_success(self):
        """Test successful Redis connectivity check."""
        mock_redis = Mock()
        mock_redis.ping.return_value = True

        with patch('redis.Redis', return_value=mock_redis), \
             patch.dict('os.environ', {'REDIS_URL': 'redis://:password@host:6379/0'}):

            result = check_redis_connectivity()

            assert result is True
            mock_redis.ping.assert_called_once()

    def test_check_redis_connectivity_no_url(self):
        """Test Redis connectivity check with no REDIS_URL."""
        with patch.dict('os.environ', {}, clear=True):
            result = check_redis_connectivity()
            assert result is False

    def test_check_redis_connectivity_connection_error(self):
        """Test Redis connectivity check with connection error."""
        with patch('redis.Redis', side_effect=redis.ConnectionError("Connection failed")), \
             patch.dict('os.environ', {'REDIS_URL': 'redis://:password@host:6379/0'}):

            result = check_redis_connectivity()
            assert result is False

    def test_check_redis_connectivity_ping_failure(self):
        """Test Redis connectivity check with ping failure."""
        mock_redis = Mock()
        mock_redis.ping.side_effect = redis.RedisError("Ping failed")

        with patch('redis.Redis', return_value=mock_redis), \
             patch.dict('os.environ', {'REDIS_URL': 'redis://:password@host:6379/0'}):

            result = check_redis_connectivity()
            assert result is False

    def test_check_redis_connectivity_url_parsing(self):
        """Test Redis connectivity with URL parsing."""
        test_url = 'redis://:testpass@testhost:6380/1'

        mock_redis = Mock()
        mock_redis.ping.return_value = True

        with patch('redis.Redis') as mock_redis_class, \
             patch.dict('os.environ', {'REDIS_URL': test_url}):

            mock_redis_class.return_value = mock_redis

            check_redis_connectivity()

            # Verify Redis was instantiated with correct parameters
            mock_redis_class.assert_called_once_with(
                host='testhost',
                port=6380,
                password='testpass',
                socket_timeout=5,
                socket_connect_timeout=5
            )


class TestHealthCheckIntegration:
    """Test health check integration scenarios."""

    @pytest.mark.asyncio
    async def test_health_check_all_async_calls(self):
        """Test that health check functions can be called asynchronously."""
        with patch('psycopg2.connect'), \
             patch('redis.Redis'), \
             patch.dict('os.environ', {
                 'DATABASE_URL': 'postgresql://user:pass@host:5432/db',
                 'REDIS_URL': 'redis://:pass@host:6379/0'
             }):

            # These should work in async context
            db_result = await check_database_connectivity()
            redis_result = await check_redis_connectivity()

            # Results depend on mocking, but functions should not raise exceptions
            assert isinstance(db_result, bool)
            assert isinstance(redis_result, bool)

    def test_health_check_timeout_handling(self):
        """Test that health checks handle timeouts appropriately."""
        # Test database timeout
        with patch('psycopg2.connect', side_effect=psycopg2.OperationalError("timeout")), \
             patch.dict('os.environ', {'DATABASE_URL': 'postgresql://user:pass@host:5432/db'}):

            result = check_database_connectivity()
            assert result is False

        # Test Redis timeout
        with patch('redis.Redis', side_effect=redis.TimeoutError("timeout")), \
             patch.dict('os.environ', {'REDIS_URL': 'redis://:pass@host:6379/0'}):

            result = check_redis_connectivity()
            assert result is False

    def test_health_check_environment_variations(self):
        """Test health checks with various environment configurations."""
        # Test with minimal URL (no password)
        with patch('psycopg2.connect') as mock_connect, \
             patch.dict('os.environ', {'DATABASE_URL': 'postgresql://user@host/db'}):

            check_database_connectivity()

            mock_connect.assert_called_once_with(
                host='host',
                port=5432,  # Default port
                database='db',
                user='user',
                password=None,  # No password in URL
                connect_timeout=5
            )

        # Test Redis with no password
        with patch('redis.Redis') as mock_redis, \
             patch.dict('os.environ', {'REDIS_URL': 'redis://host:6379/0'}):

            check_redis_connectivity()

            mock_redis.assert_called_once_with(
                host='host',
                port=6379,
                password=None,  # No password in URL
                socket_timeout=5,
                socket_connect_timeout=5
            )