import uuid
from datetime import datetime, timezone
from typing import List, Dict, Any, Optional
from sqlmodel import Field, SQLModel, Column
from sqlalchemy.dialects import postgresql as pg
from sqlalchemy import text, func


class MergeOperation(SQLModel, table=True):
    __tablename__ = "merge_operations"

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
    video_generation_id: Optional[uuid.UUID] = Field(
        default=None, sa_column=Column(pg.UUID(as_uuid=True), index=True)
    )

    merge_status: str = Field(default="PENDING")
    progress: float = Field(default=0.0)

    # JSON fields
    input_sources: List[Dict[str, Any]] = Field(
        default=[], sa_column=Column(pg.JSONB, server_default=text("'[]'::jsonb"))
    )
    ffmpeg_params: Optional[Dict[str, Any]] = Field(
        default=None, sa_column=Column(pg.JSONB)
    )
    processing_stats: Optional[Dict[str, Any]] = Field(
        default=None, sa_column=Column(pg.JSONB)
    )

    quality_tier: Optional[str] = Field(default=None)
    output_format: Optional[str] = Field(default=None)
    merge_name: Optional[str] = Field(default=None)

    output_file_url: Optional[str] = Field(default=None)
    preview_url: Optional[str] = Field(default=None)
    error_message: Optional[str] = Field(default=None)

    # Additional file URLs for direct uploads
    video_file_url: Optional[str] = Field(default=None)
    audio_file_url: Optional[str] = Field(default=None)

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
