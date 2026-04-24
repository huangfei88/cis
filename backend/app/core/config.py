from __future__ import annotations

from typing import List

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    APP_ENV: str = "development"

    # Database
    DATABASE_URL: str = "postgresql+asyncpg://cis:cis@localhost:5432/cis"

    # Redis
    REDIS_URL: str = "redis://localhost:6379/0"

    # JWT
    SECRET_KEY: str = "change-me-in-production-use-a-long-random-string"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 15
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7

    # MinIO
    MINIO_ENDPOINT: str = "localhost:9000"
    MINIO_ACCESS_KEY: str = "minioadmin"
    MINIO_SECRET_KEY: str = "minioadmin"
    MINIO_BUCKET: str = "cis-scripts"
    MINIO_SECURE: bool = False

    # Docker / execution sandbox
    DOCKER_SOCKET: str = "/var/run/docker.sock"
    EXECUTION_IMAGE: str = "cis-runner:latest"
    TASK_TIMEOUT: int = 300          # seconds; Docker-level hard kill timeout
    MAX_MEMORY: str = "256m"
    MAX_CPUS: float = 0.5
    # Seccomp profile path inside the worker container (mounted via docker-compose)
    SECCOMP_PROFILE_PATH: str = "/etc/seccomp/profile.json"
    # AppArmor profile name loaded on the Docker host; empty string = disabled
    APPARMOR_PROFILE: str = ""

    # CORS
    ALLOWED_ORIGINS: List[str] = ["http://localhost:3000", "https://localhost"]

    # Credential encryption (32-byte key as 64 hex chars, MUST be overridden in production)
    CREDENTIAL_MASTER_KEY: str = "0" * 64
    # Session / lockout settings
    MAX_ACTIVE_SESSIONS: int = 3
    PASSWORD_MAX_AGE_DAYS: int = 90
    ACCOUNT_LOCKOUT_ATTEMPTS: int = 5
    ACCOUNT_LOCKOUT_MINUTES: int = 15


settings = Settings()
