from sqlalchemy import Column, String, Integer, Text, DateTime, Enum, ForeignKey, Boolean, ARRAY
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import relationship
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy.sql import func
import uuid
import enum
from datetime import datetime
from typing import Optional, List

from app.core.database import Base


class BookType(str, enum.Enum):
    LEARNING = "learning"
    ENTERTAINMENT = "entertainment"


class DifficultyLevel(str, enum.Enum):
    EASY = "easy"
    MEDIUM = "medium"
    HARD = "hard"


class BookStatus(str, enum.Enum):
    DRAFT = "draft"
    PUBLISHED = "published"
    ARCHIVED = "archived"


class Book(Base):
    __tablename__ = "books"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    title = Column(String, nullable=False)
    author_name = Column(String, nullable=False)
    author_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)
    description = Column(Text, nullable=True)
    cover_image_url = Column(String, nullable=True)
    book_type = Column(Enum(BookType), nullable=False)
    difficulty = Column(Enum(DifficultyLevel), default=DifficultyLevel.MEDIUM)
    status = Column(Enum(BookStatus), default=BookStatus.DRAFT)
    total_chapters = Column(Integer, default=0)
    estimated_duration = Column(Integer, nullable=True)  # in minutes
    tags = Column(ARRAY(String), nullable=True)
    language = Column(String, default="en")
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    # Relationships
    chapters = relationship("Chapter", back_populates="book", cascade="all, delete-orphan")

    @classmethod
    async def get_by_id(cls, db: AsyncSession, book_id: str) -> Optional["Book"]:
        """Get book by ID"""
        result = await db.execute(select(cls).where(cls.id == book_id))
        return result.scalar_one_or_none()

    @classmethod
    async def get_published_books(cls, db: AsyncSession, book_type: Optional[BookType] = None) -> List["Book"]:
        """Get published books"""
        query = select(cls).where(cls.status == BookStatus.PUBLISHED)
        if book_type:
            query = query.where(cls.book_type == book_type)
        
        result = await db.execute(query)
        return result.scalars().all()

    @classmethod
    async def get_by_author(cls, db: AsyncSession, author_id: str) -> List["Book"]:
        """Get books by author"""
        result = await db.execute(select(cls).where(cls.author_id == author_id))
        return result.scalars().all()

    @classmethod
    async def create(cls, db: AsyncSession, **kwargs) -> "Book":
        """Create new book"""
        book = cls(**kwargs)
        db.add(book)
        await db.commit()
        await db.refresh(book)
        return book


class Chapter(Base):
    __tablename__ = "chapters"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    book_id = Column(UUID(as_uuid=True), ForeignKey("books.id"), nullable=False)
    chapter_number = Column(Integer, nullable=False)
    title = Column(String, nullable=False)
    content = Column(Text, nullable=False)
    summary = Column(Text, nullable=True)
    duration = Column(Integer, nullable=True)  # in minutes
    ai_generated_content = Column(JSONB, nullable=True)  # Store AI-generated lessons, quizzes, etc.
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    # Relationships
    book = relationship("Book", back_populates="chapters")

    @classmethod
    async def get_by_book(cls, db: AsyncSession, book_id: str) -> List["Chapter"]:
        """Get chapters by book ID"""
        result = await db.execute(
            select(cls).where(cls.book_id == book_id).order_by(cls.chapter_number)
        )
        return result.scalars().all()

    @classmethod
    async def get_by_id(cls, db: AsyncSession, chapter_id: str) -> Optional["Chapter"]:
        """Get chapter by ID"""
        result = await db.execute(select(cls).where(cls.id == chapter_id))
        return result.scalar_one_or_none()

    @classmethod
    async def create(cls, db: AsyncSession, **kwargs) -> "Chapter":
        """Create new chapter"""
        chapter = cls(**kwargs)
        db.add(chapter)
        await db.commit()
        await db.refresh(chapter)
        return chapter