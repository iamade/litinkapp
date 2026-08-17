import uuid
from datetime import datetime, timezone
from typing import Optional, List, Dict, Any
from sqlmodel import Field, SQLModel, Column, Relationship
from sqlalchemy.dialects import postgresql as pg
import sqlalchemy as sa
from sqlalchemy import func, ForeignKey, Text, Integer, UniqueConstraint
from enum import Enum


class VideoGenerationStatus(str, Enum):
    PENDING = "pending"
    GENERATING_AUDIO = "generating_audio"
    AUDIO_COMPLETED = "audio_completed"
    GENERATING_IMAGES = "generating_images"
    IMAGES_COMPLETED = "images_completed"
    GENERATING_VIDEO = "generating_video"
    VIDEO_COMPLETED = "video_completed"
    MERGING_AUDIO = "merging_audio"
    APPLYING_LIPSYNC = "applying_lipsync"
    COMBINING = "combining"
    COMPLETED = "completed"
    FAILED = "failed"
    RETRYING = "retrying"
    RETRIEVAL_FAILED = "retrieval_failed"


class VideoQualityTier(str, Enum):
    FREE = "free"
    BASIC = "basic"
    STANDARD = "standard"
    STANDARD_2 = "standard_2"
    PRO = "pro"
    MASTER = "master"


class AudioType(str, Enum):
    NARRATOR = "narrator"
    CHARACTER = "character"
    SOUND_EFFECTS = "sound_effects"
    BACKGROUND_MUSIC = "background_music"


class VideoGeneration(SQLModel, table=True):
    __tablename__ = "video_generations"

    id: uuid.UUID = Field(
        sa_column=Column(
            pg.UUID(as_uuid=True),
            primary_key=True,
            server_default="gen_random_uuid()",
        ),
        default_factory=uuid.uuid4,
    )
    chapter_id: uuid.UUID = Field(
        sa_column=Column(pg.UUID(as_uuid=True), nullable=False, index=True)
    )
    user_id: uuid.UUID = Field(
        sa_column=Column(pg.UUID(as_uuid=True), nullable=False, index=True)
    )
    script_id: Optional[uuid.UUID] = Field(
        default=None, sa_column=Column(pg.UUID(as_uuid=True), index=True)
    )

    generation_status: VideoGenerationStatus = Field(
        sa_column=Column(
            pg.ENUM(VideoGenerationStatus, name="video_generation_status", values_callable=lambda e: [m.value for m in e]),
            nullable=False,
            default=VideoGenerationStatus.PENDING,
        )
    )
    quality_tier: VideoQualityTier = Field(
        sa_column=Column(
            pg.ENUM(VideoQualityTier, name="video_quality_tier", values_callable=lambda e: [m.value for m in e]),
            nullable=False,
            default=VideoQualityTier.FREE,
        )
    )

    video_url: Optional[str] = Field(default=None)
    audio_task_id: Optional[str] = Field(default=None)
    continuity_frame_url: Optional[str] = Field(default=None)

    can_resume: bool = Field(default=False)
    retry_count: int = Field(default=0)
    error_message: Optional[str] = Field(default=None)

    # JSON fields
    task_meta: Dict[str, Any] = Field(
        default={}, sa_column=Column(pg.JSONB, server_default="'{}'::jsonb")
    )
    script_data: Dict[str, Any] = Field(
        default={}, sa_column=Column(pg.JSONB, server_default="'{}'::jsonb")
    )
    audio_files: Dict[str, Any] = Field(
        default={}, sa_column=Column(pg.JSONB, server_default="'{}'::jsonb")
    )
    image_data: Dict[str, Any] = Field(
        default={}, sa_column=Column(pg.JSONB, server_default="'{}'::jsonb")
    )
    video_data: Dict[str, Any] = Field(
        default={}, sa_column=Column(pg.JSONB, server_default="'{}'::jsonb")
    )
    merge_data: Dict[str, Any] = Field(
        default={}, sa_column=Column(pg.JSONB, server_default="'{}'::jsonb")
    )
    lipsync_data: Dict[str, Any] = Field(
        default={}, sa_column=Column(pg.JSONB, server_default="'{}'::jsonb")
    )

    created_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        sa_column=Column(
            pg.TIMESTAMP(timezone=True),
            nullable=False,
            server_default="CURRENT_TIMESTAMP",
        ),
    )
    updated_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        sa_column=Column(
            pg.TIMESTAMP(timezone=True),
            nullable=False,
            server_default="CURRENT_TIMESTAMP",
            onupdate=func.current_timestamp(),
        ),
    )

    # Relationships
    audio_generations: List["AudioGeneration"] = Relationship(
        back_populates="video_generation",
        sa_relationship_kwargs={"cascade": "all, delete-orphan"},
    )
    image_generations: List["ImageGeneration"] = Relationship(
        back_populates="video_generation",
        sa_relationship_kwargs={"cascade": "all, delete-orphan"},
    )
    video_segments: List["VideoSegment"] = Relationship(
        back_populates="video_generation",
        sa_relationship_kwargs={"cascade": "all, delete-orphan"},
    )


