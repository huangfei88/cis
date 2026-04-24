from typing import Annotated
import uuid

from fastapi import Depends, HTTPException, Request, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jose import JWTError
from redis.asyncio import Redis
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from app.core.config import settings
from app.core.database import get_db
from app.core.security import decode_token, is_token_blacklisted

_bearer = HTTPBearer(auto_error=True)


async def get_redis() -> Redis:  # type: ignore[return]
    """Yield a Redis client. Caller must not close it (handled by the pool)."""
    client = Redis.from_url(settings.REDIS_URL, decode_responses=True)
    try:
        yield client
    finally:
        await client.aclose()


async def get_current_user(
    credentials: Annotated[HTTPAuthorizationCredentials, Depends(_bearer)],
    db: Annotated[AsyncSession, Depends(get_db)],
    redis: Annotated[Redis, Depends(get_redis)],
):
    from app.models.user import User

    token = credentials.credentials
    exc = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Invalid or expired token",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = decode_token(token)
    except JWTError:
        raise exc

    if payload.get("type") != "access":
        raise exc

    if await is_token_blacklisted(token, redis):
        raise exc

    user_id: str | None = payload.get("sub")
    if not user_id:
        raise exc

    try:
        user_uuid = uuid.UUID(user_id)
    except ValueError:
        raise exc

    result = await db.execute(select(User).where(User.id == user_uuid))
    user: User | None = result.scalar_one_or_none()
    if not user or not user.is_active:
        raise exc

    return user


def require_role(*roles: str):
    """Dependency factory that enforces role membership."""
    async def _check(
        current_user=Depends(get_current_user),
    ):
        if current_user.role.value not in roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Requires one of roles: {roles}",
            )
        return current_user
    return _check


def get_client_ip(request: Request) -> str:
    # SECURITY: prefer X-Real-IP which nginx sets to $remote_addr (the actual
    # connecting socket IP).  X-Forwarded-For is NOT used here because an
    # attacker can prepend arbitrary values to it; using the first element
    # would allow IP spoofing in audit logs.
    real_ip = request.headers.get("X-Real-IP")
    if real_ip:
        return real_ip.strip()
    return request.client.host if request.client else "unknown"
