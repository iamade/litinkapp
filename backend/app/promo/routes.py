"""
Promo code redemption and credit balance endpoints.
"""

from datetime import datetime, timezone, timedelta
from fastapi import APIRouter, Depends, HTTPException, status
from sqlmodel import select, func
from sqlmodel.ext.asyncio.session import AsyncSession

from app.core.auth import get_current_active_user
from app.core.database import get_session
from app.auth.models import User
from app.promo.models import PromoCode, CreditGrant, GrantType
from app.promo.schemas import (
    RedeemPromoRequest,
    RedeemPromoResponse,
    CreditBalanceResponse,
)

router = APIRouter()


@router.post("/promo/redeem", response_model=RedeemPromoResponse)
async def redeem_promo_code(
    body: RedeemPromoRequest,
    current_user: User = Depends(get_current_active_user),
    session: AsyncSession = Depends(get_session),
):
    """Redeem a promo code and grant credits to the authenticated user."""
    code_upper = body.code.strip().upper()

    # Look up the promo code
    stmt = select(PromoCode).where(PromoCode.code == code_upper)
    result = await session.exec(stmt)
    promo = result.first()

    if not promo:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Promo code not found",
        )

    if not promo.is_active:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Promo code is inactive",
        )

    if promo.current_redemptions >= promo.max_redemptions:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Promo code has reached its redemption limit",
        )

    # Check if this user has already redeemed this code
    already_redeemed_stmt = select(CreditGrant).where(
        CreditGrant.user_id == current_user.id,
        CreditGrant.promo_code_id == promo.id,
    )
    already_redeemed_result = await session.exec(already_redeemed_stmt)
    if already_redeemed_result.first():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="You have already redeemed this promo code",
        )

    now = datetime.now(timezone.utc)
    expires_at = now + timedelta(days=promo.expiry_days)

    # Create the credit grant
    grant = CreditGrant(
        user_id=current_user.id,
        credits_remaining=promo.credit_amount,
        credits_used=0,
        expires_at=expires_at,
        promo_code_id=promo.id,
        grant_type=GrantType.PROMO,
    )
    session.add(grant)

    # Increment redemption counter
    promo.current_redemptions += 1
    session.add(promo)

    await session.commit()
    await session.refresh(grant)

    return RedeemPromoResponse(
        success=True,
        credits_granted=promo.credit_amount,
        expires_at=expires_at,
    )


@router.get("/credits/balance", response_model=CreditBalanceResponse)
async def get_credit_balance(
    current_user: User = Depends(get_current_active_user),
    session: AsyncSession = Depends(get_session),
):
    """Return the total active (non-expired) credits for the authenticated user."""
    now = datetime.now(timezone.utc)

    stmt = select(func.coalesce(func.sum(CreditGrant.credits_remaining), 0)).where(
        CreditGrant.user_id == current_user.id,
        CreditGrant.expires_at > now,
        CreditGrant.credits_remaining > 0,
    )
    result = await session.exec(stmt)
    total = result.one()

    return CreditBalanceResponse(total_credits=int(total))