class AudioGeneration(SQLModel, table=True):
    __tablename__ = "audio_generations"

    id: uuid.UUID = Field(
        sa_column=Column(
            pg.UUID(as_uuid=True),
            primary_key=True,
            server_default="gen_random_uuid()",
        ),
        default_factory=uuid.uuid4,
    )
    video_generation_id: Optional[uuid.UUID] = Field(
        default=None,
        sa_column=Column(
            pg.UUID(as_uuid=True),
            ForeignKey("video_generations.id"),
            nullable=True,
            index=True,
        ),
    )

    # Additional foreign keys
    user_id: Optional[uuid.UUID] = Field(
        default=None, sa_column=Column(pg.UUID(as_uuid=True), index=True)
    )
    chapter_id: Optional[uuid.UUID] = Field(
        default=None, sa_column=Column(pg.UUID(as_uuid=True), index=True)
    )
    script_id: Optional[uuid.UUID] = Field(
        default=None, sa_column=Column(pg.UUID(as_uuid=True), index=True)
    )

    audio_type: AudioType = Field(
        sa_column=Column(pg.ENUM(AudioType, name="audio_type", values_callable=lambda e: [m.value for m in e]), nullable=False)
    )

    scene_id: Optional[str] = Field(default=None)
    character_name: Optional[str] = Field(default=None)
    text_content: Optional[str] = Field(default=None)
    voice_id: Optional[str] = Field(default=None)
    audio_url: Optional[str] = Field(default=None)
    duration_seconds: Optional[float] = Field(default=None)
    status: str = Field(default="pending")

    # Additional fields for audio generation workflow
    sequence_order: Optional[int] = Field(default=None)
    model_id: Optional[str] = Field(default=None)
    error_message: Optional[str] = Field(default=None)
    audio_metadata: Dict[str, Any] = Field(
        default={}, sa_column=Column(pg.JSONB, server_default="'{}'::jsonb")
    )

    created_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        sa_column=Column(
            pg.TIMESTAMP(timezone=True),
            nullable=False,
            server_default="CURRENT_TIMESTAMP",
        ),
    )

    # Relationships
    video_generation: VideoGeneration = Relationship(back_populates="audio_generations")


class ImageGeneration(SQLModel, table=True):
    __tablename__ = "image_generations"

    id: uuid.UUID = Field(
        sa_column=Column(
            pg.UUID(as_uuid=True),
            primary_key=True,
            server_default="gen_random_uuid()",
        ),
        default_factory=uuid.uuid4,
    )
    video_generation_id: Optional[uuid.UUID] = Field(
        default=None,
        sa_column=Column(
            pg.UUID(as_uuid=True),
            ForeignKey("video_generations.id"),
            nullable=True,
            index=True,
        ),
    )

    image_type: Optional[str] = Field(default=None)
    scene_id: Optional[str] = Field(default=None)
    character_name: Optional[str] = Field(default=None)
    character_id: Optional[str] = Field(default=None)
    user_id: Optional[uuid.UUID] = Field(
        default=None, sa_column=Column(pg.UUID(as_uuid=True), index=True)
    )
    shot_index: int = Field(default=0)
    scene_description: Optional[str] = Field(default=None)

    image_prompt: Optional[str] = Field(default=None)
    text_prompt: Optional[str] = Field(default=None)
    style: Optional[str] = Field(default=None)
    aspect_ratio: Optional[str] = Field(default=None)

    image_url: Optional[str] = Field(default=None)
    thumbnail_url: Optional[str] = Field(default=None)

    width: Optional[int] = Field(default=None)
    height: Optional[int] = Field(default=None)
    file_size_bytes: Optional[int] = Field(default=None)
    generation_time_seconds: Optional[float] = Field(default=None)
    sequence_order: Optional[int] = Field(default=None)

    status: str = Field(default="pending")
    error_message: Optional[str] = Field(default=None)

    # Added fields to match DB schema
    script_id: Optional[uuid.UUID] = Field(
        default=None, sa_column=Column(pg.UUID(as_uuid=True), index=True)
    )
    chapter_id: Optional[uuid.UUID] = Field(
        default=None, sa_column=Column(pg.UUID(as_uuid=True), index=True)
    )
    scene_number: Optional[float] = Field(default=None)
    progress: int = Field(default=0)

    meta: Dict[str, Any] = Field(
        default={}, sa_column=Column(pg.JSONB, server_default="'{}'::jsonb")
    )

    created_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        sa_column=Column(
            pg.TIMESTAMP(timezone=True),
            nullable=False,
            server_default="CURRENT_TIMESTAMP",
        ),
    )
    updated_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        sa_column=Column(
            pg.TIMESTAMP(timezone=True),
            nullable=False,
            server_default="CURRENT_TIMESTAMP",
            onupdate=func.current_timestamp(),
        ),
    )

    # Model field for tracking (also in DB)
    model_id: Optional[str] = Field(default=None)

    # Relationships
    video_generation: VideoGeneration = Relationship(back_populates="image_generations")


