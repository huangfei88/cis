import logging
import time
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request, Response, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.api import auth, scripts, tasks, admin, servers, credentials
from app.core.config import settings
from app.core.database import init_db

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("CIS backend starting (env=%s)", settings.APP_ENV)
    await init_db()
    yield
    logger.info("CIS backend shutting down")


app = FastAPI(
    title="CIS — Centralised Infra Script Platform",
    version="1.0.0",
    # SECURITY: disable interactive docs in production
    docs_url="/docs" if settings.APP_ENV != "production" else None,
    redoc_url="/redoc" if settings.APP_ENV != "production" else None,
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    allow_headers=["Authorization", "Content-Type", "X-Requested-With"],
)

app.include_router(auth.router,        prefix="/api/v1")
app.include_router(scripts.router,     prefix="/api/v1")
app.include_router(tasks.router,       prefix="/api/v1")
app.include_router(admin.router,       prefix="/api/v1")
app.include_router(servers.router,     prefix="/api/v1")
app.include_router(credentials.router, prefix="/api/v1")


@app.middleware("http")
async def audit_middleware(request: Request, call_next) -> Response:
    start = time.monotonic()
    try:
        response: Response = await call_next(request)
    except Exception as exc:
        logger.exception("Unhandled exception: %s", exc)
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={"detail": "Internal server error"},
        )
    elapsed = round((time.monotonic() - start) * 1000, 1)
    logger.info("%s %s → %d (%.1fms)", request.method, request.url.path, response.status_code, elapsed)
    response.headers["X-Process-Time-Ms"] = str(elapsed)
    return response


@app.get("/health", include_in_schema=False)
async def health() -> dict:
    return {"status": "ok"}
