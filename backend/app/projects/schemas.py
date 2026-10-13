import uuid
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, field_validator
from datetime import datetime
from app.projects.models import ProjectType, WorkflowMode, ProjectStatus, ArtifactType


class ArtifactSchema(BaseModel):
    id: uuid.UUID
    project_id: uuid.UUID
    artifact_type: ArtifactType
    version: int
    content: Dict[str, Any]
    generated_by: str
    created_at: datetime

    class Config:
        from_attributes = True


class ProjectBase(BaseModel):
    title: str
    input_prompt: Optional[str] = None
    source_material_url: Optional[str] = None
    project_type: ProjectType
    workflow_mode: WorkflowMode
    # KAN-395: Copyright capture + classification
    original_work_title: Optional[str] = None
    original_work_author: Optional[str] = None
    original_work_url: Optional[str] = None
    rights_ownership: Optional[str] = None
    rights_notes: Optional[str] = None
    content_classification: Optional[str] = None
    requires_attribution: bool = False


class ProjectCreate(ProjectBase):
    output_type: Optional[str] = "full_production"
    trailer_config: Dict[str, Any] = {}


class ProjectUpdate(BaseModel):
    title: Optional[str] = None
    status: Optional[ProjectStatus] = None
    current_step: Optional[str] = None
    pipeline_steps: Optional[List[str]] = None
    content_terminology: Optional[str] = None  # Film, Episode, Part, Chapter, or custom
    # KAN-395: Allow updating copyright info post-creation
    original_work_title: Optional[str] = None
    original_work_author: Optional[str] = None
    original_work_url: Optional[str] = None
    rights_ownership: Optional[str] = None
    rights_notes: Optional[str] = None
    content_classification: Optional[str] = None
    requires_attribution: Optional[bool] = None
    # KAN-146: allow updating output_type + trailer_config via PATCH
    output_type: Optional[str] = None
    trailer_config: Optional[Dict[str, Any]] = None

    @field_validator("output_type")
    @classmethod
    def validate_output_type(cls, v: Optional[str]) -> Optional[str]:
        if v is not None and v not in {
            "full_production",
            "trailer",
            "short_clip",
            "ad",
        }:
            raise ValueError(
                "output_type must be one of: full_production, trailer, short_clip, ad"
            )
        return v


class ProjectRead(ProjectBase):
    id: uuid.UUID
    user_id: uuid.UUID
    status: ProjectStatus
    current_step: Optional[str]
    pipeline_steps: List[str]
    content_terminology: Optional[str] = None
    created_at: datetime
    updated_at: datetime
    artifacts: List[ArtifactSchema] = []
    upload_status: Optional[str] = None
    upload_progress: Optional[int] = None
    upload_stage: Optional[str] = None
    upload_error: Optional[str] = None
    upload_total_chapters: Optional[int] = None
    upload_chapters_processed: Optional[int] = None
    consultation_message_count: int = 0
    output_type: Optional[str] = "full_production"
    trailer_config: Dict[str, Any] = {}

    class Config:
        from_attributes = True


class IntentAnalysisRequest(BaseModel):
    prompt: str
    file_name: Optional[str] = None


class IntentAnalysisResult(BaseModel):
    primary_intent: ProjectType
    confidence: float
    reasoning: str
    suggested_mode: WorkflowMode
    detected_pipeline: List[str]