class Script(SQLModel, table=True):
    __tablename__ = "scripts"

    id: uuid.UUID = Field(
        sa_column=Column(
            pg.UUID(as_uuid=True),
            primary_key=True,
            server_default="gen_random_uuid()",
        ),
        default_factory=uuid.uuid4,
    )
    chapter_id: uuid.UUID = Field(
        sa_column=Column(pg.UUID(as_uuid=True), nullable=False, index=True)
    )
    user_id: uuid.UUID = Field(
        sa_column=Column(pg.UUID(as_uuid=True), nullable=False, index=True)
    )

    script_style: str = Field(nullable=False)
    script_name: Optional[str] = Field(default=None)
    script: str = Field(nullable=False)
    video_style: str = Field(nullable=False)
    status: str = Field(default="draft")

    # JSON fields
    characters: List[str] = Field(
        default=[], sa_column=Column(pg.JSONB, server_default="'[]'::jsonb")
    )
    # Character IDs linking to Plot Overview characters (UUIDs as strings)
    character_ids: List[str] = Field(
        default=[], sa_column=Column(pg.JSONB, server_default="'[]'::jsonb")
    )
    # Editable scene descriptions
    scene_descriptions: List[str] = Field(
        default=[], sa_column=Column(pg.JSONB, server_default="'[]'::jsonb")
    )
    # Scene order for storyboard
    scene_order: List[int] = Field(
        default=[], sa_column=Column(pg.JSONB, server_default="'[]'::jsonb")
    )
    # Storyboard configuration: key_scene_images, deselected_images, image_order
    storyboard_config: Dict[str, Any] = Field(
        default={}, sa_column=Column(pg.JSONB, server_default="'{}'::jsonb")
    )
    character_details: Optional[str] = Field(
        default=None
    )  # The code treats it as string sometimes? "character_details": character_details (string from _generate_character_details)

    evaluation: Dict[str, Any] = Field(
        default={}, sa_column=Column(pg.JSONB, server_default="'{}'::jsonb")
    )

    emotional_map: List[Dict[str, Any]] = Field(
        default=[], sa_column=Column(pg.JSONB, server_default="'[]'::jsonb")
    )

    created_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        sa_column=Column(
            pg.TIMESTAMP(timezone=True),
            nullable=False,
            server_default="CURRENT_TIMESTAMP",
        ),
    )
    updated_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        sa_column=Column(
            pg.TIMESTAMP(timezone=True),
            nullable=False,
            server_default="CURRENT_TIMESTAMP",
            onupdate=func.current_timestamp(),
        ),
    )


