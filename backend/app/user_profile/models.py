import uuid
from datetime import datetime, timezone
from typing import Optional, Dict, Any
from sqlmodel import Field, SQLModel, Column, Relationship
from sqlalchemy.dialects import postgresql as pg
from sqlalchemy import text, func


class Profile(SQLModel, table=True):
    __tablename__ = "profiles"

    id: uuid.UUID = Field(
        sa_column=Column(
            pg.UUID(as_uuid=True),
            primary_key=True,
            server_default=text("gen_random_uuid()"),
        ),
        default_factory=uuid.uuid4,
    )
    user_id: uuid.UUID = Field(
        sa_column=Column(pg.UUID(as_uuid=True), nullable=False, unique=True, index=True)
    )
    bio: Optional[str] = Field(default=None)
    avatar_url: Optional[str] = Field(default=None)
    website: Optional[str] = Field(default=None)
    location: Optional[str] = Field(default=None)

    # JSON fields
    social_links: Dict[str, Any] = Field(
        default={}, sa_column=Column(pg.JSONB, server_default=text("'{}'::jsonb"))
    )
    preferences: Dict[str, Any] = Field(
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
