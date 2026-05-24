import asyncio
from typing import AsyncGenerator
from urllib.parse import urlparse
from app.core.config import settings
from app.core.logging import get_logger
from sqlmodel.ext.asyncio.session import AsyncSession
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker
from app.core.db_model_registry import load_models
from sqlalchemy import text

from sqlalchemy.pool import NullPool, AsyncAdaptedQueuePool


logger = get_logger()

# Use NullPool in production (Supabase session mode pooler handles pooling)
# Use AsyncAdaptedQueuePool in development (direct PostgreSQL connection)
if settings.ENVIRONMENT == "production":
    engine = create_async_engine(
        settings.DATABASE_URL,
        poolclass=NullPool,
    )
else:
    engine = create_async_engine(
        settings.DATABASE_URL,
        poolclass=AsyncAdaptedQueuePool,
        pool_pre_ping=True,
        pool_size=5,
        max_overflow=10,
        pool_timeout=30,
        pool_recycle=1800,
    )

async_session = async_sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)


async def get_session() -> AsyncGenerator[AsyncSession, None]:
    session = async_session()
    try:
        yield session
    except Exception as e:
        logger.error(f"Database session error: {e}")
        if session:
            try:
                await session.rollback()
                logger.info("successfully rolled back session after error")
            except Exception as rollback_error:
                logger.error(f"Error during session rollback: {rollback_error}")
        raise
    finally:
        if session:
            try:
                await session.close()
                logger.debug("Database session closed successfully")
            except Exception as close_error:
                logger.error(f"Error closing database session: {close_error}")


async def init_db() -> None:
    try:
        load_models()
        logger.info("Models loaded successfully")

        # db-url-routing-fix 2026-05-21 (Change 5): make the chosen DB target
        # loud at startup so a wrong/leaked env file is visible immediately
        # instead of surfacing later as a confusing auth error. Password is
        # never logged.
        try:
            _u = urlparse(settings.DATABASE_URL.replace("+asyncpg", ""))
            logger.info(
                f"DB target: {_u.hostname}:{_u.port}{_u.path} | "
                f"ENVIRONMENT={settings.ENVIRONMENT}"
            )
            if settings.ENVIRONMENT == "development" and _u.hostname not in (
                "127.0.0.1",
                "localhost",
            ):
                logger.warning(
                    f"ENVIRONMENT=development but DB host is '{_u.hostname}' - "
                    "a tunnel/remote DATABASE_URL may have leaked into a local run."
                )
        except Exception as _db_target_log_err:
            logger.warning(f"Could not log DB target: {_db_target_log_err}")

        max_retries = 3
        retry_delay = 2

        for attempt in range(max_retries):
            try:
                async with engine.begin() as conn:
                    await conn.execute(text("SELECT 1"))
                logger.info("Database connection verified successfully")
                break
            except Exception:
                if attempt == max_retries - 1:
                    logger.error(
                        f"Failed to verify database connection after {max_retries} attempts"
                    )
                    raise
                logger.warning(f"Database connection attempt {attempt + 1}")
                await asyncio.sleep(retry_delay * (attempt + 1))

    except Exception as e:
        logger.error(f"Database initializtion failed: {e}")
        raise
