"""
API Routes for Cinematic Dialogue Episode Gates

Endpoints for sequence units, line tracking, shot diversity analysis,
continuity references, and episode gate status.
"""

from datetime import datetime
from typing import Optional, List, Dict, Any
import uuid
import json

from fastapi import APIRouter, Depends, HTTPException, Body
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel.ext.asyncio.session import AsyncSession

from app.core.database import get_session
from app.core.auth import get_current_active_user
from app.auth.models import User
from app.core.services.cinematic_episode_gate_service import CinematicEpisodeGateService
from app.core.services.shot_diversity_service import ShotDiversityService
from app.core.services.continuity_service import ContinuityService


router = APIRouter()


# ---------------------------------------------------------------------------
# Pydantic Schemas
# ---------------------------------------------------------------------------


class SequenceUnitCreate(BaseModel):
    unit_type: str = Field(..., description="One of: ident_title, prologue, dialogue_act, climax_resolution, closing_bookend, end_title_credits, scene")
    unit_order: int = Field(..., description="Ordering index for the unit")
    title: str = Field(..., min_length=1, description="Display title (required; DB schema enforces NOT NULL)")
    metadata: Optional[Dict[str, Any]] = None


class SequenceUnitBatchCreate(BaseModel):
    units: List[SequenceUnitCreate]


class SequenceUnitResponse(BaseModel):
    # KAN-456 (option b): declare UUID fields natively + from_attributes=True so ORM
    # objects with `uuid.UUID` columns validate directly. Pydantic v2 + FastAPI
    # JSON-serialize `uuid.UUID` → str in JSON output, so wire format is unchanged
    # (frontend still receives strings). Python instance objects have UUID types.
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    video_generation_id: uuid.UUID
    unit_type: str
    unit_order: int
    title: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None


class SequenceUnitUpdate(BaseModel):
    unit_type: Optional[str] = None
    unit_order: Optional[int] = None
    title: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None


class LineTrackingStageUpdate(BaseModel):
    status: str = Field(..., description="The next line-tracking pipeline status")
    character_name: Optional[str] = None
    voice_id: Optional[str] = None
    scene_id: Optional[str] = None
    shot_id: Optional[str] = None
    source_audio_url: Optional[str] = None
    lipsync_task_id: Optional[str] = None
    resolved_provider: Optional[str] = None
    resolved_model: Optional[str] = None
    timeline_position_ms: Optional[int] = None
    metadata: Optional[Dict[str, Any]] = None


class LineTrackingResponse(BaseModel):
    # KAN-456 (option b): UUID fields + from_attributes=True (see SequenceUnitResponse).
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    sequence_unit_id: uuid.UUID
    video_generation_id: uuid.UUID
    line_text: str
    status: str
    metadata: Optional[Dict[str, Any]] = None
    unit_type: Optional[str] = None
    unit_order: Optional[int] = None


class ShotDiversitySummary(BaseModel):
    total: int = 0
    duplicates: int = 0
    near_duplicates: int = 0
    unique: int = 0
    motifs: int = 0


class ShotDiversityReportResponse(BaseModel):
    report_id: str
    total: int = 0
    duplicates: int = 0
    near_duplicates: int = 0
    unique: int = 0
    motifs: int = 0
    duplicate_details: List[Dict[str, Any]] = Field(default_factory=list)
    near_duplicate_details: List[Dict[str, Any]] = Field(default_factory=list)
    motif_ids: List[str] = Field(default_factory=list)


class MotifMarkRequest(BaseModel):
    shot_id: str
    reason: str


class ContinuityReferenceCreate(BaseModel):
    reference_type: str = Field(..., description="One of: character, world, prop, location")
    reference_id: str
    reference_data: Dict[str, Any]
    shot_ids: List[str] = Field(default_factory=list)


class ContinuityReferenceResponse(BaseModel):
    # KAN-456 (option b): UUID fields + from_attributes=True (see SequenceUnitResponse).
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    video_generation_id: uuid.UUID
    reference_type: str
    reference_id: str
    reference_data: Optional[Dict[str, Any]] = None
    shot_ids: List[str] = Field(default_factory=list)
    adjacent_shot_qa: Optional[Dict[str, Any]] = None


class EpisodeGateStatusResponse(BaseModel):
    video_generation_id: str
    structure_valid: bool
    missing_unit_types: List[str] = Field(default_factory=list)
    out_of_order: List[str] = Field(default_factory=list)
    duplicates: List[str] = Field(default_factory=list)
    line_tracking_count: int = 0
    shot_diversity: Optional[Dict[str, Any]] = None
    continuity_references_count: int = 0
    track_consistency: Optional[Dict[str, Any]] = None


# ---------------------------------------------------------------------------
# Service instances
# ---------------------------------------------------------------------------

_gate_service = CinematicEpisodeGateService()
_diversity_service = ShotDiversityService()
_continuity_service = ContinuityService()


# ---------------------------------------------------------------------------
# Sequence Unit Endpoints
# ---------------------------------------------------------------------------


