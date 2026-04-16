"""
Trailer models for KAN-149 and KAN-150.

TrailerGeneration - tracks trailer generation pipeline state
TrailerScene - stores selected/analyzed scenes for trailer
"""

import uuid
from datetime import datetime, timezone
from typing import Optional, List, Dict, Any
from sqlmodel import Field, SQLModel, Column, Relationship
from sqlalchemy.dialects import postgresql as pg
from sqlalchemy import text, func, ForeignKey
from enum import Enum


class TrailerStatus(str, Enum):
    """Trailer generation workflow status"""
    ANALYZING = "analyzing"           # Analyzing project for scene selection
    SCENES_SELECTED = "scenes_selected"  # AI has selected highlight scenes
    SCRIPT_GENERATING = "script_generating"  # Generating trailer script
    SCRIPT_READY = "script_ready"     # Script ready for review
    AUDIO_GENERATING = "audio_generating"  # Generating narration
    AUDIO_READY = "audio_ready"       # Narration audio ready
    ASSEMBLING = "assembling"          # Assembling final video
    COMPLETED = "completed"            # Trailer complete
    FAILED = "failed"                  # Generation failed


class SelectionMethod(str, Enum):
    """How scenes were selected for trailer"""
    AI_AUTO = "ai_auto"               # AI automatically selected
    USER_MANUAL = "user_manual"        # User manually selected
    AI_SUGGESTED_USER_APPROVED = "ai_suggested_user_approved"  # AI suggested, user approved


class TrailerGeneration(SQLModel, table=True):
    """Main trailer generation record"""
    __tablename__ = "trailer_generations"

    id: uuid.UUID = Field(
        sa_column=Column(
            pg.UUID(as_uuid=True),
            primary_key=True,
            server_default=text("gen_random_uuid()"),
        ),
        default_factory=uuid.uuid4,
    )
    project_id: uuid.UUID = Field(
        sa_column=Column(
            pg.UUID(as_uuid=True),
            ForeignKey("projects.id", ondelete="CASCADE"),
            nullable=False,
            index=True,
        ),
    )
    user_id: uuid.UUID = Field(
        sa_column=Column(
            pg.UUID(as_uuid=True),
            ForeignKey("user.id", ondelete="CASCADE"),
            nullable=False,
            index=True,
        ),
    )

    # Configuration from trailer_config
    target_duration_seconds: int = Field(default=90)
    tone: str = Field(default="epic")
    style: str = Field(default="cinematic")

    # Generation state
    status: TrailerStatus = Field(
        default=TrailerStatus.ANALYZING,
        sa_column=Column(
            pg.ENUM(TrailerStatus, name="trailer_status", create_type=False),
            nullable=False,
        ),
    )
    selection_method: SelectionMethod = Field(
        default=SelectionMethod.AI_AUTO,
        sa_column=Column(
            pg.ENUM(SelectionMethod, name="selection_method", create_type=False),
            nullable=False,
        ),
    )

    # Generated content
    trailer_script: Optional[str] = Field(
        default=None,
        sa_column=Column(pg.TEXT),
    )
    narration_text: Optional[str] = Field(
        default=None,
        sa_column=Column(pg.TEXT),
    )
    narration_audio_url: Optional[str] = Field(default=None)

    # Final output
    video_url: Optional[str] = Field(default=None)
    thumbnail_url: Optional[str] = Field(default=None)

    # Metadata
    total_scenes_analyzed: int = Field(default=0)
    scenes_selected_count: int = Field(default=0)
    actual_duration_seconds: Optional[int] = Field(default=None)

    # Credit cost tracking
    credits_used: int = Field(default=0)

    # Error handling
    error_message: Optional[str] = Field(
        default=None,
        sa_column=Column(pg.TEXT),
    )

    # Timestamps
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
    completed_at: Optional[datetime] = Field(default=None)

    # Relationships
    scenes: List["TrailerScene"] = Relationship(
        back_populates="trailer_generation",
        sa_relationship_kwargs={"cascade": "all, delete-orphan"},
    )


class TrailerScene(SQLModel, table=True):
    """Individual scene selected for trailer inclusion"""
    __tablename__ = "trailer_scenes"

    id: uuid.UUID = Field(
        sa_column=Column(
            pg.UUID(as_uuid=True),
            primary_key=True,
            server_default=text("gen_random_uuid()"),
        ),
        default_factory=uuid.uuid4,
    )
    trailer_generation_id: uuid.UUID = Field(
        sa_column=Column(
            pg.UUID(as_uuid=True),
            ForeignKey("trailer_generations.id", ondelete="CASCADE"),
            nullable=False,
            index=True,
        ),
    )

    # Source scene reference (from project's chapters/artifacts)
    chapter_id: Optional[uuid.UUID] = Field(default=None)
    artifact_id: Optional[uuid.UUID] = Field(default=None)
    scene_number: int = Field(nullable=False)  # Position in trailer sequence

    # Scene content
    scene_title: Optional[str] = Field(default=None)
    scene_description: Optional[str] = Field(
        default=None,
        sa_column=Column(pg.TEXT),
    )

    # AI scoring (from KAN-149 scene selection)
    action_score: float = Field(default=0.0)      # 0-1 action intensity
    emotional_score: float = Field(default=0.0)   # 0-1 emotional impact
    visual_score: float = Field(default=0.0)       # 0-1 visual appeal
    narrative_score: float = Field(default=0.0)   # 0-1 narrative importance
    overall_score: float = Field(default=0.0)      # Weighted overall score

    # Selection metadata
    is_selected: bool = Field(default=False)
    selection_reason: Optional[str] = Field(
        default=None,
        sa_column=Column(pg.TEXT),
    )  # AI-generated explanation for selection

    # Timing in trailer
    start_time_seconds: float = Field(default=0.0)
    duration_seconds: float = Field(default=5.0)

    # Media references (generated in later phases)
    image_url: Optional[str] = Field(default=None)
    video_url: Optional[str] = Field(default=None)
    audio_url: Optional[str] = Field(default=None)

    created_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        sa_column=Column(
            pg.TIMESTAMP(timezone=True),
            nullable=False,
            server_default=text("CURRENT_TIMESTAMP"),
        ),
    )

    # Relationships
    trailer_generation: TrailerGeneration = Relationship(back_populates="scenes")