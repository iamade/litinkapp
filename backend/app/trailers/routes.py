"""
Trailer API Routes — KAN-149 and KAN-150

Endpoints:
- POST /api/v1/trailers/analyze    — Analyze project for scene selection
- GET  /api/v1/trailers/{id}       — Get trailer generation status
- GET  /api/v1/trailers/{id}/scenes — Get selected scenes
- POST /api/v1/trailers/{id}/regenerate — Re-select scenes with new criteria
"""

from typing import List
from uuid import UUID
import logging

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_session
from app.core.auth import get_current_user
from app.trailers.models import TrailerGeneration, TrailerScene, TrailerStatus
from app.trailers.schemas import (
    TrailerAnalyzeRequest,
    TrailerAnalyzeResponse,
    TrailerStatusResponse,
    SceneScore,
    TrailerGenerateRequest,
    TrailerGenerateResponse,
)
from app.trailers.service import TrailerSceneService, TrailerGenerationService
from app.auth.models import User

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/trailers", tags=["trailers"])


@router.post("/analyze", response_model=TrailerAnalyzeResponse)
async def analyze_project_for_trailer(
    request: TrailerAnalyzeRequest,
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    """
    KAN-149: Analyze a project for trailer scene selection.
    
    This endpoint uses AI to identify highlight moments across all chapters
    and selects the best scenes for a trailer.
    
    Request body:
    - project_id: UUID of the project to analyze
    - target_duration_seconds: Desired trailer length (30-300s)
    - tone: Trailer tone (epic, dramatic, action, romantic, mysterious)
    - style: Visual style (cinematic, documentary, animated)
    - max_scenes: Maximum scenes to include (5-30)
    - prefer_action/prefer_dialogue/prefer_emotional: Preference overrides
    
    Returns:
    - trailer_generation_id: ID for tracking progress
    - list of selected scenes with scores
    - estimated duration
    """
    logger.info(f"[KAN-149] Analyze request for project {request.project_id}")
    
    service = TrailerSceneService(session)
    
    try:
        trailer_gen = await service.analyze_project_for_trailer(
            project_id=request.project_id,
            user_id=current_user.id,
            config=request,
        )
        
        # Get selected scenes for response
        selected_scenes = await service.session.execute(
            """
            SELECT * FROM trailer_scenes 
            WHERE trailer_generation_id = :tg_id AND is_selected = true
            ORDER BY scene_number
            """,
            {"tg_id": str(trailer_gen.id)},
        )
        
        scenes_response = []
        for scene in selected_scenes:
            scenes_response.append(SceneScore(
                chapter_id=scene.chapter_id,
                scene_title=scene.scene_title,
                scene_description=scene.scene_description,
                action_score=scene.action_score,
                emotional_score=scene.emotional_score,
                visual_score=scene.visual_score,
                narrative_score=scene.narrative_score,
                overall_score=scene.overall_score,
                is_recommended=scene.is_selected,
                selection_reason=scene.selection_reason,
            ))
        
        return TrailerAnalyzeResponse(
            trailer_generation_id=trailer_gen.id,
            project_id=trailer_gen.project_id,
            status=trailer_gen.status.value,
            total_scenes_analyzed=trailer_gen.total_scenes_analyzed,
            scenes=scenes_response,
            recommended_scene_count=trailer_gen.scenes_selected_count,
            estimated_duration_seconds=float(trailer_gen.actual_duration_seconds or 0),
            created_at=trailer_gen.created_at,
        )
        
    except Exception as e:
        logger.error(f"[KAN-149] Analysis failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Trailer analysis failed: {str(e)}",
        )


@router.get("/{trailer_id}", response_model=TrailerStatusResponse)
async def get_trailer_status(
    trailer_id: UUID,
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    """
    Get the current status of a trailer generation.
    
    Returns:
    - status: Current pipeline stage
    - progress_percent: 0-100 completion estimate
    - current_step: Human-readable current action
    """
    service = TrailerGenerationService(session)
    trailer = await service.get_trailer_status(trailer_id)
    
    if not trailer:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Trailer generation {trailer_id} not found",
        )
    
    # Calculate progress
    status_progress = {
        TrailerStatus.ANALYZING: 10,
        TrailerStatus.SCENES_SELECTED: 25,
        TrailerStatus.SCRIPT_GENERATING: 40,
        TrailerStatus.SCRIPT_READY: 50,
        TrailerStatus.AUDIO_GENERATING: 65,
        TrailerStatus.AUDIO_READY: 75,
        TrailerStatus.ASSEMBLING: 85,
        TrailerStatus.COMPLETED: 100,
        TrailerStatus.FAILED: 0,
    }
    
    progress = status_progress.get(trailer.status, 0)
    
    return TrailerStatusResponse(
        trailer_generation_id=trailer.id,
        project_id=trailer.project_id,
        status=trailer.status.value,
        progress_percent=progress,
        current_step=_get_status_description(trailer.status),
        total_scenes=trailer.scenes_selected_count,
        scenes_completed=0 if trailer.status != TrailerStatus.COMPLETED else trailer.scenes_selected_count,
        error_message=trailer.error_message,
        created_at=trailer.created_at,
        updated_at=trailer.updated_at,
        completed_at=trailer.completed_at,
    )


@router.get("/{trailer_id}/scenes")
async def get_trailer_scenes(
    trailer_id: UUID,
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    """
    Get all scenes for a trailer generation.
    
    Returns:
    - scenes: List of TrailerScene objects with scores
    """
    service = TrailerGenerationService(session)
    scenes = await service.get_selected_scenes(trailer_id)
    
    return {
        "trailer_id": trailer_id,
        "scenes": [
            {
                "id": str(scene.id),
                "chapter_id": str(scene.chapter_id) if scene.chapter_id else None,
                "scene_number": scene.scene_number,
                "scene_title": scene.scene_title,
                "scene_description": scene.scene_description,
                "scores": {
                    "action": scene.action_score,
                    "emotional": scene.emotional_score,
                    "visual": scene.visual_score,
                    "narrative": scene.narrative_score,
                    "overall": scene.overall_score,
                },
                "timing": {
                    "start_seconds": scene.start_time_seconds,
                    "duration_seconds": scene.duration_seconds,
                },
                "selection_reason": scene.selection_reason,
                "is_selected": scene.is_selected,
            }
            for scene in scenes
        ],
    }


@router.post("/{trailer_id}/regenerate")
async def regenerate_scene_selection(
    trailer_id: UUID,
    request: TrailerAnalyzeRequest,
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    """
    Re-run scene selection with different criteria.
    
    Keep same trailer_id but re-analyze with new parameters.
    """
    service = TrailerSceneService(session)
    
    # Get existing trailer generation
    existing = await service.session.execute(
        """
        SELECT * FROM trailer_generations WHERE id = :id
        """,
        {"id": str(trailer_id)},
    )
    trailer_gen = existing.scalar_one_or_none()
    
    if not trailer_gen:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Trailer generation {trailer_id} not found",
        )
    
    # Delete existing scenes
    await service.session.execute(
        """
        DELETE FROM trailer_scenes WHERE trailer_generation_id = :tg_id
        """,
        {"tg_id": str(trailer_id)},
    )
    await service.session.commit()
    
    # Re-analyze with new criteria
    new_trailer = await service.analyze_project_for_trailer(
        project_id=trailer_gen.project_id,
        user_id=current_user.id,
        config=request,
    )
    
    # Update existing record instead of creating new one
    trailer_gen.status = new_trailer.status
    trailer_gen.tone = request.tone
    trailer_gen.style = request.style
    trailer_gen.target_duration_seconds = request.target_duration_seconds
    trailer_gen.actual_duration_seconds = new_trailer.actual_duration_seconds
    trailer_gen.scenes_selected_count = new_trailer.scenes_selected_count
    
    await service.session.commit()
    
    return {
        "trailer_id": str(trailer_id),
        "status": "regenerated",
        "new_scene_count": trailer_gen.scenes_selected_count,
        "estimated_duration": trailer_gen.actual_duration_seconds,
    }


def _get_status_description(status: TrailerStatus) -> str:
    """Human-readable status description."""
    descriptions = {
        TrailerStatus.ANALYZING: "Analyzing project content for highlight scenes",
        TrailerStatus.SCENES_SELECTED: "Scene selection complete, ready for review",
        TrailerStatus.SCRIPT_GENERATING: "Generating trailer script and narration",
        TrailerStatus.SCRIPT_READY: "Script ready for approval",
        TrailerStatus.AUDIO_GENERATING: "Generating voice-over narration",
        TrailerStatus.AUDIO_READY: "Audio ready, preparing final assembly",
        TrailerStatus.ASSEMBLING: "Assembling final trailer video",
        TrailerStatus.COMPLETED: "Trailer generation complete!",
        TrailerStatus.FAILED: "Generation failed - check error message",
    }
    return descriptions.get(status, "Unknown status")