@router.post(
    "/{vg_id}/sequence-units",
    response_model=List[SequenceUnitResponse],
)
async def create_sequence_units(
    vg_id: str,
    request: SequenceUnitBatchCreate,
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_active_user),
):
    """Create sequence units for a video generation."""
    try:
        units_data = [unit.dict() for unit in request.units]
        created = await _gate_service.create_sequence_units(vg_id, units_data, session)
        return created
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get(
    "/{vg_id}/sequence-units",
    response_model=List[SequenceUnitResponse],
)
async def list_sequence_units(
    vg_id: str,
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_active_user),
):
    """List all sequence units for a video generation."""
    try:
        units = await _gate_service.get_sequence_units(vg_id, session)
        return units
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.patch(
    "/sequence-units/{unit_id}",
    response_model=SequenceUnitResponse,
)
async def update_sequence_unit(
    unit_id: str,
    request: SequenceUnitUpdate,
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_active_user),
):
    """Update a sequence unit."""
    try:
        update_data = {k: v for k, v in request.dict().items() if v is not None}
        updated = await _gate_service.update_sequence_unit(unit_id, update_data, session)
        return updated
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ---------------------------------------------------------------------------
# Line Tracking Endpoints
# ---------------------------------------------------------------------------


@router.get(
    "/{vg_id}/line-tracking",
    response_model=List[LineTrackingResponse],
)
async def get_full_line_tracking(
    vg_id: str,
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_active_user),
):
    """Get all tracked lines for a video generation, grouped by sequence unit."""
    try:
        lines = await _gate_service.get_full_line_tracking(vg_id, session)
        return lines
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.patch("/line-tracking/{line_id}")
async def update_line_tracking_stage(
    line_id: str,
    request: LineTrackingStageUpdate,
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_active_user),
):
    """Update a line tracking record's stage as it progresses through the pipeline."""
    try:
        data = request.model_dump(exclude={"status"}, exclude_none=True)
        result = await _gate_service.track_line_through_pipeline(
            line_id, request.status, data, session
        )
        return result
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ---------------------------------------------------------------------------
# Shot Diversity Endpoints
# ---------------------------------------------------------------------------


@router.post(
    "/{vg_id}/shot-diversity/analyze",
    response_model=ShotDiversityReportResponse,
)
async def analyze_shot_diversity(
    vg_id: str,
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_active_user),
):
    """Trigger shot diversity analysis for a video generation."""
    try:
        result = await _diversity_service.analyze_shots(vg_id, session)
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{vg_id}/shot-diversity")
async def get_shot_diversity_report(
    vg_id: str,
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_active_user),
):
    """Get the latest shot diversity report for a video generation."""
    try:
        result = await _diversity_service.get_report(vg_id, session)
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.patch("/shot-diversity/{report_id}/motif")
async def mark_intentional_motif(
    report_id: str,
    request: MotifMarkRequest,
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_active_user),
):
    """Mark a shot as an intentional motif (overrides duplicate flag)."""
    try:
        result = await _diversity_service.mark_intentional_motif(
            report_id, request.shot_id, request.reason, session
        )
        return result
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ---------------------------------------------------------------------------
# Continuity Endpoints
# ---------------------------------------------------------------------------


@router.post(
    "/{vg_id}/continuity-references",
    response_model=ContinuityReferenceResponse,
)
async def create_continuity_reference(
    vg_id: str,
    request: ContinuityReferenceCreate,
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_active_user),
):
    """Create a continuity reference for a character, world element, prop, or location."""
    try:
        result = await _continuity_service.create_reference(
            vg_id,
            request.reference_type,
            request.reference_id,
            request.reference_data,
            session,
            shot_ids=request.shot_ids,
        )
        return result
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get(
    "/{vg_id}/continuity-references",
    response_model=List[ContinuityReferenceResponse],
)
async def list_continuity_references(
    vg_id: str,
    reference_type: Optional[str] = None,
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_active_user),
):
    """List continuity references, optionally filtered by type."""
    try:
        result = await _continuity_service.get_references(vg_id, reference_type, session)
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/{vg_id}/adjacent-shot-qa")
async def run_adjacent_shot_qa(
    vg_id: str,
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_active_user),
):
    """Run adjacent-shot continuity QA for a video generation."""
    try:
        result = await _continuity_service.run_adjacent_shot_qa(vg_id, session)
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{vg_id}/track-consistency")
async def validate_track_consistency(
    vg_id: str,
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_active_user),
):
    """Validate track consistency (narrator, dialogue, music, ambience) across sequence units."""
    try:
        result = await _continuity_service.validate_track_consistency(vg_id, session)
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ---------------------------------------------------------------------------
# Episode Gate Status (aggregate endpoint)
# ---------------------------------------------------------------------------


@router.get(
    "/{vg_id}/gate-status",
    response_model=EpisodeGateStatusResponse,
)
async def get_episode_gate_status(
    vg_id: str,
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_active_user),
):
    """Get full episode gate status — all gates at once."""
    try:
        # Structure validation
        structure = await _gate_service.validate_episode_structure(vg_id, session)

        # Line tracking count
        lines = await _gate_service.get_full_line_tracking(vg_id, session)

        # Shot diversity report
        diversity = await _diversity_service.get_report(vg_id, session)

        # Continuity references count
        refs = await _continuity_service.get_references(vg_id, None, session)

        # Track consistency
        track_consistency = await _continuity_service.validate_track_consistency(
            vg_id, session
        )

        return EpisodeGateStatusResponse(
            video_generation_id=vg_id,
            structure_valid=structure["valid"],
            missing_unit_types=structure["missing"],
            out_of_order=structure["out_of_order"],
            duplicates=structure["duplicates"],
            line_tracking_count=len(lines),
            shot_diversity=diversity if diversity.get("found", True) else None,
            continuity_references_count=len(refs),
            track_consistency=track_consistency,
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
