import uuid
from typing import List, Optional, Dict, Any
from pydantic import BaseModel
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


class ProjectCreate(ProjectBase):
    pass


class ProjectUpdate(BaseModel):
    title: Optional[str] = None
    status: Optional[ProjectStatus] = None
    current_step: Optional[str] = None
    pipeline_steps: Optional[List[str]] = None
    content_terminology: Optional[str] = None  # Film, Episode, Part, Chapter, or custom


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
