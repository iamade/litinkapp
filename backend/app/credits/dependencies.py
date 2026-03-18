"""
FastAPI dependency for credit gating.

Usage:
    @router.post("/my-endpoint")
    async def my_endpoint(
        reservation_id: uuid.UUID = Depends(require_credits("text_gen", TEXT_GEN)),
        ...
    ):
        ...
        # After success, confirm the reservation:
        service = CreditService(session)
        await service.confirm_deduction(reservation_id, actual_amount)
        await session.commit()
"""

import uuid
import logging
from typing import Callable

from fastapi import Depends, HTTPException, status

from app.auth.models import User
from app.core.auth import get_current_active_user
from app.core.database import get_session
from app.credits.service import CreditService
from sqlmodel.ext.asyncio.session import AsyncSession

logger = logging.getLogger(__name__)


def require_credits(operation_type: str, estimated_amount: int) -> Callable:
    """
    Factory that returns a FastAPI dependency.

    The dependency:
      1. Checks the user has >= estimated_amount effective credits.
      2. Creates a reservation (status="reserved") and commits it.
      3. Returns the reservation_id (uuid.UUID).
      4. Raises HTTP 402 if insufficient credits.

    The caller is responsible for confirming or releasing the reservation.
    """

    async def _check_and_reserve(
        current_user: User = Depends(get_current_active_user),
        session: AsyncSession = Depends(get_session),
    ) -> uuid.UUID:
        service = CreditService(session)
        try:
            reservation_id = await service.reserve_credits(
                user_id=current_user.id,
                amount=estimated_amount,
                operation_type=operation_type,
                ref_id=str(uuid.uuid4()),
            )
            await session.commit()
            return reservation_id
        except ValueError as exc:
            raise HTTPException(
                status_code=status.HTTP_402_PAYMENT_REQUIRED,
                detail=str(exc),
            )

    return _check_and_reserve
