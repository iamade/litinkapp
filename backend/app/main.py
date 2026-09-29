from fastapi import FastAPI, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import HTTPBearer
from fastapi.staticfiles import StaticFiles
import uvicorn
import os
from contextlib import asynccontextmanager
from app.api.main import api_router

from app.core.config import settings
from app.core.database import init_db
from app.core.admin_seeder import seed_admin_users


from app.core.logging import get_logger
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from app.core.health import health_checker, ServiceStatus
import asyncio
import time

logger = get_logger()


async def startup_health_check(timeout: float = 90.0) -> bool:
    try:
        async with asyncio.timeout(timeout):
            retry_intervals = [1, 2, 5, 10, 15]
            start_time = time.time()

            while True:
                is_healthy = await health_checker.wait_for_services()
                if is_healthy:
                    return True
                elapsed = time.time() - start_time
                if elapsed >= timeout:
                    logger.error("Services failed health check during startup")
                    return False
                wait_time = retry_intervals[
                    min(len(retry_intervals) - 1, int(elapsed / 10))
                ]
                logger.warning(
                    f"Services not healthy, waiting {wait_time}s before retry"
                )
                await asyncio.sleep(wait_time)
    except asyncio.TimeoutError:
        logger.error(f"Health check timed out after {timeout} seconds")
        return False
    except Exception as e:
        logger.error(f"Error during startup health check: {e}")
        return False


@asynccontextmanager
async def lifespan(app: FastAPI):
    try:
        await init_db()
        logger.info("Database initialized successfully")

        # Seed admin users if they don't exist
        await seed_admin_users()

        await health_checker.add_service("database", health_checker.check_database)
        await health_checker.add_service("celery", health_checker.check_celery)
        await health_checker.add_service("redis", health_checker.check_redis)

        if not await startup_health_check():
            logger.warning(
                "Some services failed health check during startup - continuing in degraded mode"
            )
        logger.info("Application startup complete")
        yield
    except Exception as e:
        logger.error(f"Application startup failed: {e}")
        await health_checker.cleanup()
        raise
    finally:
        logger.info("Shutting down")
        await health_checker.cleanup()


# @asynccontextmanager
# async def lifespan(app: FastAPI):
#     """Application lifespan events"""
#     # Startup
#     await init_db()
#     await redis_client.connect()
#     yield
#     # Shutdown
#     await redis_client.disconnect()


app = FastAPI(
    title=settings.PROJECT_NAME,
    description=settings.PROJECT_DESCRIPTION,
    version=settings.VERSION,
    docs_url=f"{settings.API_V1_STR}/docs",
    redoc_url=f"{settings.API_V1_STR}/redoc",
    openapi_url=f"{settings.API_V1_STR}/openapi.json",
    lifespan=lifespan,
)

# --- KAN-470 / KAN-471: sanitized validation errors -------------------------
# FastAPI's default RequestValidationError handler echoes pydantic error
# `input` values (and raw request bodies), which leaked submitted passwords
# back in 422 responses (KAN-470, P1). Every error entry is rebuilt from
# safe fields only (loc/msg/type) and a machine-readable error_code is
# attached (KAN-471 login-flow discriminator).
SENSITIVE_VALIDATION_FIELDS = frozenset(
    {
        "password",
        "confirm_password",
        "new_password",
        "old_password",
        "current_password",
        "security_answer",
        "otp",
        "token",
        "secret",
    }
)


def _validation_error_code(err: dict) -> str:
    etype = str(err.get("type", ""))
    loc = err.get("loc") or []
    field = loc[-1] if loc else ""
    if not isinstance(field, str):
        field = ""
    if etype == "json_invalid":
        return "VALIDATION_ERROR_MALFORMED_JSON"
    if etype == "missing":
        return "VALIDATION_ERROR_MISSING_FIELD"
    if field == "email" and etype == "value_error":
        return "VALIDATION_ERROR_EMAIL_FORMAT"
    if field in {"password", "confirm_password", "new_password"}:
        return "VALIDATION_ERROR_PASSWORD_POLICY"
    return "VALIDATION_ERROR"


@app.exception_handler(RequestValidationError)
async def sanitized_validation_handler(
    request: Request, exc: RequestValidationError
):
    """422 responses that never echo submitted values (KAN-470)."""
    errors = []
    for err in exc.errors():
        errors.append(
            {
                "loc": list(err.get("loc") or []),
                "msg": str(err.get("msg", "Validation error")),
                "type": str(err.get("type", "value_error")),
                "error_code": _validation_error_code(err),
            }
        )
    logger.warning(
        f"Validation error 422 on {request.method} {request.url.path}: "
        f"{len(errors)} error(s) sanitized (no input values echoed)"
    )
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content={"detail": errors, "error_code": "VALIDATION_ERROR"},
    )


# CORS middleware - Uses settings.ALLOWED_HOSTS (controlled via env vars)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.get_allowed_hosts,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
    allow_headers=["*"],
)

# Security
security = HTTPBearer()

# Uploads directory for generated content (fallback for local files)
if os.path.exists(settings.UPLOAD_DIR):
    app.mount("/uploads", StaticFiles(directory=settings.UPLOAD_DIR), name="uploads")


@app.get("/")
async def root():
    """Root endpoint"""
    return {"message": "Welcome to Litink API", "version": "1.0.0", "docs": "/docs"}


@app.get("/health", response_model=dict)
async def health_check():
    """Health check endpoint"""
    try:
        health_status = await health_checker.check_all_services()

        if health_status["status"] == ServiceStatus.HEALTHY:
            status_code = status.HTTP_200_OK
        elif health_status["status"] == ServiceStatus.DEGRADED:
            status_code = status.HTTP_206_PARTIAL_CONTENT
        else:
            status_code = status.HTTP_503_SERVICE_UNAVAILABLE

        return JSONResponse(status_code=status_code, content=health_status)
    except Exception as e:
        logger.error(f"Health check failed: {e}")
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={"status": ServiceStatus.UNHEALTHY, "error": str(e)},
        )


# Include API routes
app.include_router(api_router, prefix=settings.API_V1_STR)


if __name__ == "__main__":
    if os.getenv("ENVIRONMENT") == "development":
        import debugpy

        debugpy.listen(("0.0.0.0", 5678))
        print("🐛 Debug server listening on port 5678...")
        print("Waiting for debugger to attach...")
        # debugpy.wait_for_client()  # Uncomment to wait for debugger

    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=8000,
        reload=True if os.getenv("ENVIRONMENT") == "development" else False,
        limit_max_requests=104857600,  # 100MB max request size for file uploads
    )
