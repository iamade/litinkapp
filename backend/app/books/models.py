import uuid
from datetime import datetime, timezone
from typing import Optional, List, Dict, Any
from sqlmodel import Field, SQLModel, Column, Relationship
from sqlalchemy.dialects import postgresql as pg
from sqlalchemy import text, func, ForeignKey
from pgvector.sqlalchemy import Vector


class Book(SQLModel, table=True):
    __tablename__ = "books"

    id: uuid.UUID = Field(
        sa_column=Column(
            pg.UUID(as_uuid=True),
            primary_key=True,
            server_default=text("gen_random_uuid()"),
        ),
        default_factory=uuid.uuid4,
    )
    user_id: uuid.UUID = Field(
        sa_column=Column(pg.UUID(as_uuid=True), nullable=False, index=True)
    )
    title: str = Field(nullable=False)
    author_name: Optional[str] = Field(default=None)
    description: Optional[str] = Field(default=None)
    cover_image_url: Optional[str] = Field(default=None)
    book_type: str = Field(nullable=False)

    # Mode flag: "explorer" (default) or "creator"
    source_mode: str = Field(default="explorer")

    # Optional link to Project (when uploaded via Creator mode)
    project_id: Optional[uuid.UUID] = Field(
        default=None,
        sa_column=Column(
            pg.UUID(as_uuid=True),
            ForeignKey("projects.id", ondelete="SET NULL"),
            index=True,
        ),
    )

    status: str = Field(default="draft")
    total_chapters: int = Field(default=0)
    estimated_duration: Optional[int] = Field(default=None)
    content: Optional[str] = Field(default=None, sa_column=Column(pg.TEXT))

    # Metadata fields
    difficulty: Optional[str] = Field(default="medium")
    tags: List[str] = Field(default=[], sa_column=Column(pg.ARRAY(pg.TEXT)))
    language: str = Field(default="en")

    # Structure fields
    has_sections: bool = Field(default=False)
    structure_type: str = Field(default="flat")
    original_file_storage_path: Optional[str] = Field(default=None)

    # Progress fields
    progress: int = Field(default=0)
    progress_message: Optional[str] = Field(default=None)

    # Payment fields
    stripe_checkout_session_id: Optional[str] = Field(default=None)
    stripe_payment_intent_id: Optional[str] = Field(default=None)
    stripe_customer_id: Optional[str] = Field(default=None)
    payment_status: str = Field(default="unpaid")

    created_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        sa_column=Column(
            pg.TIMESTAMP(timezone=True),
            nullable=False,
            server_default=text("CURRENT_TIMESTAMP"),
        ),
    )
    updated_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        sa_column=Column(
            pg.TIMESTAMP(timezone=True),
            nullable=False,
            server_default=text("CURRENT_TIMESTAMP"),
            onupdate=func.current_timestamp(),
        ),
    )

    # Relationships
    chapters: List["Chapter"] = Relationship(
        back_populates="book", sa_relationship_kwargs={"cascade": "all, delete-orphan"}
    )
    sections: List["Section"] = Relationship(
        back_populates="book", sa_relationship_kwargs={"cascade": "all, delete-orphan"}
    )


class Section(SQLModel, table=True):
    __tablename__ = "sections"

    id: uuid.UUID = Field(
        sa_column=Column(
            pg.UUID(as_uuid=True),
            primary_key=True,
            server_default=text("gen_random_uuid()"),
        ),
        default_factory=uuid.uuid4,
    )
    book_id: uuid.UUID = Field(
        sa_column=Column(
            pg.UUID(as_uuid=True), ForeignKey("books.id"), nullable=False, index=True
        )
    )
    title: str = Field(nullable=False)
    section_type: str = Field(nullable=False)  # "part", "tablet", "book", "section"
    section_number: str = Field(nullable=False)
    order_index: int = Field(nullable=False)
    description: Optional[str] = Field(default=None)

    created_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        sa_column=Column(
            pg.TIMESTAMP(timezone=True),
            nullable=False,
            server_default=text("CURRENT_TIMESTAMP"),
        ),
    )
    updated_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        sa_column=Column(
            pg.TIMESTAMP(timezone=True),
            nullable=False,
            server_default=text("CURRENT_TIMESTAMP"),
            onupdate=func.current_timestamp(),
        ),
    )

    # Relationships
    book: Book = Relationship(back_populates="sections")
    chapters: List["Chapter"] = Relationship(back_populates="section")


