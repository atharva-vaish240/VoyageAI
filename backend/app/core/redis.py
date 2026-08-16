"""Redis client configuration and connection management."""

import logging
from typing import Optional

import redis

from app.core.config import get_settings

logger = logging.getLogger(__name__)

_redis_client: Optional[redis.Redis] = None


def get_redis_client() -> Optional[redis.Redis]:
    """Get or initialize the singleton Redis client.

    Returns None if Redis is not configured or fails to initialize.
    """
    global _redis_client
    settings = get_settings()

    if not settings.REDIS_URL:
        return None

    if _redis_client is None:
        try:
            _redis_client = redis.from_url(
                settings.REDIS_URL,
                decode_responses=True,
                socket_connect_timeout=1.0,
                socket_timeout=1.0,
            )
        except Exception as e:
            logger.warning(f"Failed to initialize Redis client: {e}")
            return None

    return _redis_client


def close_redis_client() -> None:
    """Close the Redis client connection if open."""
    global _redis_client
    if _redis_client is not None:
        try:
            _redis_client.close()
        except Exception as e:
            logger.warning(f"Error closing Redis client: {e}")
        finally:
            _redis_client = None