class VideoSegment(SQLModel, table=True):
    __tablename__ = "video_segments"

    id: uuid.UUID = Field(
        sa_column=Column(
            pg.UUID(as_uuid=True),
            primary_key=True,
            server_default="gen_random_uuid()",
        ),
        default_factory=uuid.uuid4,
    )
    video_generation_id: uuid.UUID = Field(
        sa_column=Column(
            pg.UUID(as_uuid=True),
            ForeignKey("video_generations.id"),
            nullable=False,
            index=True,
        )
    )
    user_id: Optional[uuid.UUID] = Field(
        default=None, sa_column=Column(pg.UUID(as_uuid=True), index=True)
    )

    scene_id: str = Field(nullable=False)
    scene_number: int = Field(nullable=False)
    # KAN-438 regression fix: this column was missing from the original
    # migration. It is the canonical ordering key used by
    # shot_diversity_service.py:72 and continuity_service.py:177.
    # Populated by backfill (existing rows) and by the `video_tasks.py`
    # insert paths (new rows). Backed by an index added in migration
    # `kan_438_video_segments_sequence_index`.
    sequence_index: int = Field(nullable=False, index=True)
    video_url: Optional[str] = Field(default=None)
    scene_description: Optional[str] = Field(default=None)

    character_count: int = Field(default=0)
    dialogue_count: int = Field(default=0)
    action_count: int = Field(default=0)

    camera_movements: List[str] = Field(
        default=[], sa_column=Column(pg.JSONB, server_default="'[]'::jsonb")
    )
    character_names: List[str] = Field(
        default=[], sa_column=Column(pg.JSONB, server_default="'[]'::jsonb")
    )

    status: str = Field(default="pending")
    prompt_length: Optional[int] = Field(default=None)
    target_duration: Optional[float] = Field(default=None)

    created_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        sa_column=Column(
            pg.TIMESTAMP(timezone=True),
            nullable=False,
            server_default="CURRENT_TIMESTAMP",
        ),
    )

    # Relationships
    video_generation: VideoGeneration = Relationship(back_populates="video_segments")


class PipelineStepModel(SQLModel, table=True):
    __tablename__ = "pipeline_steps"

    id: uuid.UUID = Field(
        sa_column=Column(
            pg.UUID(as_uuid=True),
            primary_key=True,
            server_default="gen_random_uuid()",
        ),
        default_factory=uuid.uuid4,
    )
    video_generation_id: uuid.UUID = Field(
        sa_column=Column(
            pg.UUID(as_uuid=True),
            ForeignKey("video_generations.id"),
            nullable=False,
            index=True,
        )
    )
    step_name: str = Field(nullable=False)
    step_order: int = Field(nullable=False)
    status: str = Field(default="pending")

    started_at: Optional[datetime] = Field(default=None)
    completed_at: Optional[datetime] = Field(default=None)
    error_message: Optional[str] = Field(default=None)
    retry_count: int = Field(default=0)

    step_data: Dict[str, Any] = Field(
        default={}, sa_column=Column(pg.JSONB, server_default="'{}'::jsonb")
    )

    created_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        sa_column=Column(
            pg.TIMESTAMP(timezone=True),
            nullable=False,
            server_default="CURRENT_TIMESTAMP",
        ),
    )


class AudioExport(SQLModel, table=True):
    __tablename__ = "audio_exports"

    id: uuid.UUID = Field(
        sa_column=Column(
            pg.UUID(as_uuid=True),
            primary_key=True,
            server_default="gen_random_uuid()",
        ),
        default_factory=uuid.uuid4,
    )
    user_id: uuid.UUID = Field(
        sa_column=Column(pg.UUID(as_uuid=True), nullable=False, index=True)
    )
    chapter_id: uuid.UUID = Field(
        sa_column=Column(pg.UUID(as_uuid=True), nullable=False, index=True)
    )
    export_format: str = Field(nullable=False)
    status: str = Field(default="pending")

    # Store list of audio file IDs included in the export
    audio_files: List[str] = Field(
        default=[], sa_column=Column(pg.JSONB, server_default="'[]'::jsonb")
    )

    mix_settings: Dict[str, Any] = Field(
        default={}, sa_column=Column(pg.JSONB, server_default="'{}'::jsonb")
    )
    export_metadata: Dict[str, Any] = Field(
        default={}, sa_column=Column(pg.JSONB, server_default="'{}'::jsonb")
    )

    export_url: Optional[str] = Field(default=None)
    error_message: Optional[str] = Field(default=None)

    created_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        sa_column=Column(
            pg.TIMESTAMP(timezone=True),
            nullable=False,
            server_default="CURRENT_TIMESTAMP",
        ),
    )
    updated_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        sa_column=Column(
            pg.TIMESTAMP(timezone=True),
            nullable=False,
            server_default="CURRENT_TIMESTAMP",
            onupdate=func.current_timestamp(),
        ),
    )


# ---------------------------------------------------------------------------
# KAN-438: Cinematic Dialogue Episode Gate models
# ---------------------------------------------------------------------------

