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
from sqlmodel import select

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


@celery_app.task(bind=True, name="app.tasks.credit_tasks.reconcile_failed_credits")
def reconcile_failed_credits(self):
    """
    Retry pending credit_failures that resulted from failed confirm_deduction calls.

    Runs every 15 minutes via Celery beat.
    - Finds CreditFailure rows with status='pending' and retry_count < 3
    - Tries to confirm the deduction again
    - On success: marks status='resolved'
    - On failure: increments retry_count
    - After 3 failures: marks status='voided' and logs an alert
    """
    return asyncio.run(_async_reconcile_failed_credits())


async def _async_reconcile_failed_credits():
    from app.credits.models import CreditFailure
    from app.credits.service import CreditService

    MAX_RETRIES = 3
    resolved = 0
    voided = 0

    async with async_session() as session:
        try:
            stmt = select(CreditFailure).where(
                CreditFailure.status == "pending",
                CreditFailure.retry_count < MAX_RETRIES,
            )
            result = await session.exec(stmt)
            failures = result.all()

            for failure in failures:
                credit_svc = CreditService(session)
                try:
                    confirmed = await credit_svc.confirm_deduction(
                        failure.reservation_id, failure.amount
                    )
                    if confirmed:
                        failure.status = "resolved"
                        failure.resolved_at = datetime.now(timezone.utc)
                        session.add(failure)
                        resolved += 1
                        logger.info(
                            "[CREDIT RECONCILE] Resolved failure id=%s reservation=%s",
                            failure.id,
                            failure.reservation_id,
                        )
                    else:
                        failure.retry_count += 1
                        if failure.retry_count >= MAX_RETRIES:
                            failure.status = "voided"
                            voided += 1
                            logger.error(
                                "[CREDIT RECONCILE] ALERT: voided failure id=%s "
                                "reservation=%s user=%s amount=%d op=%s — "
                                "manual intervention required",
                                failure.id,
                                failure.reservation_id,
                                failure.user_id,
                                failure.amount,
                                failure.operation_type,
                            )
                        else:
                            logger.warning(
                                "[CREDIT RECONCILE] Retry %d/%d for failure id=%s",
                                failure.retry_count,
                                MAX_RETRIES,
                                failure.id,
                            )
                        session.add(failure)
                except Exception as e:
                    failure.retry_count += 1
                    if failure.retry_count >= MAX_RETRIES:
                        failure.status = "voided"
                        voided += 1
                        logger.error(
                            "[CREDIT RECONCILE] ALERT: voided failure id=%s after exception: %s",
                            failure.id,
                            e,
                        )
                    else:
                        logger.warning(
                            "[CREDIT RECONCILE] Exception on failure id=%s retry %d: %s",
                            failure.id,
                            failure.retry_count,
                            e,
                        )
                    session.add(failure)

            await session.commit()
            logger.info(
                "[CREDIT RECONCILE] Done — resolved=%d voided=%d total=%d",
                resolved,
                voided,
                len(failures),
            )
            return {"resolved": resolved, "voided": voided, "total": len(failures)}

        except Exception as e:
            logger.error("[CREDIT RECONCILE] Error: %s", e)
            await session.rollback()
            raise
