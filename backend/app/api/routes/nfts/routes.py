from fastapi import APIRouter, Depends, HTTPException
from typing import List
from sqlmodel.ext.asyncio.session import AsyncSession
from sqlmodel import select
import uuid

from app.nfts.schemas import NFTCreate
from app.nfts.models import NFT
from app.core.database import get_session
from app.core.auth import get_current_active_user
from app.core.services.blockchain import BlockchainService

router = APIRouter()
blockchain_service = BlockchainService()


@router.post("/", response_model=NFT, status_code=201)
async def create_nft(
    nft_create: NFTCreate,
    session: AsyncSession = Depends(get_session),
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

    nft = NFT(
        name=nft_create.name,
        description=nft_create.description,
        asset_id=result["asset_id"],
        tx_id=result["tx_id"],
        metadata_url=nft_create.metadata_url,
        owner_id=uuid.UUID(current_user["id"]),
    )

    session.add(nft)
    await session.commit()
    await session.refresh(nft)

    return nft


@router.get("/user/{user_id}", response_model=List[NFT])
async def get_user_nfts(user_id: str, session: AsyncSession = Depends(get_session)):
    """Get all NFTs owned by a specific user"""
    stmt = select(NFT).where(NFT.owner_id == uuid.UUID(user_id))
    result = await session.exec(stmt)
    return result.all()


@router.get("/{asset_id}", response_model=NFT)
async def get_nft_details(asset_id: int, session: AsyncSession = Depends(get_session)):
    """Get details for a specific NFT by its asset ID"""
    stmt = select(NFT).where(NFT.asset_id == asset_id)
    result = await session.exec(stmt)
    nft = result.first()

    if not nft:
        raise HTTPException(status_code=404, detail="NFT not found")
    return nft
