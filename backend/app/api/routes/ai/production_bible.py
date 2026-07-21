"""
KAN-439: Production Bible API Routes

Endpoints:
- POST/GET/PUT /ai/production-bible — Production bible CRUD with versioning
- POST/GET /ai/voice-casting — Deterministic voice casting
- POST/GET /ai/dialogue-manifest — Immutable dialogue manifest
"""

from __future__ import annotations

import uuid
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from sqlmodel.ext.asyncio.session import AsyncSession

from app.core.auth import get_current_active_user
from app.core.database import get_session
from app.core.services.production_bible_service import (
    production_bible_service,
    voice_casting_service,
    dialogue_manifest_service,
)
from app.auth.models import User

router = APIRouter(prefix="/production-bible", tags=["production-bible"])


# ── Request/Response Schemas ──


class ProductionBibleCreate(BaseModel):
    project_id: uuid.UUID
    characters: Optional[List[Dict[str, Any]]] = Field(default_factory=list)
    objects: Optional[List[Dict[str, Any]]] = Field(default_factory=list)
    locations: Optional[List[Dict[str, Any]]] = Field(default_factory=list)
    voices: Optional[Dict[str, Any]] = Field(default_factory=dict)
    pronunciation: Optional[Dict[str, Any]] = Field(default_factory=dict)
    style_rules: Optional[Dict[str, Any]] = Field(default_factory=dict)
    world_rules: Optional[Dict[str, Any]] = Field(default_factory=dict)
    approved_reference_assets: Optional[List[Dict[str, Any]]] = Field(default_factory=list)
    change_log: Optional[str] = None


class ProductionBibleUpdate(BaseModel):
    characters: Optional[List[Dict[str, Any]]] = None
    objects: Optional[List[Dict[str, Any]]] = None
    locations: Optional[List[Dict[str, Any]]] = None
    voices: Optional[Dict[str, Any]] = None
    pronunciation: Optional[Dict[str, Any]] = None
    style_rules: Optional[Dict[str, Any]] = None
    world_rules: Optional[Dict[str, Any]] = None
    approved_reference_assets: Optional[List[Dict[str, Any]]] = None
    change_log: Optional[str] = None


class VoiceCastingRequest(BaseModel):
    project_id: uuid.UUID
    character_name: str
    provider: str = "elevenlabs"
    voice_id: Optional[str] = None
    model: Optional[str] = None
    voice_metadata: Optional[Dict[str, Any]] = Field(default_factory=dict)
    lock: bool = False


class VoiceCastingUpdate(BaseModel):
    voice_id: Optional[str] = None
    provider: Optional[str] = None
    model: Optional[str] = None
    voice_metadata: Optional[Dict[str, Any]] = None
    lock: Optional[bool] = None


class BulkVoiceCastingRequest(BaseModel):
    project_id: uuid.UUID
    character_names: List[str]
    provider: str = "elevenlabs"
    lock: bool = False


class DialogueManifestCreate(BaseModel):
    project_id: uuid.UUID
    scene_id: str
    speaker: str
    text: str
    sequence_order: int = 0
    video_generation_id: Optional[uuid.UUID] = None
    voice_id: Optional[str] = None
    voice_provider: Optional[str] = None
    scene_state: Optional[Dict[str, Any]] = Field(default_factory=dict)
    previous_frame_url: Optional[str] = None
    continuity_frame_url: Optional[str] = None


class LinkAudioRequest(BaseModel):
    manifest_id: uuid.UUID
    audio_url: str
    audio_duration_seconds: Optional[float] = None
    audio_generation_id: Optional[uuid.UUID] = None


class LinkSubtitleRequest(BaseModel):
    manifest_id: uuid.UUID
    subtitle_url: str
    subtitle_format: str = "srt"


class LinkLipSyncRequest(BaseModel):
    manifest_id: uuid.UUID
    lip_sync_url: str
    lip_sync_status: str = "completed"


class LinkMergeOutputRequest(BaseModel):
    manifest_id: uuid.UUID
    merge_output_url: str
    merge_status: str = "completed"


class PreserveSceneStateRequest(BaseModel):
    project_id: uuid.UUID
    scene_id: str
    scene_state: Dict[str, Any]
    continuity_frame_url: Optional[str] = None


# ── Production Bible Routes ──


