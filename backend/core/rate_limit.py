"""
Shared SlowAPI rate limiter instance.
Import `limiter` from here to apply @limiter.limit() decorators
on any endpoint without circular imports from main.py.
"""
from slowapi import Limiter
from slowapi.util import get_remote_address

limiter = Limiter(key_func=get_remote_address)
