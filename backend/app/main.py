import logging
import time
import uuid
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from sqlalchemy.exc import SQLAlchemyError

from app.api.routes import analytics, auth, cases, feedback, geography, map_data, reference_data, reports, system, users
from app.core.config import get_settings
from app.core.logging import configure_logging
from app.db.base import Base
from app.db.session import engine

settings = get_settings()
configure_logging(settings.log_level)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(_: FastAPI):
    """Create tables only for local development; deployed databases use Alembic migrations."""
    if settings.environment != "development" and settings.database_url.startswith("sqlite"):
        raise RuntimeError("Deployment requires PostgreSQL")
    if settings.environment != "development" and not settings.configured_api_keys:
        logger.warning("No API keys configured; protected API endpoints will return 401")
    # Create any newly introduced local tables (including platform_accounts).
    # Existing production tables remain managed by Alembic migrations.
    Base.metadata.create_all(bind=engine)
    yield


app = FastAPI(title=settings.app_name, version="0.2.0", lifespan=lifespan)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.allowed_origins,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PATCH", "DELETE"],
    allow_headers=["Content-Type", "X-API-Key", "X-Request-ID"],
)


@app.middleware("http")
async def request_logging(request: Request, call_next):
    request_id = request.headers.get("X-Request-ID", str(uuid.uuid4()))
    started = time.perf_counter()
    response = await call_next(request)
    response.headers["X-Request-ID"] = request_id
    # Dashboard assets change during local development; prevent the browser
    # from reusing an older JavaScript bundle at the plain management URL.
    if request.url.path.endswith((".html", ".js", ".css")):
        response.headers["Cache-Control"] = "no-store, no-cache, must-revalidate"
        response.headers["Pragma"] = "no-cache"
    logger.info("request_id=%s method=%s path=%s status=%s duration_ms=%.1f", request_id, request.method, request.url.path, response.status_code, (time.perf_counter() - started) * 1000)
    return response


@app.exception_handler(SQLAlchemyError)
async def database_error_handler(_: Request, error: SQLAlchemyError):
    logger.exception("Database error", exc_info=error)
    return JSONResponse(status_code=500, content={"detail": "Database operation failed"})


for api_router in (system.router, auth.router, users.router, reference_data.router, reports.router, cases.router, feedback.router, analytics.router, map_data.router, geography.router):
    app.include_router(api_router)


dashboard_dir = Path(__file__).resolve().parents[2] / "dashboard"
if dashboard_dir.is_dir():
    app.mount("/", StaticFiles(directory=dashboard_dir, html=True), name="dashboard")
