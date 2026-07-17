"""
ratelimit.py - In-memory login brute-force protection.

Tracks failed attempts per key (username) in a sliding window and locks the
account for a cooldown once the threshold is hit. Suitable for a single-process
family instance; swap for Redis if you ever run multiple workers.
"""
import time
from collections import defaultdict

from .config import settings

_failures: dict[str, list[float]] = defaultdict(list)
_locked_until: dict[str, float] = {}


def seconds_locked(key: str) -> int:
    """Return remaining lock time in seconds, or 0 if not locked."""
    remaining = _locked_until.get(key, 0) - time.time()
    return int(remaining) if remaining > 0 else 0


def record_failure(key: str) -> None:
    now = time.time()
    window = settings.login_lock_minutes * 60
    recent = [t for t in _failures[key] if now - t < window]
    recent.append(now)
    _failures[key] = recent
    if len(recent) >= settings.login_max_attempts:
        _locked_until[key] = now + window
        _failures[key] = []


def reset(key: str) -> None:
    _failures.pop(key, None)
    _locked_until.pop(key, None)