class SequenceUnitType(str, Enum):
    IDENT_TITLE = "ident_title"
    PROLOGUE = "prologue"
    DIALOGUE_ACT = "dialogue_act"
    CLIMAX_RESOLUTION = "climax_resolution"
    SCENE = "scene"  # KAN-458
    CLOSING_BOOKEND = "closing_bookend"
    END_TITLE_CREDITS = "end_title_credits"


class SequenceUnitStatus(str, Enum):
    PENDING = "pending"
    ACTIVE = "active"
    COMPLETED = "completed"
    SKIPPED = "skipped"


class LineTrackingStatus(str, Enum):
    UNASSIGNED = "unassigned"
    CHARACTER_ASSIGNED = "character_assigned"
    VOICE_ASSIGNED = "voice_assigned"
    SCENE_ASSIGNED = "scene_assigned"
    SHOT_ASSIGNED = "shot_assigned"
    AUDIO_GENERATED = "audio_generated"
    LIPSYNC_QUEUED = "lipsync_queued"
    LIPSYNC_COMPLETE = "lipsync_complete"
    PLACED = "placed"


class ShotDiversityReportStatus(str, Enum):
    PENDING = "pending"
    ANALYZING = "analyzing"
    COMPLETED = "completed"
    FAILED = "failed"


class ContinuityReferenceType(str, Enum):
    CHARACTER = "character"
    WORLD = "world"
    PROP = "prop"
    LOCATION = "location"


class SequenceUnit(SQLModel, table=True):
    """Represents a structural unit within an episode's cinematic sequence."""
    __tablename__ = "sequence_units"

    id: uuid.UUID = Field(
        sa_column=Column(
            pg.UUID(as_uuid=True),
            primary_key=True,
            server_default="gen_random_uuid()",
        ),
        default_factory=uuid.uuid4,
    )
    video_generation_id: uuid.UUID = Field(
        sa_column=Column(
            pg.UUID(as_uuid=True),
            ForeignKey("video_generations.id", ondelete="CASCADE"),
            nullable=False,
            index=True,
        ),
    )
    unit_type: SequenceUnitType = Field(
        sa_column=Column(
            pg.ENUM(SequenceUnitType, name="sequence_unit_type", values_callable=lambda e: [m.value for m in e]),
            nullable=False,
        ),
    )
    unit_order: int = Field(nullable=False)
    title: str = Field(nullable=False)
    script_content: Optional[str] = Field(default=None, sa_column=Column(Text))
    duration_seconds: Optional[float] = Field(default=None)
    status: SequenceUnitStatus = Field(
        default=SequenceUnitStatus.PENDING,
        sa_column=Column(
            pg.ENUM(SequenceUnitStatus, name="sequence_unit_status", values_callable=lambda e: [m.value for m in e]),
            nullable=False,
            server_default="'pending'",
        ),
    )
    unit_metadata: Dict[str, Any] = Field(
        default={},
        sa_column=Column("metadata", pg.JSONB, server_default="'{}'::jsonb"),
    )
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        sa_column=Column(
            pg.TIMESTAMP(timezone=True),
            nullable=False,
            server_default="CURRENT_TIMESTAMP",
        ),
    )
    updated_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        sa_column=Column(
            pg.TIMESTAMP(timezone=True),
            nullable=False,
            server_default="CURRENT_TIMESTAMP",
            onupdate=func.current_timestamp(),
        ),
    )


# ── KAN-439: Production Bible, Voice Casting, Dialogue Manifest ──


class ProductionBible(SQLModel, table=True):
    """Versioned project-scoped production bible.

    Stores characters, objects, locations, voices, pronunciation guides,
    style/world rules, and approved reference assets for a project.
    Each update creates a new version; the latest version is the active one.
    """
    __tablename__ = "production_bibles"

    id: uuid.UUID = Field(
        sa_column=Column(
            pg.UUID(as_uuid=True),
            primary_key=True,
            server_default="gen_random_uuid()",
        ),
        default_factory=uuid.uuid4,
    )
    unit_order: int = Field(nullable=False)
    title: str = Field(nullable=False)
    script_content: Optional[str] = Field(default=None, sa_column=Column(Text))
    duration_seconds: Optional[float] = Field(default=None)
    status: SequenceUnitStatus = Field(
        default=SequenceUnitStatus.PENDING,
        sa_column=Column(
            pg.ENUM(SequenceUnitStatus, name="sequence_unit_status", values_callable=lambda e: [m.value for m in e]),
            nullable=False,
            server_default="'pending'",
        ),
    )
    unit_metadata: Dict[str, Any] = Field(
        default={},
        sa_column=Column("metadata", pg.JSONB, server_default="'{}'::jsonb"),
    )
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        sa_column=Column(
            pg.TIMESTAMP(timezone=True),
            nullable=False,
            server_default="CURRENT_TIMESTAMP",
        ),
    )
    updated_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        sa_column=Column(
            pg.TIMESTAMP(timezone=True),
            nullable=False,
            server_default="CURRENT_TIMESTAMP",
            onupdate=func.current_timestamp(),
        ),
    )


