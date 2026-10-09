"""FastAPI application: middleware, rate limiting, router registration, and dashboard hosting."""
import logging
import time
import uuid
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from slowapi.errors import RateLimitExceeded
from slowapi.middleware import SlowAPIMiddleware
from sqlalchemy.exc import SQLAlchemyError

from app.api.routes import (
    advisory,
    analytics,
    auth,
    calibration,
    cases,
    channels,
    cooperatives,
    feedback,
    field_users,
    geography,
    map_data,
    public,
    reference_data,
    reports,
    schemes,
    system,
)
from app.core.config import get_settings
from app.core.logging import configure_logging
from app.core.ratelimit import limiter
from app.db.base import Base
from app.db.session import engine
from app.services import advice_scheduler

settings = get_settings()
configure_logging(settings.log_level)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(_: FastAPI):
    """Validate configuration and prepare the database for local development only."""
    settings.guard_runtime()
    if settings.dev_auth_bypass:
        logger.warning(
            "DEVELOPMENT AUTH BYPASS ACTIVE: every request is treated as an administrator. "
            "Set REQUIRE_API_KEY=true to require sign-in."
        )
    if settings.environment == "development":
        # Convenience for a throwaway local database. Every other environment is managed
        # by Alembic (`alembic upgrade head`), which start-local.ps1 and the Dockerfile run.
        Base.metadata.create_all(bind=engine)
    scheduler_task = advice_scheduler.start(settings)
    if scheduler_task is not None:
        logger.info(
            "Weekly advice scheduler enabled: %s at %s (Africa/Kigali)",
            settings.advice_schedule_weekday, settings.advice_schedule_time,
        )
    try:
        yield
    finally:
        if scheduler_task is not None:
            scheduler_task.cancel()


app = FastAPI(title=settings.app_name, version="0.4.0", lifespan=lifespan)
app.state.limiter = limiter
app.add_middleware(SlowAPIMiddleware)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.allowed_origins,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PATCH", "DELETE"],
    allow_headers=["Content-Type", "Authorization", "X-API-Key", "X-Request-ID"],
)


@app.exception_handler(RateLimitExceeded)
async def rate_limit_handler(_: Request, __: RateLimitExceeded) -> JSONResponse:
    return JSONResponse(status_code=429, content={"detail": "Too many requests. Please slow down."})


@app.middleware("http")
async def request_logging(request: Request, call_next):
    request_id = request.headers.get("X-Request-ID", str(uuid.uuid4()))
    started = time.perf_counter()
    response = await call_next(request)
    response.headers["X-Request-ID"] = request_id
    # Dashboard assets change during local development; Vite content hashes handle
    # production caching, so avoid the browser reusing an older bundle locally.
    if request.url.path.endswith((".html", ".js", ".css")):
        response.headers["Cache-Control"] = "no-store, no-cache, must-revalidate"
        response.headers["Pragma"] = "no-cache"
    logger.info(
        "request_id=%s method=%s path=%s status=%s duration_ms=%.1f",
        request_id,
        request.method,
        request.url.path,
        response.status_code,
        (time.perf_counter() - started) * 1000,
    )
    return response


@app.exception_handler(SQLAlchemyError)
async def database_error_handler(_: Request, error: SQLAlchemyError):
    logger.exception("Database error", exc_info=error)
    return JSONResponse(status_code=500, content={"detail": "Database operation failed"})


for api_router in (
    system.router,
    auth.router,
    channels.router,
    advisory.router,
    calibration.router,
    cooperatives.router,
    field_users.router,
    schemes.router,
    reference_data.router,
    reports.router,
    feedback.router,
    cases.router,
    analytics.router,
    map_data.router,
    geography.router,
    public.router,
):
    app.include_router(api_router)


# Production serves the built dashboard (dist); local development serves the source tree.
_dashboard_source = Path(__file__).resolve().parents[2] / "dashboard"
_dashboard_build = _dashboard_source / "dist"
dashboard_dir = _dashboard_build if _dashboard_build.is_dir() else _dashboard_source
if dashboard_dir.is_dir():
    app.mount("/", StaticFiles(directory=dashboard_dir, html=True), name="dashboard")
