"""
Credit transaction history endpoint.
"""

import uuid
from typing import List, Optional
from fastapi import APIRouter, Depends, Query
from sqlmodel import select
from sqlmodel.ext.asyncio.session import AsyncSession

from app.core.auth import get_current_active_user
from app.core.database import get_session
from app.auth.models import User
from app.credits.models import CreditTransaction

router = APIRouter()


@router.get("/credits/history")
async def get_credit_history(
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100, alias="limit"),
    status: Optional[str] = Query(default=None, description="Filter by status: reserved, confirmed, released"),
    current_user: User = Depends(get_current_active_user),
    session: AsyncSession = Depends(get_session),
):
    """Return paginated credit transaction history for the authenticated user."""
    offset = (page - 1) * page_size

    stmt = (
        select(CreditTransaction)
        .where(CreditTransaction.user_id == current_user.id)
        .order_by(CreditTransaction.created_at.desc())
        .offset(offset)
        .limit(page_size)
    )
    if status:
        stmt = stmt.where(CreditTransaction.status == status)

    result = await session.exec(stmt)
    transactions = result.all()

    return {
        "page": page,
        "page_size": page_size,
        "transactions": [
            {
                "id": str(t.id),
                "amount": t.amount,
                "status": t.status,
                "operation_type": t.operation_type,
                "ref_id": t.ref_id,
                "created_at": t.created_at.isoformat(),
                "expires_at": t.expires_at.isoformat() if t.expires_at else None,
            }
            for t in transactions
        ],
    }