class Chapter(SQLModel, table=True):
    __tablename__ = "chapters"

    id: uuid.UUID = Field(
        sa_column=Column(
            pg.UUID(as_uuid=True),
            primary_key=True,
            server_default=text("gen_random_uuid()"),
        ),
        default_factory=uuid.uuid4,
    )
    book_id: uuid.UUID = Field(
        sa_column=Column(
            pg.UUID(as_uuid=True), ForeignKey("books.id"), nullable=False, index=True
        )
    )
    section_id: Optional[uuid.UUID] = Field(
        default=None,
        sa_column=Column(pg.UUID(as_uuid=True), ForeignKey("sections.id"), index=True),
    )

    title: str = Field(nullable=False)
    content: str = Field(nullable=False)
    chapter_number: int = Field(nullable=False)
    summary: Optional[str] = Field(default=None)
    duration: Optional[int] = Field(default=None)

    created_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        sa_column=Column(
            pg.TIMESTAMP(timezone=True),
            nullable=False,
            server_default=text("CURRENT_TIMESTAMP"),
        ),
    )
    updated_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        sa_column=Column(
            pg.TIMESTAMP(timezone=True),
            nullable=False,
            server_default=text("CURRENT_TIMESTAMP"),
            onupdate=func.current_timestamp(),
        ),
    )

    # Relationships
    book: Book = Relationship(back_populates="chapters")
    section: Optional[Section] = Relationship(back_populates="chapters")


class ChapterEmbedding(SQLModel, table=True):
    __tablename__ = "chapter_embeddings"

    id: uuid.UUID = Field(
        sa_column=Column(
            pg.UUID(as_uuid=True),
            primary_key=True,
            server_default=text("gen_random_uuid()"),
        ),
        default_factory=uuid.uuid4,
    )
    chapter_id: uuid.UUID = Field(
        sa_column=Column(
            pg.UUID(as_uuid=True),
            ForeignKey("chapters.id", ondelete="CASCADE"),
            nullable=False,
            index=True,
        )
    )
    book_id: uuid.UUID = Field(
        sa_column=Column(
            pg.UUID(as_uuid=True),
            ForeignKey("books.id", ondelete="CASCADE"),
            nullable=False,
            index=True,
        )
    )
    content_chunk: str = Field(nullable=False)
    embedding: List[float] = Field(sa_column=Column(Vector(1536)))
    chunk_index: int = Field(nullable=False)
    chunk_size: int = Field(nullable=False)
    meta: Dict[str, Any] = Field(default={}, sa_column=Column(pg.JSONB))

    created_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        sa_column=Column(
            pg.TIMESTAMP(timezone=True),
            nullable=False,
            server_default=text("CURRENT_TIMESTAMP"),
        ),
    )


class BookEmbedding(SQLModel, table=True):
    __tablename__ = "book_embeddings"

    id: uuid.UUID = Field(
        sa_column=Column(
            pg.UUID(as_uuid=True),
            primary_key=True,
            server_default=text("gen_random_uuid()"),
        ),
        default_factory=uuid.uuid4,
    )
    book_id: uuid.UUID = Field(
        sa_column=Column(
            pg.UUID(as_uuid=True),
            ForeignKey("books.id", ondelete="CASCADE"),
            nullable=False,
            index=True,
        )
    )
    content_chunk: str = Field(nullable=False)
    embedding: List[float] = Field(sa_column=Column(Vector(1536)))
    chunk_index: int = Field(nullable=False)
    chunk_size: int = Field(nullable=False)
    chunk_type: str = Field(nullable=False)  # "title", "description", "content"
    meta: Dict[str, Any] = Field(default={}, sa_column=Column(pg.JSONB))

    created_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        sa_column=Column(
            pg.TIMESTAMP(timezone=True),
            nullable=False,
            server_default=text("CURRENT_TIMESTAMP"),
        ),
    )