class LineTracking(SQLModel, table=True):
    """Tracks individual dialogue lines through the cinematic pipeline."""
    __tablename__ = "line_tracking"

    id: uuid.UUID = Field(
        sa_column=Column(
            pg.UUID(as_uuid=True),
            primary_key=True,
            server_default="gen_random_uuid()",
        ),
        default_factory=uuid.uuid4,
    )
    sequence_unit_id: uuid.UUID = Field(
        sa_column=Column(
            pg.UUID(as_uuid=True),
            ForeignKey("sequence_units.id", ondelete="CASCADE"),
            nullable=False,
        ),
    )
    video_generation_id: uuid.UUID = Field(
        sa_column=Column(
            pg.UUID(as_uuid=True),
            ForeignKey("video_generations.id"),
            nullable=False,
            index=True,
        ),
    )
    line_text: str = Field(default=None, sa_column=Column(Text, nullable=False))
    character_name: Optional[str] = Field(default=None)
    voice_id: Optional[str] = Field(default=None)
    scene_id: Optional[str] = Field(default=None)
    shot_id: Optional[str] = Field(default=None)
    source_audio_url: Optional[str] = Field(default=None)
    lipsync_task_id: Optional[str] = Field(default=None)
    resolved_provider: Optional[str] = Field(default=None)
    resolved_model: Optional[str] = Field(default=None)
    timeline_position_ms: Optional[int] = Field(default=None)
    status: LineTrackingStatus = Field(
        default=LineTrackingStatus.UNASSIGNED,
        sa_column=Column(
            pg.ENUM(LineTrackingStatus, name="line_tracking_status", values_callable=lambda e: [m.value for m in e]),
            nullable=False,
            server_default="'unassigned'",
        ),
    )
    line_metadata: Dict[str, Any] = Field(
        default={},
        sa_column=Column("metadata", pg.JSONB, server_default="'{}'::jsonb"),
    )

    created_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        sa_column=Column(
            pg.TIMESTAMP(timezone=True),
            nullable=False,
            server_default="CURRENT_TIMESTAMP",
        ),
    )
    updated_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        sa_column=Column(
            pg.TIMESTAMP(timezone=True),
            nullable=False,
            server_default="CURRENT_TIMESTAMP",
            onupdate=func.current_timestamp(),
        ),
    )


class ShotDiversityReport(SQLModel, table=True):
    """Stores per-shot diversity analysis to detect duplicate/near-duplicate shots."""
    __tablename__ = "shot_diversity_reports"

    id: uuid.UUID = Field(
        sa_column=Column(
            pg.UUID(as_uuid=True),
            primary_key=True,
            server_default="gen_random_uuid()",
        ),
        default_factory=uuid.uuid4,
    )
    video_generation_id: uuid.UUID = Field(
        sa_column=Column(
            pg.UUID(as_uuid=True),
            ForeignKey("video_generations.id", ondelete="CASCADE"),
            nullable=False,
        ),
    )
    total_shots: int = Field(nullable=False)
    duplicate_count: int = Field(
        default=0,
        sa_column=Column(Integer, nullable=False, server_default="0"),
    )
    near_duplicate_count: int = Field(
        default=0,
        sa_column=Column(Integer, nullable=False, server_default="0"),
    )
    unique_count: int = Field(
        default=0,
        sa_column=Column(Integer, nullable=False, server_default="0"),
    )
    intentional_motif_count: int = Field(
        default=0,
        sa_column=Column(Integer, nullable=False, server_default="0"),
    )
    report_data: Dict[str, Any] = Field(
        default={},
        sa_column=Column(pg.JSONB, nullable=False, server_default="'{}'::jsonb"),
    )
    status: ShotDiversityReportStatus = Field(
        default=ShotDiversityReportStatus.PENDING,
        sa_column=Column(
            pg.ENUM(ShotDiversityReportStatus, name="shot_diversity_report_status", values_callable=lambda e: [m.value for m in e]),
            nullable=False,
            server_default="'pending'",
        ),
    )
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        sa_column=Column(
            pg.TIMESTAMP(timezone=True),
            nullable=False,
            server_default="CURRENT_TIMESTAMP",
        ),
    )
    updated_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        sa_column=Column(
            pg.TIMESTAMP(timezone=True),
            nullable=False,
            server_default="CURRENT_TIMESTAMP",
            onupdate=func.current_timestamp(),
        ),
    )


