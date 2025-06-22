from typing import List
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.auth import get_current_user
from app.core.database import get_db
from app.models.user import User
from app.models.nft import NFTCollectible, UserCollectible
from app.schemas.nft import NFTCollectible as NFTSchema, UserCollectible as UserCollectibleSchema
from app.services.blockchain_service import BlockchainService

router = APIRouter()


@router.get("/collectibles/{book_id}", response_model=List[NFTSchema])
async def get_book_collectibles(
    book_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get NFT collectibles for a book"""
    collectibles = await NFTCollectible.get_by_book(db, book_id)
    return collectibles


@router.get("/me", response_model=List[UserCollectibleSchema])
async def get_my_collectibles(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get current user's NFT collectibles"""
    user_collectibles = await UserCollectible.get_by_user(db, str(current_user.id))
    return user_collectibles


@router.post("/award")
async def award_story_nft(
    story_moment: str,
    book_id: str,
    chapter_id: str = None,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Award a story NFT to current user"""
    # Create NFT collectible if it doesn't exist
    collectible = await NFTCollectible.create(
        db,
        name=f"{story_moment} Moment",
        description=f"A unique collectible from your story journey: {story_moment}",
        story_moment=story_moment,
        book_id=book_id,
        chapter_id=chapter_id,
        rarity="rare"
    )
    
    # Create blockchain NFT
    blockchain_service = BlockchainService()
    nft_result = await blockchain_service.create_story_nft(
        collectible.name,
        collectible.description,
        collectible.image_url,
        story_moment,
        str(current_user.id)
    )
    
    # Award collectible to user
    user_collectible = await UserCollectible.create(
        db,
        user_id=str(current_user.id),
        collectible_id=str(collectible.id),
        blockchain_asset_id=nft_result.get("asset_id") if nft_result else None,
        transaction_id=nft_result.get("transaction_id") if nft_result else None
    )
    
    return {
        "message": "Story NFT awarded successfully",
        "collectible": collectible,
        "blockchain_info": nft_result
    }


@router.get("/marketplace")
async def get_nft_marketplace(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get NFT marketplace (future feature)"""
    return {
        "message": "NFT marketplace coming soon",
        "featured_nfts": []
    }