"""
Periodic Celery tasks for credit system maintenance.
"""

import asyncio
import logging
import uuid
from datetime import datetime, timezone, timedelta

from app.tasks.celery_app import celery_app
from app.core.database import async_session
from sqlalchemy import text

logger = logging.getLogger(__name__)

# Reservations older than this are auto-released
ZOMBIE_THRESHOLD_HOURS = 2  # Must match RESERVATION_TTL_HOURS in credits/service.py


@celery_app.task(bind=True, name="app.tasks.credit_tasks.release_zombie_reservations")
def release_zombie_reservations(self):
    """
    Release credit reservations that are older than ZOMBIE_THRESHOLD_HOURS.

    These are reservations where the associated task never confirmed or released
    (e.g., worker crash, timeout, or network failure).

    Runs every 10 minutes via Celery beat.
    """
    return asyncio.run(_async_release_zombie_reservations())


async def _async_release_zombie_reservations():
    cutoff = datetime.now(timezone.utc) - timedelta(hours=ZOMBIE_THRESHOLD_HOURS)

    async with async_session() as session:
        try:
            result = await session.execute(
                text("""
                    UPDATE credit_transactions
                    SET status = 'released'
                    WHERE status = 'reserved'
                      AND created_at < :cutoff
                    RETURNING id, user_id, amount, operation_type
                """),
                {"cutoff": cutoff},
            )
            rows = result.fetchall()
            await session.commit()

            if rows:
                logger.info(
                    "[CREDIT CLEANUP] Released %d zombie reservations older than %dh",
                    len(rows),
                    ZOMBIE_THRESHOLD_HOURS,
                )
                for row in rows:
                    logger.debug(
                        "[CREDIT CLEANUP] Released reservation id=%s user=%s amount=%d op=%s",
                        row[0],
                        row[1],
                        row[2],
                        row[3],
                    )
            else:
                logger.debug("[CREDIT CLEANUP] No zombie reservations found")

            return {"released": len(rows)}

        except Exception as e:
            logger.error("[CREDIT CLEANUP] Error releasing zombie reservations: %s", e)
            await session.rollback()
            raise
