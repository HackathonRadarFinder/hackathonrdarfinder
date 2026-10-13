from app.api.router import api_router
import time
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


# Request ID and request logging
@app.middleware("http")
async def request_context_middleware(request: Request, call_next):
    request_id = request.headers.get("X-Request-ID") or generate_request_id()
    request.state.request_id = request_id

    start_time = time.perf_counter()

    try:
        response = await call_next(request)
    except Exception:
        logger.exception(
            "Unhandled request error | request_id=%s method=%s path=%s",
            request_id,
            request.method,
            request.url.path,
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
        exc.errors(),
    )


@app.exception_handler(Exception)
async def unexpected_exception_handler(
    request: Request,
    exc: Exception,
):
    logger.error(
        "Unhandled application exception",
        exc_info=(type(exc), exc, exc.__traceback__),
    )

    return error_response(
        request,
        500,
        "INTERNAL_SERVER_ERROR",
        "An unexpected error occurred.",
    )
