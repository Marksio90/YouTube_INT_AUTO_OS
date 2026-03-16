"""
Shared SlowAPI rate limiter instance — backed by Redis for distributed deployments.
Import `limiter` from here to apply @limiter.limit() decorators
on any endpoint without circular imports from main.py.
"""
from slowapi import Limiter
from slowapi.util import get_remote_address

from core.config import settings

limiter = Limiter(
    key_func=get_remote_address,
    storage_uri=settings.redis_url,
)
