from app.api.router import api_router
from app.api.routes.discovery import router as discovery_router
from app.api.routes.release_admin import router as release_admin_router
from app.api.routes.duplicate_review import router as duplicate_review_router
from app.api.routes.dataset_import import router as dataset_import_router
from app.api.routes.personalized import router as personalized_router
import time
import re
from datetime import datetime, timezone

from fastapi import FastAPI, Request
from fastapi.encoders import jsonable_encoder
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

from app.api.routes import (
    events,
    organizations,
    predictions,
    auth,
    notifications,
    admin,
    account,
)
from app.core.config import settings
from app.core.exceptions import AppException
from app.core.logging import configure_logging, get_logger
from app.core.utils import generate_request_id


configure_logging()
logger = get_logger(__name__)

app = FastAPI(
    title=settings.APP_NAME,
    description="Backend API for Hackathon Radar Finder",
    version=settings.APP_VERSION,
    debug=settings.DEBUG,
)


# Preserve all existing API routes
app.include_router(events.router)
app.include_router(organizations.router)
app.include_router(predictions.router)
app.include_router(auth.router)
app.include_router(notifications.router)
app.include_router(admin.router)
app.include_router(account.router)
app.include_router(discovery_router)
app.include_router(release_admin_router)
app.include_router(duplicate_review_router)
app.include_router(dataset_import_router)
app.include_router(personalized_router)
from app.api.routes.institutions import router as institutions_router
app.include_router(institutions_router)
# Versioned API routes
app.include_router(
    api_router,
    prefix=settings.API_V1_PREFIX,
)


# Preserve the existing health endpoint
@app.get("/health", tags=["Health"])
async def health_check():
    return {
        "status": "healthy",
        "service": "hackathon-radar-api",
        "version": settings.APP_VERSION,
    }


@app.get("/ready", tags=["Health"])
def readiness_check():
    """Readiness requires database connectivity and every shipped migration."""
    from app.core.database import engine
    from app.services.readiness import check_readiness
    return check_readiness(engine)


# Request ID and request logging
@app.middleware("http")
async def request_context_middleware(request: Request, call_next):
    incoming_id = request.headers.get("X-Request-ID", "")
    request_id = incoming_id if re.fullmatch(r'[A-Za-z0-9_.-]{1,64}', incoming_id) else generate_request_id()
    request.state.request_id = request_id

    start_time = time.perf_counter()

    try:
        response = await call_next(request)
    except Exception as error:
        # Driver tracebacks may contain SQL parameters, credentials or user data.
        logger.error(
            "Unhandled request error | request_id=%s method=%s error_type=%s",
            request_id,
            request.method,
            type(error).__name__,
        )
        raise

    duration_ms = (time.perf_counter() - start_time) * 1000

    response.headers["X-Request-ID"] = request_id

    logger.info(
        "Request completed | request_id=%s method=%s path=%s "
        "status=%s duration_ms=%.2f",
        request_id,
        request.method,
        request.url.path,
        response.status_code,
        duration_ms,
    )

    return response


def error_response(request, status_code, code, message, details=None):
    request_id = getattr(
        request.state,
        "request_id",
        generate_request_id(),
    )

    return JSONResponse(
        status_code=status_code,
        content=jsonable_encoder({
            "code": code,
            "message": message,
            "details": details,
            "request_id": request_id,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }),
        headers={"X-Request-ID": request_id},
    )


@app.exception_handler(AppException)
async def app_exception_handler(request: Request, exc: AppException):
    return error_response(
        request,
        exc.status_code,
        exc.code,
        exc.message,
        exc.details,
    )


@app.exception_handler(StarletteHTTPException)
async def http_exception_handler(
    request: Request,
    exc: StarletteHTTPException,
):
    return error_response(
        request,
        exc.status_code,
        f"HTTP_{exc.status_code}",
        str(exc.detail),
    )


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(
    request: Request,
    exc: RequestValidationError,
):
    return error_response(
        request,
        422,
        "VALIDATION_ERROR",
        "Request validation failed.",
        # Pydantic error input/context may contain passwords or submitted secrets.
        [{key: error[key] for key in ("type", "loc", "msg") if key in error}
         for error in exc.errors()],
    )


@app.exception_handler(Exception)
async def unexpected_exception_handler(
    request: Request,
    exc: Exception,
):
    logger.error(
        "Unhandled application exception | request_id=%s error_type=%s",
        getattr(request.state, 'request_id', 'unavailable'),
        type(exc).__name__,
    )

    return error_response(
        request,
        500,
        "INTERNAL_SERVER_ERROR",
        "An unexpected error occurred.",
    )