@router.post("/bible")
async def create_production_bible(
    body: ProductionBibleCreate,
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_active_user),
):
    """Create a new production bible (version 1) for a project."""
    try:
        bible = await production_bible_service.create_bible(
            session=session,
            project_id=body.project_id,
            characters=body.characters,
            objects=body.objects,
            locations=body.locations,
            voices=body.voices,
            pronunciation=body.pronunciation,
            style_rules=body.style_rules,
            world_rules=body.world_rules,
            approved_reference_assets=body.approved_reference_assets,
            change_log=body.change_log,
            created_by=current_user.id,
        )
        return {"status": "ok", "bible": _bible_to_dict(bible)}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/bible/{project_id}")
async def get_production_bible(
    project_id: uuid.UUID,
    version: Optional[int] = Query(None, description="Specific version to fetch"),
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_active_user),
):
    """Get the active (or specific version) production bible for a project."""
    try:
        if version is not None:
            bible = await production_bible_service.get_bible_by_version(
                session, project_id, version
            )
        else:
            bible = await production_bible_service.get_active_bible(session, project_id)

        if bible is None:
            raise HTTPException(status_code=404, detail="Production bible not found")
        return {"status": "ok", "bible": _bible_to_dict(bible)}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.put("/bible/{project_id}")
async def update_production_bible(
    project_id: uuid.UUID,
    body: ProductionBibleUpdate,
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_active_user),
):
    """Update the production bible (creates a new version)."""
    try:
        bible = await production_bible_service.update_bible(
            session=session,
            project_id=project_id,
            characters=body.characters,
            objects=body.objects,
            locations=body.locations,
            voices=body.voices,
            pronunciation=body.pronunciation,
            style_rules=body.style_rules,
            world_rules=body.world_rules,
            approved_reference_assets=body.approved_reference_assets,
            change_log=body.change_log,
            created_by=current_user.id,
        )
        return {"status": "ok", "bible": _bible_to_dict(bible)}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/bible/{project_id}/versions")
async def list_bible_versions(
    project_id: uuid.UUID,
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_active_user),
):
    """List all versions of the production bible for a project."""
    try:
        versions = await production_bible_service.list_bible_versions(session, project_id)
        return {
            "status": "ok",
            "versions": [_bible_to_dict(v) for v in versions],
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ── Voice Casting Routes ──


@router.post("/voice-casting")
async def cast_voice(
    body: VoiceCastingRequest,
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_active_user),
):
    """Cast a voice for a character in a project (deterministic, stable across reruns)."""
    try:
        casting = await voice_casting_service.cast_voice(
            session=session,
            project_id=body.project_id,
            character_name=body.character_name,
            provider=body.provider,
            voice_id=body.voice_id,
            model=body.model,
            voice_metadata=body.voice_metadata,
            lock=body.lock,
        )
        return {"status": "ok", "casting": _casting_to_dict(casting)}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/voice-casting/bulk")
async def bulk_cast_voices(
    body: BulkVoiceCastingRequest,
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_active_user),
):
    """Cast voices for multiple characters at once."""
    try:
        castings = await voice_casting_service.bulk_cast(
            session=session,
            project_id=body.project_id,
            character_names=body.character_names,
            provider=body.provider,
            lock=body.lock,
        )
        return {
            "status": "ok",
            "castings": [_casting_to_dict(c) for c in castings],
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/voice-casting/{project_id}")
async def list_voice_castings(
    project_id: uuid.UUID,
    character_name: Optional[str] = Query(None),
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_active_user),
):
    """List voice castings for a project, optionally filtered by character."""
    try:
        if character_name:
            casting = await voice_casting_service.get_casting(
                session, project_id, character_name
            )
            if casting is None:
                raise HTTPException(status_code=404, detail="Voice casting not found")
            return {"status": "ok", "casting": _casting_to_dict(casting)}
        castings = await voice_casting_service.list_castings(session, project_id)
        return {
            "status": "ok",
            "castings": [_casting_to_dict(c) for c in castings],
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.put("/voice-casting/{project_id}/{character_name}")
async def update_voice_casting(
    project_id: uuid.UUID,
    character_name: str,
    body: VoiceCastingUpdate,
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_active_user),
):
    """Update a voice casting (refuses if locked)."""
    try:
        casting = await voice_casting_service.update_casting(
            session=session,
            project_id=project_id,
            character_name=character_name,
            voice_id=body.voice_id,
            provider=body.provider,
            model=body.model,
            voice_metadata=body.voice_metadata,
            lock=body.lock,
        )
        if casting is None:
            raise HTTPException(status_code=404, detail="Voice casting not found")
        return {"status": "ok", "casting": _casting_to_dict(casting)}
    except ValueError as e:
        raise HTTPException(status_code=409, detail=str(e))
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ── Dialogue Manifest Routes ──