class VoiceCasting(SQLModel, table=True):
    """Deterministic project-scoped voice casting.

    Maps (project_id, character_name) → (voice_id, provider, model).
    Stable across reruns — NOT based on hash(character_name) alone.
    Uses a composite unique constraint on (project_id, character_name).
    """
    __tablename__ = "voice_castings"

    id: uuid.UUID = Field(
        sa_column=Column(
            pg.UUID(as_uuid=True),
            primary_key=True,
            server_default="gen_random_uuid()",
        ),
        default_factory=uuid.uuid4,
    )
    duplicate_count: int = Field(
        default=0,
        sa_column=Column(Integer, nullable=False, server_default="0"),
    )
    near_duplicate_count: int = Field(
        default=0,
        sa_column=Column(Integer, nullable=False, server_default="0"),
    )
    unique_count: int = Field(
        default=0,
        sa_column=Column(Integer, nullable=False, server_default="0"),
    )
    intentional_motif_count: int = Field(
        default=0,
        sa_column=Column(Integer, nullable=False, server_default="0"),
    )
    report_data: Dict[str, Any] = Field(
        default={},
        sa_column=Column(pg.JSONB, nullable=False, server_default="'{}'::jsonb"),
    )
    status: ShotDiversityReportStatus = Field(
        default=ShotDiversityReportStatus.PENDING,
        sa_column=Column(
            pg.ENUM(ShotDiversityReportStatus, name="shot_diversity_report_status", values_callable=lambda e: [m.value for m in e]),
            nullable=False,
            server_default="'pending'",
        ),
    )
    project_id: uuid.UUID = Field(
        sa_column=Column(
            pg.UUID(as_uuid=True),
            ForeignKey("projects.id", ondelete="CASCADE"),
            nullable=False,
            index=True,
        )
    )
    character_name: str = Field(nullable=False, index=True)
    voice_id: str = Field(nullable=False)
    provider: str = Field(nullable=False)
    model: Optional[str] = Field(default=None)

    # Voice metadata
    voice_metadata: Dict[str, Any] = Field(
        default={}, sa_column=Column(pg.JSONB, server_default="'{}'::jsonb")
    )

    # Lock flag — once cast, can be locked to prevent accidental changes
    is_locked: bool = Field(default=False)

    created_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        sa_column=Column(
            pg.TIMESTAMP(timezone=True),
            nullable=False,
            server_default="CURRENT_TIMESTAMP",
        ),
    )
    updated_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        sa_column=Column(
            pg.TIMESTAMP(timezone=True),
            nullable=False,
            server_default="CURRENT_TIMESTAMP",
            onupdate=func.current_timestamp(),
        ),
    )

    # Composite unique constraint: one voice per character per project
    __table_args__ = (
        UniqueConstraint("project_id", "character_name", name="uq_voice_casting_project_character"),
    )


class ContinuityReference(SQLModel, table=True):
    """Stores character/world/prop/location continuity references for visual consistency."""
    __tablename__ = "continuity_references"

    id: uuid.UUID = Field(
        sa_column=Column(
            pg.UUID(as_uuid=True),
            primary_key=True,
            server_default="gen_random_uuid()",
        ),
        default_factory=uuid.uuid4,
    )
    video_generation_id: uuid.UUID = Field(
        sa_column=Column(
            pg.UUID(as_uuid=True),
            ForeignKey("video_generations.id", ondelete="CASCADE"),
            nullable=False,
        ),
    )
    reference_type: ContinuityReferenceType = Field(
        sa_column=Column(
            pg.ENUM(ContinuityReferenceType, name="continuity_reference_type", values_callable=lambda e: [m.value for m in e]),
            nullable=False,
        ),
    )
    reference_id: str = Field(nullable=False)
    reference_data: Dict[str, Any] = Field(
        default={},
        sa_column=Column(pg.JSONB, nullable=False, server_default="'{}'::jsonb"),
    )
    shot_ids: List[str] = Field(
        default=[],
        sa_column=Column(pg.JSONB, server_default="'[]'::jsonb"),
    )
    adjacent_shot_qa: Dict[str, Any] = Field(
        default={},
        sa_column=Column(pg.JSONB, server_default="'{}'::jsonb"),
    )
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        sa_column=Column(
            pg.TIMESTAMP(timezone=True),
            nullable=False,
            server_default="CURRENT_TIMESTAMP",
        ),
    )
    updated_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        sa_column=Column(
            pg.TIMESTAMP(timezone=True),
            nullable=False,
            server_default="CURRENT_TIMESTAMP",
            onupdate=func.current_timestamp(),
        ),
    )


