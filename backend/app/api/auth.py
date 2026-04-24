from __future__ import annotations

import uuid
from datetime import datetime, timedelta, timezone
from typing import Annotated

import pyotp
from fastapi import APIRouter, Depends, HTTPException, Request, status
from jose import JWTError
from redis.asyncio import Redis
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from app.core.config import settings
from app.core.database import get_db
from app.core.deps import get_client_ip, get_current_user, get_redis
from app.core.security import (
    add_token_to_blacklist,
    create_access_token,
    create_refresh_token,
    decode_token,
    hash_password,
    is_token_blacklisted,
    verify_password,
)
from app.models.user import User
from app.schemas.auth import (
    ChangePasswordRequest,
    LoginRequest,
    MfaDisableRequest,
    MfaEnableRequest,
    MfaSetupResponse,
    RefreshRequest,
    RegisterRequest,
    TokenResponse,
)
from app.services.audit_service import AuditService

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/register", status_code=status.HTTP_201_CREATED)
async def register(
    payload: RegisterRequest,
    request: Request,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> dict:
    existing = await db.execute(
        select(User).where(
            (User.username == payload.username) | (User.email == payload.email)
        )
    )
    if existing.scalar_one_or_none():
        raise HTTPException(status_code=409, detail="Username or email already registered")
    user = User(
        username=payload.username,
        email=payload.email,
        hashed_password=hash_password(payload.password),
        password_changed_at=datetime.now(timezone.utc),
    )
    db.add(user)
    await db.flush()
    await AuditService.log_action(
        db,
        action="user.register",
        user_id=user.id,
        resource_type="user",
        resource_id=str(user.id),
        ip_address=get_client_ip(request),
        user_agent=request.headers.get("User-Agent"),
        request_path=request.url.path,
        request_method=request.method,
        status_code=201,
        result="success",
    )
    return {"message": "Registration successful", "user_id": str(user.id)}


@router.post("/login")
async def login(
    payload: LoginRequest,
    request: Request,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> dict:
    result = await db.execute(select(User).where(User.username == payload.username))
    user: User | None = result.scalar_one_or_none()

    async def _audit_failure(detail_dict: dict | None = None) -> None:
        await AuditService.log_action(
            db,
            action="user.login.failed",
            ip_address=get_client_ip(request),
            user_agent=request.headers.get("User-Agent"),
            request_path=request.url.path,
            request_method=request.method,
            status_code=401,
            result="failure",
            detail=detail_dict,
        )

    if not user:
        await _audit_failure({"attempted_username": payload.username})
        raise HTTPException(status_code=401, detail="Invalid credentials")

    # Account lockout check
    now = datetime.now(timezone.utc)
    if user.locked_until and user.locked_until > now:
        retry_after = int((user.locked_until - now).total_seconds())
        raise HTTPException(
            status_code=429,
            detail=f"Account locked. Try again in {retry_after} seconds.",
        )

    if not user.is_active:
        raise HTTPException(status_code=403, detail="Account is disabled")

    if not verify_password(payload.password, user.hashed_password):
        user.failed_login_attempts = (user.failed_login_attempts or 0) + 1
        if user.failed_login_attempts >= settings.ACCOUNT_LOCKOUT_ATTEMPTS:
            user.locked_until = now + timedelta(minutes=settings.ACCOUNT_LOCKOUT_MINUTES)
        await db.flush()
        await _audit_failure({"attempted_username": payload.username})
        raise HTTPException(status_code=401, detail="Invalid credentials")

    # Password age check
    if user.password_changed_at is not None:
        age_days = (now - user.password_changed_at).days
        if age_days > settings.PASSWORD_MAX_AGE_DAYS:
            raise HTTPException(
                status_code=403,
                detail="Password expired, please change your password",
            )

    # MFA check
    if user.mfa_enabled:
        if not payload.mfa_code:
            # Password is correct but MFA code not provided yet
            return {"mfa_required": True}
        if not pyotp.TOTP(user.mfa_secret).verify(payload.mfa_code, valid_window=1):
            await _audit_failure({"attempted_username": payload.username, "reason": "mfa_failed"})
            raise HTTPException(status_code=401, detail="Invalid MFA code")

    # Successful login
    user.failed_login_attempts = 0
    user.locked_until = None
    user.last_login_at = now
    await db.flush()

    token_data = {"sub": str(user.id), "username": user.username, "role": user.role}
    access_token = create_access_token(token_data)
    refresh_token = create_refresh_token(token_data)

    await AuditService.log_action(
        db,
        action="user.login",
        user_id=user.id,
        resource_type="user",
        resource_id=str(user.id),
        ip_address=get_client_ip(request),
        user_agent=request.headers.get("User-Agent"),
        request_path=request.url.path,
        request_method=request.method,
        status_code=200,
        result="success",
    )
    return TokenResponse(
        access_token=access_token,
        refresh_token=refresh_token,
        expires_in=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
    )


@router.post("/refresh", response_model=TokenResponse)
async def refresh(
    payload: RefreshRequest,
    db: Annotated[AsyncSession, Depends(get_db)],
    redis: Annotated[Redis, Depends(get_redis)],
) -> TokenResponse:
    try:
        claims = decode_token(payload.refresh_token)
    except JWTError:
        raise HTTPException(status_code=401, detail="Invalid or expired refresh token")
    if claims.get("type") != "refresh":
        raise HTTPException(status_code=401, detail="Token type mismatch")
    if await is_token_blacklisted(payload.refresh_token, redis):
        raise HTTPException(status_code=401, detail="Refresh token revoked")
    sub: str | None = claims.get("sub")
    if not sub:
        raise HTTPException(status_code=401, detail="Invalid token payload")
    try:
        user_uuid = uuid.UUID(sub)
    except ValueError:
        raise HTTPException(status_code=401, detail="Invalid token payload")
    result = await db.execute(select(User).where(User.id == user_uuid))
    user: User | None = result.scalar_one_or_none()
    if not user or not user.is_active:
        raise HTTPException(status_code=401, detail="User not found")
    await add_token_to_blacklist(payload.refresh_token, redis)
    token_data = {"sub": str(user.id), "username": user.username, "role": user.role}
    return TokenResponse(
        access_token=create_access_token(token_data),
        refresh_token=create_refresh_token(token_data),
        expires_in=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
    )


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
async def logout(
    request: Request,
    db: Annotated[AsyncSession, Depends(get_db)],
    redis: Annotated[Redis, Depends(get_redis)],
    current_user: Annotated[User, Depends(get_current_user)],
) -> None:
    token = request.headers.get("Authorization", "").removeprefix("Bearer ").strip()
    await add_token_to_blacklist(token, redis)
    await AuditService.log_action(
        db,
        action="user.logout",
        user_id=current_user.id,
        ip_address=get_client_ip(request),
        request_path=request.url.path,
        request_method=request.method,
        status_code=204,
        result="success",
    )


# ---------------------------------------------------------------------------
# MFA endpoints
# ---------------------------------------------------------------------------

@router.post("/mfa/setup", response_model=MfaSetupResponse)
async def mfa_setup(
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
) -> MfaSetupResponse:
    secret = pyotp.random_base32()
    current_user.mfa_secret = secret
    await db.flush()
    uri = pyotp.TOTP(secret).provisioning_uri(name=current_user.email, issuer_name="CIS")
    return MfaSetupResponse(uri=uri)


@router.post("/mfa/enable", status_code=status.HTTP_204_NO_CONTENT)
async def mfa_enable(
    payload: MfaEnableRequest,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
) -> None:
    if not current_user.mfa_secret:
        raise HTTPException(status_code=400, detail="MFA not set up. Call /auth/mfa/setup first.")
    if not pyotp.TOTP(current_user.mfa_secret).verify(payload.code, valid_window=1):
        raise HTTPException(status_code=400, detail="Invalid MFA code")
    current_user.mfa_enabled = True
    await db.flush()


@router.post("/mfa/disable", status_code=status.HTTP_204_NO_CONTENT)
async def mfa_disable(
    payload: MfaDisableRequest,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
) -> None:
    if not current_user.mfa_enabled:
        raise HTTPException(status_code=400, detail="MFA is not enabled")
    if not pyotp.TOTP(current_user.mfa_secret).verify(payload.code, valid_window=1):
        raise HTTPException(status_code=400, detail="Invalid MFA code")
    current_user.mfa_enabled = False
    current_user.mfa_secret = None
    await db.flush()


# ---------------------------------------------------------------------------
# Change password
# ---------------------------------------------------------------------------

@router.post("/change-password", status_code=status.HTTP_204_NO_CONTENT)
async def change_password(
    payload: ChangePasswordRequest,
    request: Request,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
) -> None:
    if not verify_password(payload.current_password, current_user.hashed_password):
        await AuditService.log_action(
            db,
            action="user.change_password.failed",
            user_id=current_user.id,
            ip_address=get_client_ip(request),
            request_path=request.url.path,
            request_method=request.method,
            status_code=400,
            result="failure",
        )
        raise HTTPException(status_code=400, detail="Current password is incorrect")
    current_user.hashed_password = hash_password(payload.new_password)
    current_user.password_changed_at = datetime.now(timezone.utc)
    await db.flush()
    await AuditService.log_action(
        db,
        action="user.change_password",
        user_id=current_user.id,
        resource_type="user",
        resource_id=str(current_user.id),
        ip_address=get_client_ip(request),
        request_path=request.url.path,
        request_method=request.method,
        status_code=204,
        result="success",
    )
