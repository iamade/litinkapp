from typing import List, Optional, Dict, Any
from fastapi import APIRouter, Depends, HTTPException, status, Request
from sqlmodel.ext.asyncio.session import AsyncSession
from pydantic import BaseModel

from app.core.database import get_session
from app.core.auth import get_current_user
from app.auth.models import User
from app.projects.schemas import (
    ProjectCreate,
    ProjectRead,
    ProjectUpdate,
    IntentAnalysisRequest,
    IntentAnalysisResult,
)
from app.projects.models import ProjectType
from fastapi import UploadFile, File, Form
from app.projects.services import ProjectService, IntentService
from app.api.services.consultation import ConsultationService

router = APIRouter()


# Consultation Schemas
class ConsultationRequest(BaseModel):
    """Request to analyze scripts for cinematic universe structure."""

    user_prompt: Optional[str] = None  # Additional creative direction


class ConsultationAcceptRequest(BaseModel):
    """Request to accept and apply consultation recommendations."""

    universe_name: str
    content_type_label: str = "Film"  # Film, Episode, or Part
    phases: List[Dict[str, Any]]


class ConsultationResponse(BaseModel):
    """Response from consultation analysis."""

    status: str
    consultation: Optional[Dict[str, Any]] = None
    model_used: Optional[str] = None
    scripts_analyzed: int = 0
    error: Optional[str] = None