@router.post("/dialogue-manifest")
async def create_dialogue_manifest(
    body: DialogueManifestCreate,
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_active_user),
):
    """Create a new dialogue manifest entry (immutable once finalized)."""
    try:
        manifest = await dialogue_manifest_service.create_manifest(
            session=session,
            project_id=body.project_id,
            scene_id=body.scene_id,
            speaker=body.speaker,
            text=body.text,
            sequence_order=body.sequence_order,
            video_generation_id=body.video_generation_id,
            voice_id=body.voice_id,
            voice_provider=body.voice_provider,
            scene_state=body.scene_state,
            previous_frame_url=body.previous_frame_url,
            continuity_frame_url=body.continuity_frame_url,
        )
        return {"status": "ok", "manifest": _manifest_to_dict(manifest)}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/dialogue-manifest/{project_id}")
async def list_dialogue_manifests(
    project_id: uuid.UUID,
    scene_id: Optional[str] = Query(None),
    video_generation_id: Optional[uuid.UUID] = Query(None),
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_active_user),
):
    """List dialogue manifests for a project."""
    try:
        manifests = await dialogue_manifest_service.list_manifests(
            session=session,
            project_id=project_id,
            scene_id=scene_id,
            video_generation_id=video_generation_id,
        )
        return {
            "status": "ok",
            "manifests": [_manifest_to_dict(m) for m in manifests],
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/dialogue-manifest/{project_id}/{manifest_id}")
async def get_dialogue_manifest(
    project_id: uuid.UUID,
    manifest_id: uuid.UUID,
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_active_user),
):
    """Get a specific dialogue manifest by ID."""
    try:
        manifest = await dialogue_manifest_service.get_manifest(session, manifest_id)
        if manifest is None:
            raise HTTPException(status_code=404, detail="Dialogue manifest not found")
        return {"status": "ok", "manifest": _manifest_to_dict(manifest)}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/dialogue-manifest/link-audio")
async def link_audio_to_manifest(
    body: LinkAudioRequest,
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_active_user),
):
    """Link generated audio to a dialogue manifest entry."""
    try:
        manifest = await dialogue_manifest_service.link_audio(
            session=session,
            manifest_id=body.manifest_id,
            audio_url=body.audio_url,
            audio_duration_seconds=body.audio_duration_seconds,
            audio_generation_id=body.audio_generation_id,
        )
        if manifest is None:
            raise HTTPException(status_code=404, detail="Dialogue manifest not found")
        return {"status": "ok", "manifest": _manifest_to_dict(manifest)}
    except ValueError as e:
        raise HTTPException(status_code=409, detail=str(e))
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/dialogue-manifest/link-subtitle")
async def link_subtitle_to_manifest(
    body: LinkSubtitleRequest,
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_active_user),
):
    """Link generated subtitles to a dialogue manifest entry."""
    try:
        manifest = await dialogue_manifest_service.link_subtitle(
            session=session,
            manifest_id=body.manifest_id,
            subtitle_url=body.subtitle_url,
            subtitle_format=body.subtitle_format,
        )
        if manifest is None:
            raise HTTPException(status_code=404, detail="Dialogue manifest not found")
        return {"status": "ok", "manifest": _manifest_to_dict(manifest)}
    except ValueError as e:
        raise HTTPException(status_code=409, detail=str(e))
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/dialogue-manifest/link-lipsync")
async def link_lipsync_to_manifest(
    body: LinkLipSyncRequest,
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_active_user),
):
    """Link lip-sync output to a dialogue manifest entry."""
    try:
        manifest = await dialogue_manifest_service.link_lip_sync(
            session=session,
            manifest_id=body.manifest_id,
            lip_sync_url=body.lip_sync_url,
            lip_sync_status=body.lip_sync_status,
        )
        if manifest is None:
            raise HTTPException(status_code=404, detail="Dialogue manifest not found")
        return {"status": "ok", "manifest": _manifest_to_dict(manifest)}
    except ValueError as e:
        raise HTTPException(status_code=409, detail=str(e))
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/dialogue-manifest/link-merge")
async def link_merge_to_manifest(
    body: LinkMergeOutputRequest,
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_active_user),
):
    """Link final merge output to a dialogue manifest entry."""
    try:
        manifest = await dialogue_manifest_service.link_merge_output(
            session=session,
            manifest_id=body.manifest_id,
            merge_output_url=body.merge_output_url,
            merge_status=body.merge_status,
        )
        if manifest is None:
            raise HTTPException(status_code=404, detail="Dialogue manifest not found")
        return {"status": "ok", "manifest": _manifest_to_dict(manifest)}
    except ValueError as e:
        raise HTTPException(status_code=409, detail=str(e))
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/dialogue-manifest/finalize/{manifest_id}")
async def finalize_dialogue_manifest(
    manifest_id: uuid.UUID,
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_active_user),
):
    """Finalize a dialogue manifest — makes it immutable."""
    try:
        manifest = await dialogue_manifest_service.finalize_manifest(session, manifest_id)
        if manifest is None:
            raise HTTPException(status_code=404, detail="Dialogue manifest not found")
        return {"status": "ok", "manifest": _manifest_to_dict(manifest)}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/dialogue-manifest/preserve-scene-state")
