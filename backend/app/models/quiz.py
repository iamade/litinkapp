from sqlalchemy import Column, String, Integer, DateTime, ForeignKey, Text
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import relationship
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy.sql import func
import uuid
from datetime import datetime
from typing import Optional, List

from app.core.database import Base


class Quiz(Base):
    __tablename__ = "quizzes"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    chapter_id = Column(UUID(as_uuid=True), ForeignKey("chapters.id"), nullable=False)
    title = Column(String, nullable=False)
    questions = Column(JSONB, nullable=False)  # Array of question objects
    difficulty = Column(String, default="medium")
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    @classmethod
    async def get_by_chapter(cls, db: AsyncSession, chapter_id: str) -> List["Quiz"]:
        """Get quizzes by chapter ID"""
        result = await db.execute(select(cls).where(cls.chapter_id == chapter_id))
        return result.scalars().all()

    @classmethod
    async def create(cls, db: AsyncSession, **kwargs) -> "Quiz":
        """Create new quiz"""
        quiz = cls(**kwargs)
        db.add(quiz)
        await db.commit()
        await db.refresh(quiz)
        return quiz


class QuizAttempt(Base):
    __tablename__ = "quiz_attempts"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    quiz_id = Column(UUID(as_uuid=True), ForeignKey("quizzes.id"), nullable=False)
    answers = Column(JSONB, nullable=False)  # User's answers
    score = Column(Integer, nullable=False)
    completed_at = Column(DateTime(timezone=True), server_default=func.now())
    time_taken = Column(Integer, nullable=True)  # in seconds

    @classmethod
    async def get_by_user(cls, db: AsyncSession, user_id: str) -> List["QuizAttempt"]:
        """Get quiz attempts by user ID"""
        result = await db.execute(select(cls).where(cls.user_id == user_id))
        return result.scalars().all()

    @classmethod
    async def create(cls, db: AsyncSession, **kwargs) -> "QuizAttempt":
        """Create new quiz attempt"""
        attempt = cls(**kwargs)
        db.add(attempt)
        await db.commit()
        await db.refresh(attempt)
        return attempt