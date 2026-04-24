import hashlib
from datetime import datetime, timedelta, timezone
from typing import Any

from jose import JWTError, jwt
from passlib.context import CryptContext
from redis.asyncio import Redis

from app.core.config import settings

# SECURITY: bcrypt with default cost factor (12)
_pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

_BLACKLIST_PREFIX = "token:blacklist:"


# ── Password ──────────────────────────────────────────────────────────────────

def hash_password(password: str) -> str:
    return _pwd_context.hash(password)


def verify_password(plain: str, hashed: str) -> bool:
    return _pwd_context.verify(plain, hashed)


# ── JWT ───────────────────────────────────────────────────────────────────────

def _make_token(data: dict[str, Any], delta: timedelta) -> str:
    payload = {**data, "exp": datetime.now(timezone.utc) + delta}
    return jwt.encode(payload, settings.SECRET_KEY, algorithm=settings.ALGORITHM)


def create_access_token(data: dict[str, Any], expires_delta: timedelta | None = None) -> str:
    """Short-lived access token (default 15 min)."""
    delta = expires_delta or timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    return _make_token({**data, "type": "access"}, delta)


def create_refresh_token(data: dict[str, Any]) -> str:
    """Long-lived refresh token (7 days). Single-use — rotated on each use."""
    delta = timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS)
    return _make_token({**data, "type": "refresh"}, delta)


def decode_token(token: str) -> dict[str, Any]:
    """Decode and verify a JWT. Raises JWTError on failure."""
    return jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])


# ── Redis token blacklist ─────────────────────────────────────────────────────

def _bl_key(token: str) -> str:
    digest = hashlib.sha256(token.encode()).hexdigest()
    return f"{_BLACKLIST_PREFIX}{digest}"


async def add_token_to_blacklist(token: str, redis: Redis) -> None:
    """Revoke a token until its natural expiry."""
    try:
        payload = decode_token(token)
        exp: int | None = payload.get("exp")
        ttl = max(int(exp - datetime.now(timezone.utc).timestamp()), 1) if exp else (
            settings.REFRESH_TOKEN_EXPIRE_DAYS * 86400
        )
        await redis.setex(_bl_key(token), ttl, "1")
    except JWTError:
        pass  # already invalid


async def is_token_blacklisted(token: str, redis: Redis) -> bool:
    return bool(await redis.exists(_bl_key(token)))
