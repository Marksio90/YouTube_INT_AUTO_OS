"""
Redis connection manager — shared async pool, health check, and token blacklist.

Provides:
- A singleton connection pool initialized on app startup
- `get_redis()` for direct access anywhere in the app
- `redis_health_check()` for the /health endpoint
- Token blacklist for JWT revocation (logout)
"""
from __future__ import annotations

import structlog
import redis.asyncio as aioredis

from core.config import settings

logger = structlog.get_logger(__name__)

_BLACKLIST_PREFIX = "token_blacklist:"

# Module-level singleton — set by init_redis(), cleared by close_redis()
_redis_client: aioredis.Redis | None = None


# ============================================================
# Lifecycle
# ============================================================

async def init_redis() -> None:
    """Initialize the shared Redis connection pool. Called on app startup.

    If a client is already set (e.g. injected by tests), this is a no-op.
    """
    global _redis_client
    if _redis_client is not None:
        return  # Already initialized — preserve test injection or prior setup
    _redis_client = aioredis.from_url(
        settings.redis_url,
        decode_responses=True,
        socket_connect_timeout=2,
        socket_keepalive=True,
        health_check_interval=30,
    )
    await _redis_client.ping()
    logger.info("Redis connection pool initialized", url=settings.redis_url)


async def close_redis() -> None:
    """Close the shared Redis connection pool. Called on app shutdown."""
    global _redis_client
    if _redis_client is not None:
        await _redis_client.aclose()
        _redis_client = None
        logger.info("Redis connection pool closed")


# ============================================================
# Access
# ============================================================

def get_redis() -> aioredis.Redis:
    """Return the shared Redis client. Raises RuntimeError if not initialized."""
    if _redis_client is None:
        raise RuntimeError("Redis not initialized — call init_redis() first")
    return _redis_client


async def redis_health_check() -> bool:
    """Ping Redis and return True if reachable."""
    try:
        return bool(await get_redis().ping())
    except Exception:
        return False


# ============================================================
# Token blacklist (JWT revocation for logout)
# ============================================================

async def blacklist_token(token: str, ttl_seconds: int) -> None:
    """
    Add a JWT to the revocation blacklist with a TTL matching its remaining lifetime.
    Subsequent requests bearing this token will be rejected by get_current_user().
    """
    key = f"{_BLACKLIST_PREFIX}{token}"
    await get_redis().setex(key, ttl_seconds, "1")
    logger.debug("Token blacklisted", ttl=ttl_seconds)


async def is_token_blacklisted(token: str) -> bool:
    """Return True if the token has been revoked."""
    key = f"{_BLACKLIST_PREFIX}{token}"
    return bool(await get_redis().exists(key))
