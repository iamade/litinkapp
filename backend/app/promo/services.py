"""
Credit deduction utility.

Usage:
    success = await deduct_credits(user_id=user.id, amount=100, session=session)
    if not success:
        raise HTTPException(402, "Insufficient credits")
"""

import uuid
from datetime import datetime, timezone

from sqlmodel import select
from sqlmodel.ext.asyncio.session import AsyncSession

from app.promo.models import CreditGrant


async def deduct_credits(
    user_id: uuid.UUID,
    amount: int,
    session: AsyncSession,
) -> bool:
    """
    Deduct `amount` credits from the user's active grants using FIFO order
    (oldest non-expired grant first).

    Returns True if the full amount was deducted, False if credits are insufficient.
    The session is NOT committed here — callers are responsible for committing.
    """
    if amount <= 0:
        return True

    now = datetime.now(timezone.utc)

    # Fetch active grants ordered by creation date (FIFO)
    stmt = (
        select(CreditGrant)
        .where(
            CreditGrant.user_id == user_id,
            CreditGrant.expires_at > now,
            CreditGrant.credits_remaining > 0,
        )
        .order_by(CreditGrant.created_at.asc())
    )
    result = await session.exec(stmt)
    grants = result.all()

    remaining = amount
    for grant in grants:
        if remaining <= 0:
            break

        if grant.credits_remaining >= remaining:
            grant.credits_remaining -= remaining
            grant.credits_used += remaining
            session.add(grant)
            remaining = 0
        else:
            remaining -= grant.credits_remaining
            grant.credits_used += grant.credits_remaining
            grant.credits_remaining = 0
            session.add(grant)

    return remaining == 0
