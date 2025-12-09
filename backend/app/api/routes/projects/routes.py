from typing import List
from fastapi import APIRouter, Depends, HTTPException, status
from sqlmodel.ext.asyncio.session import AsyncSession

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
from app.projects.services import ProjectService, IntentService

router = APIRouter()


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
