from sqlalchemy import Column, Integer, DateTime, ForeignKey, Text
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy.sql import func
import uuid
from datetime import datetime
from typing import Optional, List

from app.core.database import Base


class UserProgress(Base):
    __tablename__ = "user_progress"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    book_id = Column(UUID(as_uuid=True), ForeignKey("books.id"), nullable=False)
    current_chapter = Column(Integer, default=1)
    progress_percentage = Column(Integer, default=0)
    time_spent = Column(Integer, default=0)  # in minutes
    last_read_at = Column(DateTime(timezone=True), server_default=func.now())
    completed_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    @classmethod
    async def get_by_user_and_book(cls, db: AsyncSession, user_id: str, book_id: str) -> Optional["UserProgress"]:
        """Get user progress for specific book"""
        result = await db.execute(
            select(cls).where(cls.user_id == user_id, cls.book_id == book_id)
        )
        return result.scalar_one_or_none()

    @classmethod
    async def get_by_user(cls, db: AsyncSession, user_id: str) -> List["UserProgress"]:
        """Get all user progress"""
        result = await db.execute(select(cls).where(cls.user_id == user_id))
        return result.scalars().all()

    @classmethod
    async def create_or_update(cls, db: AsyncSession, user_id: str, book_id: str, **kwargs) -> "UserProgress":
        """Create or update user progress"""
        progress = await cls.get_by_user_and_book(db, user_id, book_id)
        
        if progress:
            # Update existing progress
            for key, value in kwargs.items():
                if hasattr(progress, key):
                    setattr(progress, key, value)
            progress.updated_at = datetime.utcnow()
        else:
            # Create new progress
            progress = cls(user_id=user_id, book_id=book_id, **kwargs)
            db.add(progress)
        
        await db.commit()
        await db.refresh(progress)
        return progress


class UserStoryProgress(Base):
    __tablename__ = "user_story_progress"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    book_id = Column(UUID(as_uuid=True), ForeignKey("books.id"), nullable=False)
    current_branch = Column(Text, nullable=False)
    choices_made = Column(JSONB, default=list)
    story_state = Column(JSONB, default=dict)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    @classmethod
    async def get_by_user_and_book(cls, db: AsyncSession, user_id: str, book_id: str) -> Optional["UserStoryProgress"]:
        """Get user story progress for specific book"""
        result = await db.execute(
            select(cls).where(cls.user_id == user_id, cls.book_id == book_id)
        )
        return result.scalar_one_or_none()

    @classmethod
    async def create_or_update(cls, db: AsyncSession, user_id: str, book_id: str, **kwargs) -> "UserStoryProgress":
        """Create or update user story progress"""
        progress = await cls.get_by_user_and_book(db, user_id, book_id)
        
        if progress:
            # Update existing progress
            for key, value in kwargs.items():
                if hasattr(progress, key):
                    setattr(progress, key, value)
            progress.updated_at = datetime.utcnow()
        else:
            # Create new progress
            progress = cls(user_id=user_id, book_id=book_id, **kwargs)
            db.add(progress)
        
        await db.commit()
        await db.refresh(progress)
        return progress