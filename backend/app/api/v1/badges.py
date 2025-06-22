from typing import List
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.auth import get_current_user
from app.core.database import get_db
from app.models.user import User
from app.models.badge import Badge, UserBadge
from app.schemas.badge import Badge as BadgeSchema, UserBadge as UserBadgeSchema
from app.services.blockchain_service import BlockchainService

router = APIRouter()


@router.get("/", response_model=List[BadgeSchema])
async def get_all_badges(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get all available badges"""
    badges = await Badge.get_all(db)
    return badges


@router.get("/me", response_model=List[UserBadgeSchema])
async def get_my_badges(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get current user's badges"""
    user_badges = await UserBadge.get_by_user(db, str(current_user.id))
    return user_badges


@router.post("/award/{badge_name}")
async def award_badge(
    badge_name: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Award a badge to current user (for testing/admin)"""
    # Get badge
    badge = await Badge.get_by_name(db, badge_name)
    if not badge:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Badge not found"
        )
    
    # Check if user already has this badge
    existing_badges = await UserBadge.get_by_user(db, str(current_user.id))
    if any(ub.badge_id == badge.id for ub in existing_badges):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="User already has this badge"
        )
    
    # Create blockchain NFT
    blockchain_service = BlockchainService()
    nft_result = await blockchain_service.create_badge_nft(
        badge_name,
        badge.description,
        badge.image_url,
        str(current_user.id)
    )
    
    # Award badge
    user_badge = await UserBadge.create(
        db,
        user_id=str(current_user.id),
        badge_id=str(badge.id),
        blockchain_asset_id=nft_result.get("asset_id") if nft_result else None,
        transaction_id=nft_result.get("transaction_id") if nft_result else None
    )
    
    return {
        "message": "Badge awarded successfully",
        "badge": badge,
        "blockchain_info": nft_result
    }


@router.get("/leaderboard")
async def get_badge_leaderboard(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get badge leaderboard"""
    # This would require a more complex query to aggregate user badge counts
    # For now, return a simple response
    return {
        "message": "Leaderboard feature coming soon",
        "top_users": []
    }