@router.post("/upload", response_model=ProjectRead)
async def create_project_upload(
    files: List[UploadFile] = File(...),
    project_type: ProjectType = Form(ProjectType.ENTERTAINMENT),
    input_prompt: Optional[str] = Form(None),
    content_terminology: Optional[str] = Form(None),
    universe_name: Optional[str] = Form(None),
    content_type: Optional[str] = Form(None),
    consultation_data: Optional[str] = Form(None),  # JSON string
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    """
    Create a new project from uploaded files (PDF, DOCX, TXT, etc).
    Supports multiple file uploads simultaneously.
    Extracts chapters and stores them as artifacts.
    """
    import json

    # Parse consultation_data JSON if provided
    parsed_consultation_data = None
    if consultation_data:
        try:
            parsed_consultation_data = json.loads(consultation_data)
        except json.JSONDecodeError:
            pass

    project_service = ProjectService(session)
    return await project_service.create_project_from_upload(
        files,
        current_user.id,
        project_type,
        input_prompt,
        consultation_config=(
            {
                "content_terminology": content_terminology,
                "universe_name": universe_name,
                "content_type": content_type,
                "consultation_data": parsed_consultation_data,
            }
            if any(
                [
                    content_terminology,
                    universe_name,
                    content_type,
                    parsed_consultation_data,
                ]
            )
            else None
        ),
    )


@router.post("/", response_model=ProjectRead, status_code=status.HTTP_201_CREATED)
async def create_project(
    project_in: ProjectCreate,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    """
    Create a new project.
    """
    project_service = ProjectService(session)
    return await project_service.create_project(project_in, current_user.id)


@router.get("/", response_model=List[ProjectRead])
async def get_projects(
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    """
    Get all projects for the current user.
    """
    project_service = ProjectService(session)
    return await project_service.get_user_projects(current_user.id)


@router.get("/{project_id}", response_model=ProjectRead)
async def get_project(
    project_id: str,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    """
    Get a specific project by ID.
    """
    project_service = ProjectService(session)
    project = await project_service.get_project(project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    if project.user_id != current_user.id:
        raise HTTPException(
            status_code=403, detail="Not authorized to view this project"
        )
    return project


@router.patch("/{project_id}", response_model=ProjectRead)
async def update_project(
    project_id: str,
    project_in: ProjectUpdate,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    """
    Update a project.
    """
    project_service = ProjectService(session)
    project = await project_service.get_project(project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    if project.user_id != current_user.id:
        raise HTTPException(
            status_code=403, detail="Not authorized to update this project"
        )

    return await project_service.update_project(project_id, project_in)


@router.delete("/{project_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_project(
    project_id: str,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    """
    Delete a project.
    """
    project_service = ProjectService(session)
    project = await project_service.get_project(project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    if project.user_id != current_user.id:
        raise HTTPException(
            status_code=403, detail="Not authorized to delete this project"
        )

    await project_service.delete_project(project_id)
    return None


@router.post("/analyze-intent", response_model=IntentAnalysisResult)
async def analyze_intent(
    request: IntentAnalysisRequest,
    current_user: User = Depends(get_current_user),
):
    """
    Analyze user intent based on prompt and/or file.
    """
    # Simple logic to determine if user is explorer based on roles or profile
    # For now assume Explorer if they have the role or just pass it in.
    # We'll default to True for now as placeholder or check user.roles
    user_is_explorer = False  # Default to Creator mode logic unless specified
    # user_is_explorer = "explorer" in current_user.roles

    return await IntentService.analyze_intent(request, user_is_explorer)


# ============================================================================
# CONSULTATION ENDPOINTS - Cinematic Universe Mode
# ============================================================================


@router.post("/{project_id}/consultation", response_model=ConsultationResponse)
async def analyze_for_cinematic_universe(
    project_id: str,
    request: ConsultationRequest,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    """
    Analyze uploaded scripts and provide cinematic universe recommendations.

    This endpoint triggers AI analysis of all scripts in the project and returns:
    - Suggested universe names
    - Recommended phase structure
    - Ordering recommendations
    - AI commentary on the project potential
    """
    # Verify project ownership
    project_service = ProjectService(session)
    project = await project_service.get_project(project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    if project.user_id != current_user.id:
        raise HTTPException(
            status_code=403, detail="Not authorized to access this project"
        )

    # Get user tier for model selection
    user_tier = getattr(current_user, "subscription_tier", "free") or "free"

    # Use the original prompt if no new one provided
    user_prompt = (
        request.user_prompt
        or project.input_prompt
        or "Analyze these scripts for a cinematic universe."
    )

    consultation_service = ConsultationService(session)
    result = await consultation_service.analyze_scripts_for_cinematic_universe(
        project_id=project.id,
        user_prompt=user_prompt,
        user_tier=user_tier,
    )

    return ConsultationResponse(**result)


@router.put("/{project_id}/consultation/accept")
async def accept_consultation(
    project_id: str,
    request: ConsultationAcceptRequest,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    """
    Accept the consultation recommendations and apply them to the project.

    This updates:
    - Project title to the selected universe name
    - Artifact metadata with script ordering and labels
    - Phase structure for the workflow
    """
    # Verify project ownership
    project_service = ProjectService(session)
    project = await project_service.get_project(project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    if project.user_id != current_user.id:
        raise HTTPException(
            status_code=403, detail="Not authorized to access this project"
        )

    consultation_service = ConsultationService(session)
    result = await consultation_service.accept_consultation(
        project_id=project.id,
        accepted_structure={
            "universe_name": request.universe_name,
            "content_type_label": request.content_type_label,
            "phases": request.phases,
        },
    )

    return result


@router.get("/{project_id}/consultation/saved")
async def get_saved_consultation(
    project_id: str,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    """
    Get saved consultation results if they exist.

    Returns the previously saved consultation data instead of re-running analysis.
    This is used by the Cinematic Universe Setup tab to display existing agreements.
    """
    import uuid
    from sqlmodel import select
    from app.projects.models import Artifact, ArtifactType

    # Verify project ownership
    project_service = ProjectService(session)
    project = await project_service.get_project(project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    if project.user_id != current_user.id:
        raise HTTPException(
            status_code=403, detail="Not authorized to access this project"
        )

    # Query for consultation artifact
    project_uuid = uuid.UUID(project_id) if isinstance(project_id, str) else project_id
    stmt = select(Artifact).where(
        Artifact.project_id == project_uuid,
        Artifact.artifact_type == ArtifactType.DOCUMENT_SUMMARY,
    )
    result = await session.exec(stmt)
    artifacts = result.all()

    # Find the consultation artifact
    consultation_artifact = None
    for artifact in artifacts:
        if (
            artifact.content
            and artifact.content.get("type") == "cinematic_universe_consultation"
        ):
            consultation_artifact = artifact
            break

    if consultation_artifact:
        return {
            "status": "success",
            "consultation": consultation_artifact.content.get("consultation"),
            "conversation": consultation_artifact.content.get("conversation", []),
            "agreements": consultation_artifact.content.get("agreements", {}),
        }

    return {
        "status": "success",
        "consultation": None,
        "message": "No saved consultation found",
    }


# ============================================================================
# ARTIFACT UPDATE ENDPOINTS - Script Editing & Re-upload
# ============================================================================


class ConsultationChatRequest(BaseModel):
    """Request to continue consultation conversation."""

    message: str
    conversation_history: List[Dict[str, Any]] = []
    file_summary: Optional[str] = None


@router.post("/{project_id}/consultation/chat")
async def consultation_chat(
    project_id: str,
    request: ConsultationChatRequest,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    """
    Continue or refine the consultation conversation for a project.
    Used in the Cinematic Universe Setup tab to refine agreements with AI.
    """
    # Verify project ownership
    project_service = ProjectService(session)
    project = await project_service.get_project(project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    if project.user_id != current_user.id:
        raise HTTPException(
            status_code=403, detail="Not authorized to access this project"
        )

    user_tier = getattr(current_user, "subscription_tier", "free") or "free"

    # Build file summary from project artifacts if not provided
    file_summary = request.file_summary
    if not file_summary:
        file_summary = f"Project: {project.title or 'Untitled'}"
        if project.input_prompt:
            file_summary += f"\nUser prompt: {project.input_prompt}"

    consultation_service = ConsultationService(session)
    result = await consultation_service.continue_conversation(
        message=request.message,
        context={
            "messages": request.conversation_history,
            "file_summary": file_summary,
        },
        user_tier=user_tier,
    )

    return result


class ArtifactUpdateRequest(BaseModel):
    """Request model for updating artifact content"""

    content: Optional[str] = None  # New text content for the artifact
    title: Optional[str] = None  # Updated title
    content_type_label: Optional[str] = None  # Updated label (Film, Episode, Part)
    script_order: Optional[int] = None  # Updated order in the sequence


class ArtifactUpdateResponse(BaseModel):
    """Response model for artifact update"""

    id: str
    title: Optional[str]
    content_type_label: Optional[str]
    script_order: Optional[int]
    updated: bool
    message: str


@router.put(
    "/{project_id}/artifacts/{artifact_id}", response_model=ArtifactUpdateResponse
)
async def update_artifact(
    project_id: str,
    artifact_id: str,
    request: ArtifactUpdateRequest,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    """
    Update an artifact's content or metadata.

    This endpoint allows:
    - Editing script/chapter text content
    - Updating title and labels
    - Reordering scripts in the sequence
    """
    from app.projects.models import Artifact
    from sqlmodel import select

    # Verify project ownership
    project_service = ProjectService(session)
    project = await project_service.get_project(project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    if project.user_id != current_user.id:
        raise HTTPException(
            status_code=403, detail="Not authorized to access this project"
        )

    # Get the artifact
    stmt = select(Artifact).where(
        Artifact.id == artifact_id, Artifact.project_id == project_id
    )
    result = await session.exec(stmt)
    artifact = result.first()

    if not artifact:
        raise HTTPException(status_code=404, detail="Artifact not found")

    updated = False

    # Update content if provided
    if request.content is not None:
        if artifact.content is None:
            artifact.content = {}
        artifact.content["content"] = request.content
        updated = True

    # Update title if provided
    if request.title is not None:
        if artifact.content is None:
            artifact.content = {}
        artifact.content["title"] = request.title
        updated = True

    # Update content_type_label if provided
    if request.content_type_label is not None:
        artifact.content_type_label = request.content_type_label
        updated = True

    # Update script_order if provided
    if request.script_order is not None:
        artifact.script_order = request.script_order
        updated = True

    if updated:
        session.add(artifact)
        await session.commit()
        await session.refresh(artifact)

    return ArtifactUpdateResponse(
        id=str(artifact.id),
        title=artifact.content.get("title") if artifact.content else None,
        content_type_label=artifact.content_type_label,
        script_order=artifact.script_order,
        updated=updated,
        message="Artifact updated successfully" if updated else "No changes made",
    )
