from sqlalchemy import Column, String, Integer, DateTime, ForeignKey, Text, BigInteger
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy.sql import func
import uuid
from datetime import datetime
from typing import Optional, List

from app.core.database import Base


class Badge(Base):
    __tablename__ = "badges"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String, unique=True, nullable=False)
    description = Column(Text, nullable=False)
    image_url = Column(String, nullable=True)
    criteria = Column(Text, nullable=False)
    rarity = Column(String, default="common")
    points = Column(Integer, default=0)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    @classmethod
    async def get_all(cls, db: AsyncSession) -> List["Badge"]:
        """Get all badges"""
        result = await db.execute(select(cls))
        return result.scalars().all()

    @classmethod
    async def get_by_name(cls, db: AsyncSession, name: str) -> Optional["Badge"]:
        """Get badge by name"""
        result = await db.execute(select(cls).where(cls.name == name))
        return result.scalar_one_or_none()


class UserBadge(Base):
    __tablename__ = "user_badges"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    badge_id = Column(UUID(as_uuid=True), ForeignKey("badges.id"), nullable=False)
    earned_at = Column(DateTime(timezone=True), server_default=func.now())
    blockchain_asset_id = Column(BigInteger, nullable=True)
    transaction_id = Column(String, nullable=True)

    @classmethod
    async def get_by_user(cls, db: AsyncSession, user_id: str) -> List["UserBadge"]:
        """Get user badges"""
        result = await db.execute(select(cls).where(cls.user_id == user_id))
        return result.scalars().all()

    @classmethod
    async def create(cls, db: AsyncSession, **kwargs) -> "UserBadge":
        """Award badge to user"""
        user_badge = cls(**kwargs)
        db.add(user_badge)
        await db.commit()
        await db.refresh(user_badge)
        return user_badge