class DialogueManifest(SQLModel, table=True):
    """Immutable dialogue manifest.

    Links approved text → speaker → audio → subtitle → lip-sync → merge output.
    Once created, records are immutable (enforced at the application layer).
    """
    __tablename__ = "dialogue_manifests"

    id: uuid.UUID = Field(
        sa_column=Column(
            pg.UUID(as_uuid=True),
            primary_key=True,
            server_default="gen_random_uuid()",
        ),
        default_factory=uuid.uuid4,
    )
    video_generation_id: uuid.UUID = Field(
        sa_column=Column(
            pg.UUID(as_uuid=True),
            ForeignKey("video_generations.id", ondelete="CASCADE"),
            nullable=False,
        ),
    )
    reference_id: str = Field(nullable=False)
    reference_data: Dict[str, Any] = Field(
        default={},
        sa_column=Column(pg.JSONB, nullable=False, server_default="'{}'::jsonb"),
    )
    shot_ids: List[str] = Field(
        default=[],
        sa_column=Column(pg.JSONB, server_default="'[]'::jsonb"),
    )
    adjacent_shot_qa: Dict[str, Any] = Field(
        default={},
        sa_column=Column(pg.JSONB, server_default="'{}'::jsonb"),
    )
    project_id: uuid.UUID = Field(
        sa_column=Column(
            pg.UUID(as_uuid=True),
            ForeignKey("projects.id", ondelete="CASCADE"),
            nullable=False,
            index=True,
        )
    )
    video_generation_id: Optional[uuid.UUID] = Field(
        default=None,
        sa_column=Column(
            pg.UUID(as_uuid=True),
            ForeignKey("video_generations.id", ondelete="SET NULL"),
            index=True,
        ),
    )

    # Immutable content hash (SHA-256 of text + speaker + scene_id)
    content_hash: str = Field(nullable=False, unique=True, index=True)

    # Dialogue data
    scene_id: str = Field(nullable=False, index=True)
    speaker: str = Field(nullable=False)
    manifest_text: str = Field(default=None, sa_column=Column(pg.TEXT, nullable=False))
    sequence_order: int = Field(default=0)

    # Linked outputs (immutable once set)
    audio_url: Optional[str] = Field(default=None)
    audio_duration_seconds: Optional[float] = Field(default=None)
    audio_generation_id: Optional[uuid.UUID] = Field(
        default=None, sa_column=Column(pg.UUID(as_uuid=True), index=True)
    )
    subtitle_url: Optional[str] = Field(default=None)
    subtitle_format: Optional[str] = Field(default=None)
    lip_sync_url: Optional[str] = Field(default=None)
    lip_sync_status: Optional[str] = Field(default=None)
    merge_output_url: Optional[str] = Field(default=None)
    merge_status: Optional[str] = Field(default=None)

    # Voice used for this line
    voice_id: Optional[str] = Field(default=None)
    voice_provider: Optional[str] = Field(default=None)

    # Scene state for previous-frame chaining
    scene_state: Dict[str, Any] = Field(
        default={}, sa_column=Column(pg.JSONB, server_default="'{}'::jsonb")
    )
    previous_frame_url: Optional[str] = Field(default=None)
    continuity_frame_url: Optional[str] = Field(default=None)

    # Status tracking
    status: str = Field(default="pending")
    is_finalized: bool = Field(default=False)

    created_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        sa_column=Column(
            pg.TIMESTAMP(timezone=True),
            nullable=False,
            server_default="CURRENT_TIMESTAMP",
        ),
    )
    updated_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        sa_column=Column(
            pg.TIMESTAMP(timezone=True),
            nullable=False,
            server_default="CURRENT_TIMESTAMP",
            onupdate=func.current_timestamp(),
        ),
    )
