import uuid
from datetime import datetime, timezone
from typing import Optional, List, Dict, Any
from sqlmodel import Field, SQLModel, Column, Relationship
from sqlalchemy.dialects import postgresql as pg
from sqlalchemy import text, func, ForeignKey
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
            server_default=text("gen_random_uuid()"),
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

    can_resume: bool = Field(default=False)
    retry_count: int = Field(default=0)
    error_message: Optional[str] = Field(default=None)

    # JSON fields
    task_meta: Dict[str, Any] = Field(
        default={}, sa_column=Column(pg.JSONB, server_default=text("'{}'::jsonb"))
    )
    script_data: Dict[str, Any] = Field(
        default={}, sa_column=Column(pg.JSONB, server_default=text("'{}'::jsonb"))
    )
    audio_files: Dict[str, Any] = Field(
        default={}, sa_column=Column(pg.JSONB, server_default=text("'{}'::jsonb"))
    )
    image_data: Dict[str, Any] = Field(
        default={}, sa_column=Column(pg.JSONB, server_default=text("'{}'::jsonb"))
    )
    video_data: Dict[str, Any] = Field(
        default={}, sa_column=Column(pg.JSONB, server_default=text("'{}'::jsonb"))
    )
    merge_data: Dict[str, Any] = Field(
        default={}, sa_column=Column(pg.JSONB, server_default=text("'{}'::jsonb"))
    )
    lipsync_data: Dict[str, Any] = Field(
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
            server_default=text("gen_random_uuid()"),
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

    # Relationships
    video_generation: VideoGeneration = Relationship(back_populates="audio_generations")


class ImageGeneration(SQLModel, table=True):
    __tablename__ = "image_generations"

    id: uuid.UUID = Field(
        sa_column=Column(
            pg.UUID(as_uuid=True),
            primary_key=True,
            server_default=text("gen_random_uuid()"),
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
            server_default=text("gen_random_uuid()"),
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
        default=[], sa_column=Column(pg.JSONB, server_default=text("'[]'::jsonb"))
    )
    # Character IDs linking to Plot Overview characters (UUIDs as strings)
    character_ids: List[str] = Field(
        default=[], sa_column=Column(pg.JSONB, server_default=text("'[]'::jsonb"))
    )
    # Editable scene descriptions
    scene_descriptions: List[str] = Field(
        default=[], sa_column=Column(pg.JSONB, server_default=text("'[]'::jsonb"))
    )
    # Scene order for storyboard
    scene_order: List[int] = Field(
        default=[], sa_column=Column(pg.JSONB, server_default=text("'[]'::jsonb"))
    )
    # Storyboard configuration: key_scene_images, deselected_images, image_order
    storyboard_config: Dict[str, Any] = Field(
        default={}, sa_column=Column(pg.JSONB, server_default=text("'{}'::jsonb"))
    )
    character_details: Optional[str] = Field(
        default=None
    )  # The code treats it as string sometimes? "character_details": character_details (string from _generate_character_details)

    evaluation: Dict[str, Any] = Field(
        default={}, sa_column=Column(pg.JSONB, server_default=text("'{}'::jsonb"))
    )

    emotional_map: List[Dict[str, Any]] = Field(
        default=[], sa_column=Column(pg.JSONB, server_default=text("'[]'::jsonb"))
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


class VideoSegment(SQLModel, table=True):
    __tablename__ = "video_segments"

    id: uuid.UUID = Field(
        sa_column=Column(
            pg.UUID(as_uuid=True),
            primary_key=True,
            server_default=text("gen_random_uuid()"),
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
    video_url: Optional[str] = Field(default=None)
    scene_description: Optional[str] = Field(default=None)

    character_count: int = Field(default=0)
    dialogue_count: int = Field(default=0)
    action_count: int = Field(default=0)

    camera_movements: List[str] = Field(
        default=[], sa_column=Column(pg.JSONB, server_default=text("'[]'::jsonb"))
    )
    character_names: List[str] = Field(
        default=[], sa_column=Column(pg.JSONB, server_default=text("'[]'::jsonb"))
    )

    status: str = Field(default="pending")
    prompt_length: Optional[int] = Field(default=None)
    target_duration: Optional[float] = Field(default=None)

    created_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        sa_column=Column(
            pg.TIMESTAMP(timezone=True),
            nullable=False,
            server_default=text("CURRENT_TIMESTAMP"),
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
            server_default=text("gen_random_uuid()"),
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


class AudioExport(SQLModel, table=True):
    __tablename__ = "audio_exports"

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
    chapter_id: uuid.UUID = Field(
        sa_column=Column(pg.UUID(as_uuid=True), nullable=False, index=True)
    )
    export_format: str = Field(nullable=False)
    status: str = Field(default="pending")

    # Store list of audio file IDs included in the export
    audio_files: List[str] = Field(
        default=[], sa_column=Column(pg.JSONB, server_default=text("'[]'::jsonb"))
    )

    mix_settings: Dict[str, Any] = Field(
        default={}, sa_column=Column(pg.JSONB, server_default=text("'{}'::jsonb"))
    )
    export_metadata: Dict[str, Any] = Field(
        default={}, sa_column=Column(pg.JSONB, server_default=text("'{}'::jsonb"))
    )

    export_url: Optional[str] = Field(default=None)
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
