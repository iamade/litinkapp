from sqlalchemy import Column, String, DateTime, ForeignKey, Text, BigInteger
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy.sql import func
import uuid
from datetime import datetime
from typing import Optional, List

from app.core.database import Base


class NFTCollectible(Base):
    __tablename__ = "nft_collectibles"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String, nullable=False)
    description = Column(Text, nullable=False)
    image_url = Column(String, nullable=True)
    animation_url = Column(String, nullable=True)
    story_moment = Column(Text, nullable=False)
    rarity = Column(String, default="common")
    book_id = Column(UUID(as_uuid=True), ForeignKey("books.id"), nullable=False)
    chapter_id = Column(UUID(as_uuid=True), ForeignKey("chapters.id"), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    @classmethod
    async def get_by_book(cls, db: AsyncSession, book_id: str) -> List["NFTCollectible"]:
        """Get NFT collectibles by book"""
        result = await db.execute(select(cls).where(cls.book_id == book_id))
        return result.scalars().all()


class UserCollectible(Base):
    __tablename__ = "user_collectibles"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    collectible_id = Column(UUID(as_uuid=True), ForeignKey("nft_collectibles.id"), nullable=False)
    earned_at = Column(DateTime(timezone=True), server_default=func.now())
    blockchain_asset_id = Column(BigInteger, nullable=True)
    transaction_id = Column(String, nullable=True)

    @classmethod
    async def get_by_user(cls, db: AsyncSession, user_id: str) -> List["UserCollectible"]:
        """Get user collectibles"""
        result = await db.execute(select(cls).where(cls.user_id == user_id))
        return result.scalars().all()

    @classmethod
    async def create(cls, db: AsyncSession, **kwargs) -> "UserCollectible":
        """Award collectible to user"""
        user_collectible = cls(**kwargs)
        db.add(user_collectible)
        await db.commit()
        await db.refresh(user_collectible)
        return user_collectible