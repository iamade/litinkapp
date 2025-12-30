from fastapi import APIRouter, Depends, HTTPException
from typing import List
from sqlmodel import select
from sqlmodel.ext.asyncio.session import AsyncSession

from app.badges.schemas import BadgeCreate
from app.badges.models import Badge, UserBadge
from app.core.database import get_session
from app.core.auth import get_current_active_user

router = APIRouter()


@router.post("/", response_model=Badge, status_code=201)
async def create_badge(
    badge: BadgeCreate,
    session: AsyncSession = Depends(get_session),
    current_user: dict = Depends(get_current_active_user),
):
    """Create a new badge (admin-only in a real app)"""
    new_badge = Badge(**badge.dict())
    session.add(new_badge)
    await session.commit()
    await session.refresh(new_badge)
    return new_badge


@router.get("/", response_model=List[Badge])
async def get_all_badges(session: AsyncSession = Depends(get_session)):
    """Get all available badges"""
    result = await session.exec(select(Badge))
    return result.all()


@router.get("/{badge_id}", response_model=Badge)
async def get_badge(badge_id: int, session: AsyncSession = Depends(get_session)):
    """Get a badge by its ID"""
    badge = await session.get(Badge, badge_id)
    if not badge:
        raise HTTPException(status_code=404, detail="Badge not found")
    return badge


@router.post("/award/{user_id}/{badge_id}", response_model=dict)
async def award_badge_to_user(
    user_id: str,
    badge_id: int,
    session: AsyncSession = Depends(get_session),
    current_user: dict = Depends(get_current_active_user),
):
    """Award a badge to a user (admin-only in a real app)"""
    # Check if badge exists
    badge = await session.get(Badge, badge_id)
    if not badge:
        raise HTTPException(status_code=404, detail="Badge not found")

    # Check if already awarded
    existing = await session.get(UserBadge, (user_id, badge_id))
    if existing:
        raise HTTPException(status_code=409, detail="User already has this badge")

    user_badge = UserBadge(user_id=user_id, badge_id=badge_id)
    session.add(user_badge)
    await session.commit()

    return {"message": "Badge awarded successfully"}


@router.get("/user/{user_id}", response_model=List[Badge])
async def get_user_badges(user_id: str, session: AsyncSession = Depends(get_session)):
    """Get all badges for a specific user"""
    statement = select(Badge).join(UserBadge).where(UserBadge.user_id == user_id)
    result = await session.exec(statement)
    return result.all()
