"""
Session management for F1 Prediction Analytics.

This module provides session management using Redis for caching user sessions,
rate limiting, and other session-related functionality.
"""

import json
import logging
from datetime import datetime, timedelta, timezone
from typing import Dict, Optional, Any, List
from dataclasses import dataclass, asdict
from enum import Enum

import redis.asyncio as redis
from redis.exceptions import RedisError

from ..config import settings

logger = logging.getLogger(__name__)


class SessionStatus(Enum):
    """Session status enumeration."""
    ACTIVE = "active"
    EXPIRED = "expired"
    INVALID = "invalid"


@dataclass
class UserSession:
    """User session data structure."""
    user_id: int
    email: str
    created_at: datetime
    last_accessed: datetime
    ip_address: Optional[str] = None
    user_agent: Optional[str] = None
    additional_data: Optional[Dict[str, Any]] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert session to dictionary for Redis storage."""
        data = asdict(self)
        # Convert datetime objects to ISO strings
        data["created_at"] = self.created_at.isoformat()
        data["last_accessed"] = self.last_accessed.isoformat()
        return data

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "UserSession":
        """Create session from dictionary."""
        # Convert ISO strings back to datetime objects
        data["created_at"] = datetime.fromisoformat(data["created_at"])
        data["last_accessed"] = datetime.fromisoformat(data["last_accessed"])
        return cls(**data)


class SessionManager:
    """Redis-based session management for F1 analytics."""

    def __init__(self):
        self.redis_client: Optional[redis.Redis] = None
        self._connection_pool: Optional[redis.ConnectionPool] = None

    async def initialize(self) -> None:
        """Initialize Redis connection."""
        try:
            self._connection_pool = redis.ConnectionPool.from_url(
                settings.redis.redis_url,
                max_connections=settings.redis.redis_max_connections,
                retry_on_timeout=settings.redis.redis_retry_on_timeout,
                socket_timeout=settings.redis.redis_socket_timeout
            )

            self.redis_client = redis.Redis(
                connection_pool=self._connection_pool,
                decode_responses=True
            )

            # Test connection
            await self.redis_client.ping()
            logger.info("Redis session manager initialized successfully")

        except RedisError as e:
            logger.error(f"Failed to initialize Redis session manager: {e}")
            raise SessionError(f"Redis initialization failed: {e}")

    async def close(self) -> None:
        """Close Redis connections."""
        if self.redis_client:
            await self.redis_client.close()
        if self._connection_pool:
            await self._connection_pool.disconnect()
        logger.info("Redis session manager closed")

    def _get_session_key(self, user_id: int) -> str:
        """Generate Redis key for user session."""
        return f"f1:session:user:{user_id}"

    def _get_rate_limit_key(self, user_id: int) -> str:
        """Generate Redis key for rate limiting."""
        return f"f1:rate_limit:user:{user_id}"

    def _get_cache_key(self, cache_type: str, identifier: str) -> str:
        """Generate Redis key for caching."""
        return f"f1:cache:{cache_type}:{identifier}"

    async def create_session(
        self,
        user_id: int,
        email: str,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None,
        additional_data: Optional[Dict[str, Any]] = None
    ) -> UserSession:
        """
        Create a new user session.

        Args:
            user_id: User's database ID
            email: User's email address
            ip_address: Client IP address
            user_agent: Client user agent string
            additional_data: Additional session data

        Returns:
            UserSession: Created session object
        """
        if not self.redis_client:
            raise SessionError("Session manager not initialized")

        now = datetime.now(timezone.utc)
        session = UserSession(
            user_id=user_id,
            email=email,
            created_at=now,
            last_accessed=now,
            ip_address=ip_address,
            user_agent=user_agent,
            additional_data=additional_data or {}
        )

        try:
            session_key = self._get_session_key(user_id)
            session_data = json.dumps(session.to_dict())

            # Store session with TTL of 24 hours
            await self.redis_client.setex(
                session_key,
                timedelta(hours=24),
                session_data
            )

            logger.debug(f"Session created for user {user_id}")
            return session

        except RedisError as e:
            logger.error(f"Failed to create session for user {user_id}: {e}")
            raise SessionError(f"Session creation failed: {e}")

    async def get_session(self, user_id: int) -> Optional[UserSession]:
        """
        Retrieve user session.

        Args:
            user_id: User's database ID

        Returns:
            UserSession or None: User session if exists and valid
        """
        if not self.redis_client:
            raise SessionError("Session manager not initialized")

        try:
            session_key = self._get_session_key(user_id)
            session_data = await self.redis_client.get(session_key)

            if not session_data:
                return None

            session_dict = json.loads(session_data)
            session = UserSession.from_dict(session_dict)

            # Update last accessed time
            await self.update_session_access(user_id)

            return session

        except (RedisError, json.JSONDecodeError, ValueError) as e:
            logger.error(f"Failed to get session for user {user_id}: {e}")
            return None

    async def update_session_access(self, user_id: int) -> bool:
        """
        Update session last accessed time.

        Args:
            user_id: User's database ID

        Returns:
            bool: True if session was updated
        """
        if not self.redis_client:
            raise SessionError("Session manager not initialized")

        try:
            session_key = self._get_session_key(user_id)
            session_data = await self.redis_client.get(session_key)

            if not session_data:
                return False

            session_dict = json.loads(session_data)
            session_dict["last_accessed"] = datetime.now(timezone.utc).isoformat()

            updated_data = json.dumps(session_dict)
            await self.redis_client.setex(
                session_key,
                timedelta(hours=24),
                updated_data
            )

            return True

        except (RedisError, json.JSONDecodeError) as e:
            logger.error(f"Failed to update session access for user {user_id}: {e}")
            return False

    async def delete_session(self, user_id: int) -> bool:
        """
        Delete user session (logout).

        Args:
            user_id: User's database ID

        Returns:
            bool: True if session was deleted
        """
        if not self.redis_client:
            raise SessionError("Session manager not initialized")

        try:
            session_key = self._get_session_key(user_id)
            result = await self.redis_client.delete(session_key)

            if result:
                logger.debug(f"Session deleted for user {user_id}")

            return bool(result)

        except RedisError as e:
            logger.error(f"Failed to delete session for user {user_id}: {e}")
            return False

    async def check_rate_limit(self, user_id: int) -> Dict[str, Any]:
        """
        Check and update rate limiting for user.

        Args:
            user_id: User's database ID

        Returns:
            dict: Rate limit information
        """
        if not self.redis_client:
            raise SessionError("Session manager not initialized")

        try:
            rate_limit_key = self._get_rate_limit_key(user_id)
            window_seconds = settings.app.rate_limit_window
            max_requests = settings.app.rate_limit_requests

            # Use Redis pipeline for atomic operations
            pipe = self.redis_client.pipeline()
            pipe.incr(rate_limit_key)
            pipe.expire(rate_limit_key, window_seconds)
            results = await pipe.execute()

            current_requests = results[0]
            remaining = max(0, max_requests - current_requests)

            return {
                "allowed": current_requests <= max_requests,
                "current_requests": current_requests,
                "max_requests": max_requests,
                "remaining_requests": remaining,
                "window_seconds": window_seconds,
                "reset_time": datetime.now(timezone.utc) + timedelta(seconds=window_seconds)
            }

        except RedisError as e:
            logger.error(f"Failed to check rate limit for user {user_id}: {e}")
            # Allow request if Redis is down (fail open)
            return {
                "allowed": True,
                "error": str(e)
            }

    async def cache_data(
        self,
        cache_type: str,
        identifier: str,
        data: Any,
        ttl_seconds: Optional[int] = None
    ) -> bool:
        """
        Cache data in Redis.

        Args:
            cache_type: Type of cached data (e.g., 'predictions', 'races')
            identifier: Unique identifier for the cached item
            data: Data to cache (will be JSON serialized)
            ttl_seconds: TTL in seconds (uses default if None)

        Returns:
            bool: True if caching was successful
        """
        if not self.redis_client:
            raise SessionError("Session manager not initialized")

        # Set default TTL based on cache type
        if ttl_seconds is None:
            ttl_map = {
                'predictions': settings.redis.prediction_cache_ttl,
                'races': settings.redis.race_calendar_ttl,
                'rankings': settings.redis.driver_rankings_ttl
            }
            ttl_seconds = ttl_map.get(cache_type, 3600)  # Default 1 hour

        try:
            cache_key = self._get_cache_key(cache_type, identifier)
            cached_data = json.dumps(data, default=str)  # default=str for datetime serialization

            await self.redis_client.setex(cache_key, ttl_seconds, cached_data)
            logger.debug(f"Cached {cache_type} data for {identifier}")
            return True

        except (RedisError, TypeError) as e:
            logger.error(f"Failed to cache {cache_type} data for {identifier}: {e}")
            return False

    async def get_cached_data(self, cache_type: str, identifier: str) -> Optional[Any]:
        """
        Retrieve cached data from Redis.

        Args:
            cache_type: Type of cached data
            identifier: Unique identifier for the cached item

        Returns:
            Cached data or None if not found
        """
        if not self.redis_client:
            raise SessionError("Session manager not initialized")

        try:
            cache_key = self._get_cache_key(cache_type, identifier)
            cached_data = await self.redis_client.get(cache_key)

            if cached_data:
                return json.loads(cached_data)

            return None

        except (RedisError, json.JSONDecodeError) as e:
            logger.error(f"Failed to get cached {cache_type} data for {identifier}: {e}")
            return None

    async def invalidate_cache(self, cache_type: str, identifier: str) -> bool:
        """
        Invalidate cached data.

        Args:
            cache_type: Type of cached data
            identifier: Unique identifier for the cached item

        Returns:
            bool: True if cache was invalidated
        """
        if not self.redis_client:
            raise SessionError("Session manager not initialized")

        try:
            cache_key = self._get_cache_key(cache_type, identifier)
            result = await self.redis_client.delete(cache_key)

            if result:
                logger.debug(f"Invalidated {cache_type} cache for {identifier}")

            return bool(result)

        except RedisError as e:
            logger.error(f"Failed to invalidate {cache_type} cache for {identifier}: {e}")
            return False

    async def get_active_sessions_count(self) -> int:
        """Get count of active sessions."""
        if not self.redis_client:
            raise SessionError("Session manager not initialized")

        try:
            pattern = "f1:session:user:*"
            keys = await self.redis_client.keys(pattern)
            return len(keys)

        except RedisError as e:
            logger.error(f"Failed to get active sessions count: {e}")
            return 0

    async def health_check(self) -> Dict[str, Any]:
        """
        Perform health check on session manager.

        Returns:
            dict: Health check results
        """
        try:
            if not self.redis_client:
                return {
                    "status": "unhealthy",
                    "error": "Session manager not initialized"
                }

            # Test Redis connection
            await self.redis_client.ping()

            # Get basic stats
            info = await self.redis_client.info('memory')
            active_sessions = await self.get_active_sessions_count()

            return {
                "status": "healthy",
                "redis_connected": True,
                "active_sessions": active_sessions,
                "memory_usage": info.get('used_memory_human', 'unknown'),
                "timestamp": datetime.now(timezone.utc).isoformat()
            }

        except Exception as e:
            return {
                "status": "unhealthy",
                "error": str(e),
                "timestamp": datetime.now(timezone.utc).isoformat()
            }


class SessionError(Exception):
    """Base exception for session operations."""
    pass


# Global session manager instance
session_manager = SessionManager()