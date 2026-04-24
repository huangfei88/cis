from __future__ import annotations

from pydantic import BaseModel, EmailStr, field_validator


class RegisterRequest(BaseModel):
    username: str
    email: EmailStr
    password: str

    @field_validator("password")
    @classmethod
    def password_strength(cls, v: str) -> str:
        if len(v) < 12:
            raise ValueError("Password must be at least 12 characters")
        # SECURITY: cap bcrypt input — bcrypt silently truncates at 72 bytes,
        # but an extremely long password (e.g. 1 MiB) is a CPU-DoS vector.
        if len(v) > 128:
            raise ValueError("Password must be at most 128 characters")
        if not any(c.isupper() for c in v):
            raise ValueError("Password must contain at least one uppercase letter")
        if not any(c.islower() for c in v):
            raise ValueError("Password must contain at least one lowercase letter")
        if not any(c.isdigit() for c in v):
            raise ValueError("Password must contain at least one digit")
        special = set('!@#$%^&*()_+-=[]{}|;:\'",.<>?/`~\\')
        if not any(c in special for c in v):
            raise ValueError("Password must contain at least one special character")
        return v

    @field_validator("username")
    @classmethod
    def username_alnum(cls, v: str) -> str:
        if len(v) > 64:
            raise ValueError("Username must be at most 64 characters")
        if not v.replace("_", "").replace("-", "").isalnum():
            raise ValueError("Username may only contain letters, digits, _ and -")
        return v


class LoginRequest(BaseModel):
    username: str
    password: str
    mfa_code: str | None = None


class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int


class RefreshRequest(BaseModel):
    refresh_token: str


class MfaSetupResponse(BaseModel):
    uri: str


class MfaEnableRequest(BaseModel):
    code: str


class MfaDisableRequest(BaseModel):
    code: str


class ChangePasswordRequest(BaseModel):
    current_password: str
    new_password: str

    @field_validator("new_password")
    @classmethod
    def new_password_strength(cls, v: str) -> str:
        if len(v) < 12:
            raise ValueError("Password must be at least 12 characters")
        if len(v) > 128:
            raise ValueError("Password must be at most 128 characters")
        if not any(c.isupper() for c in v):
            raise ValueError("Password must contain at least one uppercase letter")
        if not any(c.islower() for c in v):
            raise ValueError("Password must contain at least one lowercase letter")
        if not any(c.isdigit() for c in v):
            raise ValueError("Password must contain at least one digit")
        special = set('!@#$%^&*()_+-=[]{}|;:\'",.<>?/`~\\')
        if not any(c in special for c in v):
            raise ValueError("Password must contain at least one special character")
        return v
