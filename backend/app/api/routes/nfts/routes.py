from fastapi import APIRouter, Depends, HTTPException
from typing import List
from supabase import Client

from app.nfts.schemas import NFT, NFTCreate
from app.core.database import get_supabase
from app.core.auth import get_current_active_user
from app.core.services.blockchain import BlockchainService

router = APIRouter()
blockchain_service = BlockchainService()


@router.post("/", response_model=NFT, status_code=201)
async def create_nft(
    nft_create: NFTCreate,
    supabase_client: Client = Depends(get_supabase),
    current_user: dict = Depends(get_current_active_user),
):
    """Mint a new NFT (e.g., for completing a book)"""

    if not current_user.get("wallet_mnemonic"):
        raise HTTPException(status_code=400, detail="User wallet not configured.")

    result = await blockchain_service.create_nft(
        asset_name=nft_create.name,
        unit_name="LITNFT",
        total=1,
        url=nft_create.metadata_url,
        creator_mnemonic=current_user["wallet_mnemonic"],
    )

    nft_data = {
        "name": nft_create.name,
        "description": nft_create.description,
        "asset_id": result["asset_id"],
        "tx_id": result["tx_id"],
        "metadata_url": nft_create.metadata_url,
        "owner_id": current_user["id"],
    }

    response = supabase_client.table("nfts").insert(nft_data).execute()
    if response.error:
        raise HTTPException(
            status_code=500,
            detail=f"Blockchain succeeded, but DB insert failed: {response.error.message}",
        )

    return response.data[0]


@router.get("/user/{user_id}", response_model=List[NFT])
async def get_user_nfts(user_id: str, supabase_client: Client = Depends(get_supabase)):
    """Get all NFTs owned by a specific user"""
    response = (
        supabase_client.table("nfts").select("*").eq("owner_id", user_id).execute()
    )
    if response.error:
        raise HTTPException(status_code=400, detail=response.error.message)
    return response.data


@router.get("/{asset_id}", response_model=NFT)
async def get_nft_details(
    asset_id: int, supabase_client: Client = Depends(get_supabase)
):
    """Get details for a specific NFT by its asset ID"""
    response = (
        supabase_client.table("nfts")
        .select("*")
        .eq("asset_id", asset_id)
        .single()
        .execute()
    )
    if response.error:
        raise HTTPException(status_code=404, detail="NFT not found")
    return response.data


# from typing import List
# from fastapi import APIRouter, Depends, HTTPException, status
# from sqlalchemy.ext.asyncio import AsyncSession
# from supabase import Client

# from app.core.auth import get_current_user
# from app.core.database import get_supabase
# from app.models.user import User
# from app.models.nft import NFTCollectible, UserCollectible
# from app.schemas.nft import NFTCollectible as NFTSchema, UserCollectible as UserCollectibleSchema
# from app.services.blockchain_service import BlockchainService
# from app.schemas import NFT, NFTCreate, User
# from app.core.auth import get_current_active_user

# router = APIRouter()
# blockchain_service = BlockchainService()


# @router.get("/collectibles/{book_id}", response_model=List[NFTSchema])
# async def get_book_collectibles(
#     book_id: str,
#     db: AsyncSession = Depends(get_supabase),
#     current_user: User = Depends(get_current_user)
# ):
#     """Get NFT collectibles for a book"""
#     collectibles = await NFTCollectible.get_by_book(db, book_id)
#     return collectibles


# @router.get("/me", response_model=List[UserCollectibleSchema])
# async def get_my_collectibles(
#     db: AsyncSession = Depends(get_supabase),
#     current_user: User = Depends(get_current_user)
# ):
#     """Get current user's NFT collectibles"""
#     user_collectibles = await UserCollectible.get_by_user(db, str(current_user.id))
#     return user_collectibles


# @router.post("/award")
# async def award_story_nft(
#     story_moment: str,
#     book_id: str,
#     chapter_id: str = None,
#     db: AsyncSession = Depends(get_supabase),
#     current_user: User = Depends(get_current_user)
# ):
#     """Award a story NFT to current user"""
#     # Create NFT collectible if it doesn't exist
#     collectible = await NFTCollectible.create(
#         db,
#         name=f"{story_moment} Moment",
#         description=f"A unique collectible from your story journey: {story_moment}",
#         story_moment=story_moment,
#         book_id=book_id,
#         chapter_id=chapter_id,
#         rarity="rare"
#     )

#     # Create blockchain NFT
#     nft_result = await blockchain_service.create_story_nft(
#         collectible.name,
#         collectible.description,
#         collectible.image_url,
#         story_moment,
#         str(current_user.id)
#     )

#     # Award collectible to user
#     user_collectible = await UserCollectible.create(
#         db,
#         user_id=str(current_user.id),
#         collectible_id=str(collectible.id),
#         blockchain_asset_id=nft_result.get("asset_id") if nft_result else None,
#         transaction_id=nft_result.get("transaction_id") if nft_result else None
#     )

#     return {
#         "message": "Story NFT awarded successfully",
#         "collectible": collectible,
#         "blockchain_info": nft_result
#     }


# @router.get("/marketplace")
# async def get_nft_marketplace(
#     db: AsyncSession = Depends(get_supabase),
#     current_user: User = Depends(get_current_user)
# ):
#     """Get NFT marketplace (future feature)"""
#     return {
#         "message": "NFT marketplace coming soon",
#         "featured_nfts": []
#     }


# @router.post("/", response_model=NFT, status_code=201)
# async def create_nft(
#     nft_create: NFTCreate,
#     supabase_client: Client = Depends(get_supabase),
#     current_user: dict = Depends(get_current_active_user)
# ):
#     """Mint a new NFT (e.g., for completing a book)"""

#     if not current_user.get('wallet_mnemonic'):
#         raise HTTPException(status_code=400, detail="User wallet not configured.")

#     result = await blockchain_service.create_nft(
#         asset_name=nft_create.name,
#         unit_name="LITNFT",
#         total=1,
#         url=nft_create.metadata_url,
#         creator_mnemonic=current_user['wallet_mnemonic']
#     )

#     nft_data = {
#         "name": nft_create.name,
#         "description": nft_create.description,
#         "asset_id": result['asset_id'],
#         "tx_id": result['tx_id'],
#         "metadata_url": nft_create.metadata_url,
#         "owner_id": current_user['id']
#     }

#     response = supabase_client.table('nfts').insert(nft_data).execute()
#     if response.error:
#         raise HTTPException(status_code=500, detail=f"Blockchain succeeded, but DB insert failed: {response.error.message}")

#     return response.data[0]


# @router.get("/user/{user_id}", response_model=List[NFT])
# async def get_user_nfts(
#     user_id: str,
#     supabase_client: Client = Depends(get_supabase)
# ):
#     """Get all NFTs owned by a specific user"""
#     response = supabase_client.table('nfts').select('*').eq('owner_id', user_id).execute()
#     if response.error:
#         raise HTTPException(status_code=400, detail=response.error.message)
#     return response.data


# @router.get("/{asset_id}", response_model=NFT)
# async def get_nft_details(
#     asset_id: int,
#     supabase_client: Client = Depends(get_supabase)
# ):
#     """Get details for a specific NFT by its asset ID"""
#     response = supabase_client.table('nfts').select('*').eq('asset_id', asset_id).single().execute()
#     if response.error:
#         raise HTTPException(status_code=404, detail="NFT not found")
#     return response.data
