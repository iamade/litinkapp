import uuid
from datetime import datetime, timezone
from typing import Optional, List
from sqlmodel import Field, SQLModel, Column, Relationship
from sqlalchemy.dialects import postgresql as pg
from sqlalchemy import text, func, ForeignKey


class Audiobook(SQLModel, table=True):
    __tablename__ = "audiobooks"

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
    title: str = Field(nullable=False)
    status: str = Field(default="pending")  # pending/generating/completed/failed
    voice_id: Optional[str] = Field(default=None)
    total_chapters: int = Field(default=0)
    completed_chapters: int = Field(default=0)
    total_duration_seconds: Optional[float] = Field(default=0.0)
    error_message: Optional[str] = Field(default=None)
    credits_reserved: int = Field(default=0)
    credits_used: int = Field(default=0)

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
    chapters: List["AudiobookChapter"] = Relationship(
        back_populates="audiobook",
        sa_relationship_kwargs={"cascade": "all, delete-orphan"},
    )


class AudiobookChapter(SQLModel, table=True):
    __tablename__ = "audiobook_chapters"

    id: uuid.UUID = Field(
        sa_column=Column(
            pg.UUID(as_uuid=True),
            primary_key=True,
            server_default=text("gen_random_uuid()"),
        ),
        default_factory=uuid.uuid4,
    )
    audiobook_id: uuid.UUID = Field(
        sa_column=Column(
            pg.UUID(as_uuid=True),
            ForeignKey("audiobooks.id", ondelete="CASCADE"),
            nullable=False,
            index=True,
        )
    )
    chapter_id: uuid.UUID = Field(
        sa_column=Column(
            pg.UUID(as_uuid=True),
            ForeignKey("chapters.id", ondelete="CASCADE"),
            nullable=False,
            index=True,
        )
    )
    chapter_number: int = Field(nullable=False)
    status: str = Field(default="pending")  # pending/generating/completed/failed
    audio_url: Optional[str] = Field(default=None)
    duration_seconds: Optional[float] = Field(default=0.0)
    credits_used: int = Field(default=0)
    error_message: Optional[str] = Field(default=None)

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
    audiobook: Audiobook = Relationship(back_populates="chapters")
