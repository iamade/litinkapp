"""
CreditService — reserve, confirm, and release credits for AI operations.

Flow:
    reservation_id = await service.reserve_credits(user_id, amount, operation_type)
    # ... do the work ...
    await service.confirm_deduction(reservation_id, actual_amount)   # on success
    await service.release_reservation(reservation_id)                # on failure

For per-unit task deductions (idempotent):
    await service.deduct_for_operation(user_id, amount, operation_type, ref_id)
"""

import uuid
import math
import logging
from contextlib import asynccontextmanager
from datetime import datetime, timezone, timedelta
from typing import Optional

from sqlmodel import select, func
from sqlmodel.ext.asyncio.session import AsyncSession
from sqlalchemy import text

from app.credits.models import CreditTransaction, CreditFailure
from app.promo.models import CreditGrant
from app.promo.services import deduct_credits

logger = logging.getLogger(__name__)

# Reservations expire after 2 hours if not confirmed/released
RESERVATION_TTL_HOURS = 2


class CreditService:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def get_raw_balance(self, user_id: uuid.UUID) -> int:
        """Sum of credits_remaining in non-expired grants."""
        now = datetime.now(timezone.utc)
        stmt = select(func.coalesce(func.sum(CreditGrant.credits_remaining), 0)).where(
            CreditGrant.user_id == user_id,
            CreditGrant.expires_at > now,
            CreditGrant.credits_remaining > 0,
        )
        result = await self.session.exec(stmt)
        return int(result.one())

    async def get_pending_reservations(self, user_id: uuid.UUID) -> int:
        """Sum of credits held in active (non-expired) reservations."""
        now = datetime.now(timezone.utc)
        stmt = select(func.coalesce(func.sum(CreditTransaction.amount), 0)).where(
            CreditTransaction.user_id == user_id,
            CreditTransaction.status == "reserved",
            CreditTransaction.expires_at > now,
        )
        result = await self.session.exec(stmt)
        return int(result.one())

    async def get_effective_balance(self, user_id: uuid.UUID) -> int:
        """Available credits = raw balance minus pending reservations."""
        raw = await self.get_raw_balance(user_id)
        pending = await self.get_pending_reservations(user_id)
        return max(0, raw - pending)

    async def reserve_credits(
        self,
        user_id: uuid.UUID,
        amount: int,
        operation_type: str,
        ref_id: Optional[str] = None,
        meta: Optional[dict] = None,
    ) -> uuid.UUID:
        """
        Atomically check available balance and create a reservation.

        Uses SELECT FOR UPDATE on credit_grants to prevent double-spending.
        Raises ValueError if insufficient credits.
        Returns the reservation transaction id.
        """
        if amount <= 0:
            raise ValueError("Reserve amount must be positive")

        now = datetime.now(timezone.utc)
        expires_at = now + timedelta(hours=RESERVATION_TTL_HOURS)

        # Lock active grant rows to prevent concurrent over-commitment
        # Note: FOR UPDATE cannot be used with aggregate functions in PostgreSQL,
        # so we lock the rows first, then sum separately
        lock_stmt = text("""
            SELECT id, credits_remaining
            FROM credit_grants
            WHERE user_id = :user_id
              AND expires_at > NOW()
              AND credits_remaining > 0
            ORDER BY id
            FOR UPDATE
        """)
        lock_result = await self.session.execute(lock_stmt, {"user_id": str(user_id)})
        locked_rows = lock_result.fetchall()
        raw_balance = sum(row[1] for row in locked_rows)

        # Also fetch current pending reservation total (without locking transactions table)
        pending = await self.get_pending_reservations(user_id)
        effective = max(0, raw_balance - pending)

        if effective < amount:
            raise ValueError(
                f"Insufficient credits: required={amount}, available={effective}"
            )

        transaction = CreditTransaction(
            user_id=user_id,
            amount=amount,
            status="reserved",
            operation_type=operation_type,
            ref_id=ref_id,
            meta=meta,
            expires_at=expires_at,
        )
        self.session.add(transaction)
        await self.session.flush()  # get the id without committing
        return transaction.id

    async def confirm_deduction(
        self,
        reservation_id: uuid.UUID,
        actual_amount: Optional[int] = None,
    ) -> bool:
        """
        Finalize a reservation: deduct credits from grants and mark confirmed.

        If actual_amount < reserved amount, only the actual amount is deducted.
        Returns True on success, False if reservation not found or already settled.
        """
        stmt = select(CreditTransaction).where(
            CreditTransaction.id == reservation_id,
            CreditTransaction.status == "reserved",
        )
        result = await self.session.exec(stmt)
        transaction = result.first()

        if not transaction:
            logger.warning(
                "confirm_deduction: reservation %s not found or already settled",
                reservation_id,
            )
            return False

        deduct_amount = actual_amount if actual_amount is not None else transaction.amount
        if deduct_amount > 0:
            success = await deduct_credits(
                user_id=transaction.user_id,
                amount=deduct_amount,
                session=self.session,
            )
            if not success:
                logger.error(
                    "confirm_deduction: deduct_credits failed for reservation %s "
                    "(user=%s, amount=%d)",
                    reservation_id,
                    transaction.user_id,
                    deduct_amount,
                )
                return False

        transaction.status = "confirmed"
        transaction.amount = deduct_amount
        self.session.add(transaction)
        return True

    async def release_reservation(self, reservation_id: uuid.UUID) -> bool:
        """
        Release a reservation without deducting any credits.
        Returns True if found and released, False otherwise.
        """
        stmt = select(CreditTransaction).where(
            CreditTransaction.id == reservation_id,
            CreditTransaction.status == "reserved",
        )
        result = await self.session.exec(stmt)
        transaction = result.first()

        if not transaction:
            logger.warning(
                "release_reservation: reservation %s not found or already settled",
                reservation_id,
            )
            return False

        transaction.status = "released"
        self.session.add(transaction)
        return True

    async def log_credit_failure(
        self,
        user_id: uuid.UUID,
        reservation_id: uuid.UUID,
        amount: int,
        operation_type: str,
        error_message: Optional[str] = None,
    ) -> None:
        """Persist a credit confirm_deduction failure for later reconciliation."""
        failure = CreditFailure(
            user_id=user_id,
            reservation_id=reservation_id,
            amount=amount,
            operation_type=operation_type,
            error_message=error_message,
            status="pending",
        )
        self.session.add(failure)
        try:
            await self.session.commit()
        except Exception as e:
            logger.error(
                "log_credit_failure: could not persist failure record: %s", e
            )

    @asynccontextmanager
    async def credit_transaction(self, reservation_id: uuid.UUID, amount: int):
        """
        Async context manager that confirms deduction on success and releases
        the reservation on any exception, then re-raises.

        Usage::

            async with credit_service.credit_transaction(reservation_id, COST):
                # do the billable work here
        """
        try:
            yield
            await self.confirm_deduction(reservation_id, amount)
            await self.session.commit()
        except Exception:
            try:
                await self.release_reservation(reservation_id)
                await self.session.commit()
            except Exception as release_err:
                logger.warning(
                    "credit_transaction: release failed for reservation %s: %s",
                    reservation_id,
                    release_err,
                )
            raise

    async def deduct_for_operation(
        self,
        user_id: uuid.UUID,
        amount: int,
        operation_type: str,
        ref_id: str,
    ) -> bool:
        """
        Idempotent per-unit deduction (for use inside Celery tasks).

        Checks for an existing confirmed transaction with the same ref_id and
        operation_type before deducting, so retries are safe.

        Returns True on success (or if already deducted), False if insufficient.
        """
        if amount <= 0:
            return True

        # Idempotency check
        existing_stmt = select(CreditTransaction).where(
            CreditTransaction.ref_id == ref_id,
            CreditTransaction.operation_type == operation_type,
            CreditTransaction.status == "confirmed",
        )
        existing_result = await self.session.exec(existing_stmt)
        if existing_result.first():
            logger.debug(
                "deduct_for_operation: skipping duplicate deduction ref_id=%s op=%s",
                ref_id,
                operation_type,
            )
            return True

        success = await deduct_credits(
            user_id=user_id,
            amount=amount,
            session=self.session,
        )
        if not success:
            logger.warning(
                "deduct_for_operation: insufficient credits user=%s amount=%d op=%s ref=%s",
                user_id,
                amount,
                operation_type,
                ref_id,
            )
            return False

        transaction = CreditTransaction(
            user_id=user_id,
            amount=amount,
            status="confirmed",
            operation_type=operation_type,
            ref_id=ref_id,
        )
        self.session.add(transaction)
        return True


def credits_for_audio_duration(duration_seconds: float) -> int:
    """Convert audio duration to credit cost (ceiling, 1 credit/second)."""
    from app.credits.constants import AUDIO_PER_SECOND
    return max(1, math.ceil(duration_seconds) * AUDIO_PER_SECOND)


def credits_for_video_duration(duration_seconds: float) -> int:
    """Convert video duration to credit cost (ceiling, 5 credits/second)."""
    from app.credits.constants import VIDEO_PER_SECOND
    return max(1, math.ceil(duration_seconds) * VIDEO_PER_SECOND)
