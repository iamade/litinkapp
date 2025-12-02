import uuid
from datetime import datetime, timezone
from typing import Optional, List, Dict, Any
from sqlmodel import Field, SQLModel, Column, Relationship
from sqlalchemy.dialects import postgresql as pg
from sqlalchemy import text, func, ForeignKey


class PlotOverview(SQLModel, table=True):
    __tablename__ = "plot_overviews"

    id: uuid.UUID = Field(
        sa_column=Column(
            pg.UUID(as_uuid=True),
            primary_key=True,
            server_default=text("gen_random_uuid()"),
        ),
        default_factory=uuid.uuid4,
    )
    book_id: uuid.UUID = Field(
        sa_column=Column(pg.UUID(as_uuid=True), nullable=False, index=True)
    )
    user_id: uuid.UUID = Field(
        sa_column=Column(pg.UUID(as_uuid=True), nullable=False, index=True)
    )
    logline: Optional[str] = Field(default=None)

    # JSON fields
    themes: List[str] = Field(
        default=[], sa_column=Column(pg.JSONB, server_default=text("'[]'::jsonb"))
    )

    story_type: Optional[str] = Field(default=None)
    script_story_type: Optional[str] = Field(default=None)
    genre: Optional[str] = Field(default=None)
    tone: Optional[str] = Field(default=None)
    audience: Optional[str] = Field(default=None)
    setting: Optional[str] = Field(default=None)

    generation_method: Optional[str] = Field(default=None)
    model_used: Optional[str] = Field(default=None)
    status: str = Field(default="pending")
    version: int = Field(default=1)

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
    characters: List["Character"] = Relationship(
        back_populates="plot_overview",
        sa_relationship_kwargs={"cascade": "all, delete-orphan"},
    )
    chapter_scripts: List["ChapterScript"] = Relationship(
        back_populates="plot_overview",
        sa_relationship_kwargs={"cascade": "all, delete-orphan"},
    )


class Character(SQLModel, table=True):
    __tablename__ = "characters"

    id: uuid.UUID = Field(
        sa_column=Column(
            pg.UUID(as_uuid=True),
            primary_key=True,
            server_default=text("gen_random_uuid()"),
        ),
        default_factory=uuid.uuid4,
    )
    plot_overview_id: uuid.UUID = Field(
        sa_column=Column(
            pg.UUID(as_uuid=True),
            ForeignKey("plot_overviews.id"),
            nullable=False,
            index=True,
        )
    )
    book_id: uuid.UUID = Field(
        sa_column=Column(pg.UUID(as_uuid=True), nullable=False, index=True)
    )
    user_id: uuid.UUID = Field(
        sa_column=Column(pg.UUID(as_uuid=True), nullable=False, index=True)
    )

    name: str = Field(nullable=False)
    role: Optional[str] = Field(default=None)
    character_arc: Optional[str] = Field(default=None)
    physical_description: Optional[str] = Field(default=None)
    personality: Optional[str] = Field(default=None)

    # JSON fields
    archetypes: List[str] = Field(
        default=[], sa_column=Column(pg.JSONB, server_default=text("'[]'::jsonb"))
    )

    want: Optional[str] = Field(default=None)
    need: Optional[str] = Field(default=None)
    lie: Optional[str] = Field(default=None)
    ghost: Optional[str] = Field(default=None)

    image_url: Optional[str] = Field(default=None)
    image_generation_prompt: Optional[str] = Field(default=None)

    image_metadata: Dict[str, Any] = Field(
        default={}, sa_column=Column(pg.JSONB, server_default=text("'{}'::jsonb"))
    )

    status: str = Field(default="active")

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
    plot_overview: PlotOverview = Relationship(back_populates="characters")


class ChapterScript(SQLModel, table=True):
    __tablename__ = "chapter_scripts"

    id: uuid.UUID = Field(
        sa_column=Column(
            pg.UUID(as_uuid=True),
            primary_key=True,
            server_default=text("gen_random_uuid()"),
        ),
        default_factory=uuid.uuid4,
    )
    chapter_id: uuid.UUID = Field(
        sa_column=Column(pg.UUID(as_uuid=True), nullable=False, index=True)
    )
    plot_overview_id: Optional[uuid.UUID] = Field(
        default=None,
        sa_column=Column(
            pg.UUID(as_uuid=True), ForeignKey("plot_overviews.id"), index=True
        ),
    )
    user_id: uuid.UUID = Field(
        sa_column=Column(pg.UUID(as_uuid=True), nullable=False, index=True)
    )

    plot_enhanced: bool = Field(default=False)
    character_enhanced: bool = Field(default=False)

    # JSON fields
    scenes: Dict[str, Any] = Field(
        default={}, sa_column=Column(pg.JSONB, server_default=text("'{}'::jsonb"))
    )
    acts: Dict[str, Any] = Field(
        default={}, sa_column=Column(pg.JSONB, server_default=text("'{}'::jsonb"))
    )
    beats: Dict[str, Any] = Field(
        default={}, sa_column=Column(pg.JSONB, server_default=text("'{}'::jsonb"))
    )
    character_details: Dict[str, Any] = Field(
        default={}, sa_column=Column(pg.JSONB, server_default=text("'{}'::jsonb"))
    )
    character_arcs: Dict[str, Any] = Field(
        default={}, sa_column=Column(pg.JSONB, server_default=text("'{}'::jsonb"))
    )
    generation_metadata: Dict[str, Any] = Field(
        default={}, sa_column=Column(pg.JSONB, server_default=text("'{}'::jsonb"))
    )

    status: str = Field(default="pending")
    version: int = Field(default=1)

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
    plot_overview: Optional[PlotOverview] = Relationship(
        back_populates="chapter_scripts"
    )


class CharacterArchetype(SQLModel, table=True):
    __tablename__ = "character_archetypes"

    id: uuid.UUID = Field(
        sa_column=Column(
            pg.UUID(as_uuid=True),
            primary_key=True,
            server_default=text("gen_random_uuid()"),
        ),
        default_factory=uuid.uuid4,
    )
    name: str = Field(nullable=False)
    description: Optional[str] = Field(default=None)
    category: Optional[str] = Field(default=None)

    # JSON fields
    traits: Dict[str, Any] = Field(
        default={}, sa_column=Column(pg.JSONB, server_default=text("'{}'::jsonb"))
    )
    typical_roles: Dict[str, Any] = Field(
        default={}, sa_column=Column(pg.JSONB, server_default=text("'{}'::jsonb"))
    )

    example_characters: Optional[str] = Field(default=None)
    is_active: bool = Field(default=True)

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
