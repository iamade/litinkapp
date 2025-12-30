import uuid
from datetime import datetime, timezone
from typing import Optional, Dict, Any
from sqlmodel import Field, SQLModel, Column
from sqlalchemy.dialects import postgresql as pg
from sqlalchemy import text, func, ForeignKey


class ImageRecord(SQLModel, table=True):
    __tablename__ = "image_records"

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
    image_type: str = Field(nullable=False)

    scene_description: Optional[str] = Field(default=None)
    character_name: Optional[str] = Field(default=None)

    image_url: Optional[str] = Field(default=None)
    thumbnail_url: Optional[str] = Field(default=None)
    image_prompt: Optional[str] = Field(default=None)

    script_id: Optional[uuid.UUID] = Field(
        default=None, sa_column=Column(pg.UUID(as_uuid=True), index=True)
    )
    chapter_id: Optional[uuid.UUID] = Field(
        default=None, sa_column=Column(pg.UUID(as_uuid=True), index=True)
    )

    scene_number: Optional[int] = Field(default=None)
    retry_count: int = Field(default=0)
    status: str = Field(default="pending")

    generation_time_seconds: Optional[float] = Field(default=None)
    width: Optional[int] = Field(default=None)
    height: Optional[int] = Field(default=None)
    file_size_bytes: Optional[int] = Field(default=None)

    meta: Dict[str, Any] = Field(
        default={}, sa_column=Column(pg.JSONB, server_default=text("'{}'::jsonb"))
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