async def preserve_scene_state(
    body: PreserveSceneStateRequest,
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_active_user),
):
    """Preserve scene state for previous-frame chaining across scenes/reruns."""
    try:
        manifest = await dialogue_manifest_service.preserve_scene_state(
            session=session,
            project_id=body.project_id,
            scene_id=body.scene_id,
            scene_state=body.scene_state,
            continuity_frame_url=body.continuity_frame_url,
        )
        if manifest is None:
            raise HTTPException(
                status_code=404,
                detail="No dialogue manifest found for this scene",
            )
        return {"status": "ok", "manifest": _manifest_to_dict(manifest)}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/dialogue-manifest/previous-frame/{project_id}/{scene_id}")
async def get_previous_frame(
    project_id: uuid.UUID,
    scene_id: str,
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_active_user),
):
    """Get the previous frame state for a scene (for chaining)."""
    try:
        frame = await dialogue_manifest_service.get_previous_frame(
            session=session,
            project_id=project_id,
            scene_id=scene_id,
        )
        if frame is None:
            raise HTTPException(
                status_code=404,
                detail="No previous frame found for this scene",
            )
        return {"status": "ok", "previous_frame": frame}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ── Serialization Helpers ──


def _bible_to_dict(bible) -> Dict[str, Any]:
    return {
        "id": str(bible.id),
        "project_id": str(bible.project_id),
        "version": bible.version,
        "is_active": bible.is_active,
        "characters": bible.characters,
        "objects": bible.objects,
        "locations": bible.locations,
        "voices": bible.voices,
        "pronunciation": bible.pronunciation,
        "style_rules": bible.style_rules,
        "world_rules": bible.world_rules,
        "approved_reference_assets": bible.approved_reference_assets,
        "change_log": bible.change_log,
        "created_by": str(bible.created_by) if bible.created_by else None,
        "created_at": bible.created_at.isoformat() if bible.created_at else None,
        "updated_at": bible.updated_at.isoformat() if bible.updated_at else None,
    }


def _casting_to_dict(casting) -> Dict[str, Any]:
    return {
        "id": str(casting.id),
        "project_id": str(casting.project_id),
        "character_name": casting.character_name,
        "voice_id": casting.voice_id,
        "provider": casting.provider,
        "model": casting.model,
        "voice_metadata": casting.voice_metadata,
        "is_locked": casting.is_locked,
        "created_at": casting.created_at.isoformat() if casting.created_at else None,
        "updated_at": casting.updated_at.isoformat() if casting.updated_at else None,
    }


def _manifest_to_dict(manifest) -> Dict[str, Any]:
    return {
        "id": str(manifest.id),
        "project_id": str(manifest.project_id),
        "video_generation_id": str(manifest.video_generation_id)
        if manifest.video_generation_id
        else None,
        "content_hash": manifest.content_hash,
        "scene_id": manifest.scene_id,
        "speaker": manifest.speaker,
        "text": manifest.text,
        "sequence_order": manifest.sequence_order,
        "audio_url": manifest.audio_url,
        "audio_duration_seconds": manifest.audio_duration_seconds,
        "audio_generation_id": str(manifest.audio_generation_id)
        if manifest.audio_generation_id
        else None,
        "subtitle_url": manifest.subtitle_url,
        "subtitle_format": manifest.subtitle_format,
        "lip_sync_url": manifest.lip_sync_url,
        "lip_sync_status": manifest.lip_sync_status,
        "merge_output_url": manifest.merge_output_url,
        "merge_status": manifest.merge_status,
        "voice_id": manifest.voice_id,
        "voice_provider": manifest.voice_provider,
        "scene_state": manifest.scene_state,
        "previous_frame_url": manifest.previous_frame_url,
        "continuity_frame_url": manifest.continuity_frame_url,
        "status": manifest.status,
        "is_finalized": manifest.is_finalized,
        "created_at": manifest.created_at.isoformat() if manifest.created_at else None,
        "updated_at": manifest.updated_at.isoformat() if manifest.updated_at else None,
    }
