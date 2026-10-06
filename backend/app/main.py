import time
from datetime import datetime, timezone

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

from app.api.router import api_router
from app.core.config import settings
from app.core.exceptions import AppException
from app.core.logging import configure_logging, get_logger
from app.core.utils import generate_request_id


configure_logging()

logger = get_logger(__name__)


app = FastAPI(
    title=settings.app_name,
    description="AI-powered hackathon discovery and intelligence platform",
    version=settings.app_version,
    debug=settings.debug,
)


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


@app.exception_handler(AppException)
async def app_exception_handler(
    request: Request,
    exc: AppException,
):
    request_id = getattr(
        request.state,
        "request_id",
        generate_request_id(),
    )

    return JSONResponse(
        status_code=exc.status_code,
        content={
            "code": exc.code,
            "message": exc.message,
            "details": exc.details,
            "request_id": request_id,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        },
        headers={"X-Request-ID": request_id},
    )


@app.exception_handler(StarletteHTTPException)
async def http_exception_handler(
    request: Request,
    exc: StarletteHTTPException,
):
    request_id = getattr(
        request.state,
        "request_id",
        generate_request_id(),
    )

    return JSONResponse(
        status_code=exc.status_code,
        content={
            "code": f"HTTP_{exc.status_code}",
            "message": str(exc.detail),
            "details": None,
            "request_id": request_id,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        },
        headers={"X-Request-ID": request_id},
    )


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(
    request: Request,
    exc: RequestValidationError,
):
    request_id = getattr(
        request.state,
        "request_id",
        generate_request_id(),
    )

    return JSONResponse(
        status_code=422,
        content={
            "code": "VALIDATION_ERROR",
            "message": "Request validation failed.",
            "details": exc.errors(),
            "request_id": request_id,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        },
        headers={"X-Request-ID": request_id},
    )


@app.exception_handler(Exception)
async def unexpected_exception_handler(
    request: Request,
    exc: Exception,
):
    request_id = getattr(
        request.state,
        "request_id",
        generate_request_id(),
    )

    logger.exception(
        "Unhandled application exception | request_id=%s",
        request_id,
        exc_info=exc,
    )

    return JSONResponse(
        status_code=500,
        content={
            "code": "INTERNAL_SERVER_ERROR",
            "message": "An unexpected error occurred.",
            "details": None,
            "request_id": request_id,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        },
        headers={"X-Request-ID": request_id},
    )


app.include_router(
    api_router,
    prefix=settings.api_v1_prefix,
)