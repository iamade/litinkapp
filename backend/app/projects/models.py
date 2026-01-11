import uuid
from datetime import datetime, timezone
from enum import Enum
from typing import List, Optional, Dict, Any
from sqlmodel import Field, SQLModel, Column, Relationship
from sqlalchemy.dialects import postgresql as pg
from sqlalchemy import text, func, ForeignKey


class ProjectType(str, Enum):
    ENTERTAINMENT = "entertainment"
    TRAINING = "training"
    ADVERT = "advert"
    MUSIC_VIDEO = "music_video"


class WorkflowMode(str, Enum):
    EXPLORER = "explorer_agentic"
    CREATOR = "creator_interactive"


class ProjectStatus(str, Enum):
    DRAFT = "draft"
    GENERATING = "generating"
    REVIEW = "review"
    COMPLETED = "completed"
    PUBLISHED = "published"


class ArtifactType(str, Enum):
    PLOT = "PLOT"
    SCRIPT = "SCRIPT"
    STORYBOARD = "STORYBOARD"
    IMAGE = "IMAGE"
    AUDIO = "AUDIO"
    VIDEO = "VIDEO"
    CHAPTER = "CHAPTER"
    DOCUMENT_SUMMARY = "DOCUMENT_SUMMARY"


class Project(SQLModel, table=True):
    __tablename__ = "projects"

    id: uuid.UUID = Field(
        sa_column=Column(
            pg.UUID(as_uuid=True),
            primary_key=True,
            server_default=text("gen_random_uuid()"),
        ),
        default_factory=uuid.uuid4,
    )
    user_id: uuid.UUID = Field(
        sa_column=Column(pg.UUID(as_uuid=True), ForeignKey("user.id"), index=True),
    )

    title: str = Field(nullable=False)
    project_type: ProjectType = Field(
        sa_column=Column(pg.ENUM(ProjectType, name="project_type"), nullable=False)
    )
    workflow_mode: WorkflowMode = Field(
        sa_column=Column(pg.ENUM(WorkflowMode, name="workflow_mode"), nullable=False)
    )
    status: ProjectStatus = Field(
        default=ProjectStatus.DRAFT,
        sa_column=Column(pg.ENUM(ProjectStatus, name="project_status"), nullable=False),
    )

    # Input Data
    input_prompt: Optional[str] = Field(default=None, sa_column=Column(pg.TEXT))
    source_material_url: Optional[str] = Field(default=None)  # Link to uploaded file

    # Optional link to Book (when content is uploaded and processed)
    book_id: Optional[uuid.UUID] = Field(
        default=None,
        sa_column=Column(
            pg.UUID(as_uuid=True),
            ForeignKey("books.id", ondelete="SET NULL"),
            index=True,
        ),
    )

    # Progress Tracking
    current_step: Optional[str] = Field(default=None)
    pipeline_steps: List[str] = Field(default=[], sa_column=Column(pg.ARRAY(pg.TEXT)))

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

    # Relationships
    artifacts: List["Artifact"] = Relationship(
        back_populates="project",
        sa_relationship_kwargs={"cascade": "all, delete-orphan"},
    )


class Artifact(SQLModel, table=True):
    __tablename__ = "artifacts"

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
            index=True,
            nullable=False,
        ),
    )

    artifact_type: ArtifactType = Field(
        sa_column=Column(
            pg.ENUM(ArtifactType, name="artifact_type", create_type=False),
            nullable=False,
        )
    )
    version: int = Field(default=1)

    # Content - Flexible JSON storage for Plot structure, Script lines, or Media URLs
    content: Dict[str, Any] = Field(
        default={}, sa_column=Column(pg.JSONB, server_default=text("'{}'::jsonb"))
    )

    # Lineage
    parent_artifact_id: Optional[uuid.UUID] = Field(
        default=None, sa_column=Column(pg.UUID(as_uuid=True), index=True)
    )

    # Metadata
    generated_by: str = Field(default="ai")  # 'ai' or 'user' (for manual edits)
    generation_metadata: Dict[str, Any] = Field(
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

    project: Project = Relationship(back_populates="artifacts")