class LearningContent(SQLModel, table=True):
    __tablename__ = "learning_content"

    id: uuid.UUID = Field(
        sa_column=Column(
            pg.UUID(as_uuid=True),
            primary_key=True,
            server_default=text("gen_random_uuid()"),
        ),
        default_factory=uuid.uuid4,
    )
    chapter_id: uuid.UUID = Field(
        sa_column=Column(
            pg.UUID(as_uuid=True),
            ForeignKey("chapters.id", ondelete="CASCADE"),
            nullable=False,
            index=True,
        )
    )
    user_id: uuid.UUID = Field(
        sa_column=Column(pg.UUID(as_uuid=True), nullable=False, index=True)
    )
    content_type: str = Field(
        nullable=False
    )  # "audio_narration", "realistic_video", etc.
    status: str = Field(default="pending")

    # Additional fields based on potential usage (can be expanded)
    content_url: Optional[str] = Field(default=None)
    tavus_url: Optional[str] = Field(default=None)
    generation_progress: Optional[str] = Field(default=None)
    tavus_response: Dict[str, Any] = Field(default={}, sa_column=Column(pg.JSONB))
    meta: Dict[str, Any] = Field(default={}, sa_column=Column(pg.JSONB))

    created_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        sa_column=Column(
            pg.TIMESTAMP(timezone=True),
            nullable=False,
            server_default=text("CURRENT_TIMESTAMP"),
        ),
    )
    updated_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        sa_column=Column(
            pg.TIMESTAMP(timezone=True),
            nullable=False,
            server_default=text("CURRENT_TIMESTAMP"),
            onupdate=func.current_timestamp(),
        ),
    )


class UserProgress(SQLModel, table=True):
    __tablename__ = "user_progress"

    id: uuid.UUID = Field(
        sa_column=Column(
            pg.UUID(as_uuid=True),
            primary_key=True,
            server_default=text("gen_random_uuid()"),
        ),
        default_factory=uuid.uuid4,
    )
    user_id: uuid.UUID = Field(
        sa_column=Column(pg.UUID(as_uuid=True), nullable=False, index=True)
    )
    book_id: uuid.UUID = Field(
        sa_column=Column(
            pg.UUID(as_uuid=True),
            ForeignKey("books.id", ondelete="CASCADE"),
            nullable=False,
            index=True,
        )
    )
    current_chapter_id: Optional[uuid.UUID] = Field(
        default=None,
        sa_column=Column(
            pg.UUID(as_uuid=True),
            ForeignKey("chapters.id", ondelete="SET NULL"),
            nullable=True,
        ),
    )
    completed_at: Optional[datetime] = Field(default=None)
    time_spent: int = Field(default=0)  # In minutes
    last_read_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        sa_column=Column(
            pg.TIMESTAMP(timezone=True),
            nullable=False,
            server_default=text("CURRENT_TIMESTAMP"),
            onupdate=func.current_timestamp(),
        ),
    )

    created_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        sa_column=Column(
            pg.TIMESTAMP(timezone=True),
            nullable=False,
            server_default=text("CURRENT_TIMESTAMP"),
        ),
    )
    updated_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        sa_column=Column(
            pg.TIMESTAMP(timezone=True),
            nullable=False,
            server_default=text("CURRENT_TIMESTAMP"),
            onupdate=func.current_timestamp(),
        ),
    )

    # Relationships
    # book: Book = Relationship() # Circular dependency if not careful, but string forward ref works
    # current_chapter: Optional[Chapter] = Relationship()
