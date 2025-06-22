from typing import List
from fastapi import APIRouter, Depends, HTTPException, status
from supabase import Client

from app.core.auth import get_current_user
from app.core.database import get_supabase
from app.models.user import User
from app.models.badge import Badge, UserBadge
from app.schemas.badge import Badge as BadgeSchema, UserBadge as UserBadgeSchema
from app.services.blockchain_service import BlockchainService

router = APIRouter()


@router.get("/", response_model=List[BadgeSchema])
async def get_all_badges(
    supabase_client: Client = Depends(get_supabase),
    current_user: User = Depends(get_current_user)
):
    """Get all available badges"""
    response = supabase_client.table('badges').select('*').execute()
    if response.error:
        raise HTTPException(status_code=400, detail=response.error.message)
    return response.data


@router.get("/me", response_model=List[UserBadgeSchema])
async def get_my_badges(
    supabase_client: Client = Depends(get_supabase),
    current_user: User = Depends(get_current_user)
):
    """Get current user's badges"""
    response = supabase_client.table('user_badges').select('badges(*)').eq('user_id', current_user.id).execute()
    
    if response.error:
        raise HTTPException(status_code=400, detail=response.error.message)
        
    # The result is a list of {'badges': {...}} dicts, so we extract the badge details.
    user_badges = [item['badges'] for item in response.data if item.get('badges')]
    
    return user_badges


@router.post("/award/{badge_name}")
async def award_badge(
    badge_name: str,
    supabase_client: Client = Depends(get_supabase),
    current_user: User = Depends(get_current_user)
):
    """Award a badge to current user (for testing/admin)"""
    # Get badge
    response = supabase_client.table('badges').select('*').eq('name', badge_name).single().execute()
    if response.error:
        raise HTTPException(status_code=404, detail="Badge not found")
    badge = response.data
    
    # Check if user already has this badge
    response = supabase_client.table('user_badges').select('*').eq('user_id', current_user.id).eq('badge_id', badge['id']).execute()
    if response.data:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="User already has this badge"
        )
    
    # Create blockchain NFT
    blockchain_service = BlockchainService()
    nft_result = await blockchain_service.create_badge_nft(
        badge_name,
        badge['description'],
        badge['image_url'],
        str(current_user.id)
    )
    
    # Award badge
    response = supabase_client.table('user_badges').insert({
        'user_id': current_user.id,
        'badge_id': badge['id'],
        'blockchain_asset_id': nft_result.get("asset_id") if nft_result else None,
        'transaction_id': nft_result.get("transaction_id") if nft_result else None
    }).execute()
    
    if response.error:
        raise HTTPException(status_code=400, detail=response.error.message)
    
    return {
        "message": "Badge awarded successfully",
        "badge": badge,
        "blockchain_info": nft_result
    }


@router.get("/leaderboard")
async def get_badge_leaderboard(
    supabase_client: Client = Depends(get_supabase),
    current_user: User = Depends(get_current_user)
):
    """Get badge leaderboard"""
    # This would require a more complex query to aggregate user badge counts
    # For now, return a simple response
    return {
        "message": "Leaderboard feature coming soon",
        "top_users": []
    }