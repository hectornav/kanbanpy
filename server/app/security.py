"""
security.py - Password/secret hashing (argon2) and JWT helpers.

Replaces the old unsalted single-round SHA-256 scheme. Passwords and security
answers are hashed with argon2id (per-hash random salt, memory-hard).
"""
from datetime import datetime, timedelta, timezone

import jwt
from argon2 import PasswordHasher
from argon2.exceptions import VerifyMismatchError, InvalidHashError

from .config import SECRET_KEY, settings

_ph = PasswordHasher()
_ALGORITHM = "HS256"


def hash_secret(raw: str) -> str:
    """Hash a password or security answer with argon2id."""
    return _ph.hash(raw)


def verify_secret(raw: str, hashed: str) -> bool:
    """Constant-time verification. Returns False on any mismatch or bad hash."""
    try:
        return _ph.verify(hashed, raw)
    except (VerifyMismatchError, InvalidHashError, Exception):
        return False


def needs_rehash(hashed: str) -> bool:
    """True if the stored hash uses outdated argon2 parameters."""
    try:
        return _ph.check_needs_rehash(hashed)
    except Exception:
        return True


def create_access_token(subject: str | int) -> str:
    """Create a signed JWT carrying the user id as `sub`."""
    expire = datetime.now(timezone.utc) + timedelta(minutes=settings.access_token_expire_minutes)
    payload = {"sub": str(subject), "exp": expire, "iat": datetime.now(timezone.utc)}
    return jwt.encode(payload, SECRET_KEY, algorithm=_ALGORITHM)


def decode_access_token(token: str) -> int | None:
    """Return the user id from a valid token, or None if invalid/expired."""
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[_ALGORITHM])
        sub = payload.get("sub")
        return int(sub) if sub is not None else None
    except (jwt.PyJWTError, ValueError):
        return None
