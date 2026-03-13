"""
Redis-backed LLM response cache.

Caches LLM responses by SHA-256(model + prompt) to avoid redundant API calls
for identical inputs (e.g. repeated niche analysis, scoring of same hook text).

Usage:
    from utils.llm_cache import get_cached_response, cache_response, make_cache_key

    key = make_cache_key(prompt="...", model="gpt-4o-mini")
    cached = await get_cached_response(key)
    if cached:
        return cached

    result = await llm.ainvoke(prompt)
    await cache_response(key, result, ttl=3600)
    return result

Or use the decorator:
    @cached_llm_call(ttl=3600)
    async def my_llm_call(prompt: str, model: str) -> str:
        ...
"""
from __future__ import annotations

import hashlib
import json
import functools
from typing import Optional, Callable, Any

import structlog

from core.config import settings

logger = structlog.get_logger(__name__)

_CACHE_PREFIX = "llm_cache:"
_DEFAULT_TTL = 3600  # 1 hour


def make_cache_key(prompt: str, model: str) -> str:
    """Generate a deterministic Redis key from model + prompt."""
    content = f"{model}:{prompt}"
    digest = hashlib.sha256(content.encode("utf-8")).hexdigest()
    return f"{_CACHE_PREFIX}{digest}"


async def _get_redis_client():
    import redis.asyncio as aioredis
    return aioredis.from_url(
        settings.redis_url,
        decode_responses=True,
        socket_connect_timeout=1,
    )


async def get_cached_response(cache_key: str) -> Optional[str]:
    """
    Retrieve a cached LLM response string from Redis.
    Returns None if cache miss or Redis unavailable.
    """
    try:
        client = await _get_redis_client()
        async with client:
            value = await client.get(cache_key)
            if value:
                logger.debug("LLM cache hit", key=cache_key[:32])
                return value
    except Exception as e:
        logger.debug("LLM cache read failed (non-critical)", error=str(e))
    return None


async def cache_response(cache_key: str, response: str, ttl: int = _DEFAULT_TTL) -> None:
    """
    Store an LLM response string in Redis with TTL.
    Silently ignores Redis failures — caching is best-effort.
    """
    try:
        client = await _get_redis_client()
        async with client:
            await client.setex(cache_key, ttl, response)
            logger.debug("LLM response cached", key=cache_key[:32], ttl=ttl)
    except Exception as e:
        logger.debug("LLM cache write failed (non-critical)", error=str(e))


def cached_llm_call(ttl: int = _DEFAULT_TTL):
    """
    Decorator for async LLM functions. Caches by (prompt, model) arguments.

    The decorated function must accept `prompt: str` and `model: str` kwargs
    (or positional args in that order).

    Example:
        @cached_llm_call(ttl=1800)
        async def score_hook(prompt: str, model: str) -> str:
            ...
    """
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        async def wrapper(*args, **kwargs) -> Any:
            # Extract prompt and model for cache key
            prompt = kwargs.get("prompt") or (args[0] if args else "")
            model = kwargs.get("model") or (args[1] if len(args) > 1 else "unknown")
            key = make_cache_key(str(prompt), str(model))

            cached = await get_cached_response(key)
            if cached is not None:
                return cached

            result = await func(*args, **kwargs)

            # Only cache string results
            if isinstance(result, str):
                await cache_response(key, result, ttl=ttl)

            return result
        return wrapper
    return decorator
