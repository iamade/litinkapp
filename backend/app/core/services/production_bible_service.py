"""
KAN-439: Production Bible Service

Provides:
- CRUD for ProductionBible with versioning
- Deterministic voice casting (project-scoped, stable across reruns)
- Immutable dialogue manifest creation and retrieval
- Scene-state preservation for previous-frame chaining
"""

from __future__ import annotations

import hashlib
import json
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import select, func

from app.videos.models import ProductionBible, VoiceCasting, DialogueManifest


# ── Production Bible CRUD ──


class ProductionBibleService:
    """Service for managing versioned production bibles."""

    async def create_bible(
        self,
        session: AsyncSession,
        project_id: uuid.UUID,
        characters: Optional[List[Dict[str, Any]]] = None,
        objects: Optional[List[Dict[str, Any]]] = None,
        locations: Optional[List[Dict[str, Any]]] = None,
        voices: Optional[Dict[str, Any]] = None,
        pronunciation: Optional[Dict[str, Any]] = None,
        style_rules: Optional[Dict[str, Any]] = None,
        world_rules: Optional[Dict[str, Any]] = None,
        approved_reference_assets: Optional[List[Dict[str, Any]]] = None,
        change_log: Optional[str] = None,
        created_by: Optional[uuid.UUID] = None,
    ) -> ProductionBible:
        """Create a new production bible (version 1) for a project."""
        bible = ProductionBible(
            project_id=project_id,
            version=1,
            is_active=True,
            characters=characters or [],
            objects=objects or [],
            locations=locations or [],
            voices=voices or {},
            pronunciation=pronunciation or {},
            style_rules=style_rules or {},
            world_rules=world_rules or {},
            approved_reference_assets=approved_reference_assets or [],
            change_log=change_log,
            created_by=created_by,
        )
        session.add(bible)
        await session.commit()
        await session.refresh(bible)
        return bible

    async def get_active_bible(
        self, session: AsyncSession, project_id: uuid.UUID
    ) -> Optional[ProductionBible]:
        """Get the currently active production bible for a project."""
        result = await session.exec(
            select(ProductionBible)
            .where(ProductionBible.project_id == project_id)
            .where(ProductionBible.is_active == True)
            .order_by(ProductionBible.version.desc())
            .limit(1)
        )
        return result.first()

    async def get_bible_by_version(
        self, session: AsyncSession, project_id: uuid.UUID, version: int
    ) -> Optional[ProductionBible]:
        """Get a specific version of the production bible."""
        result = await session.exec(
            select(ProductionBible)
            .where(ProductionBible.project_id == project_id)
            .where(ProductionBible.version == version)
        )
        return result.first()

    async def list_bible_versions(
        self, session: AsyncSession, project_id: uuid.UUID
    ) -> List[ProductionBible]:
        """List all versions of the production bible for a project."""
        result = await session.exec(
            select(ProductionBible)
            .where(ProductionBible.project_id == project_id)
            .order_by(ProductionBible.version.desc())
        )
        return list(result.all())

    async def update_bible(
        self,
        session: AsyncSession,
        project_id: uuid.UUID,
        characters: Optional[List[Dict[str, Any]]] = None,
        objects: Optional[List[Dict[str, Any]]] = None,
        locations: Optional[List[Dict[str, Any]]] = None,
        voices: Optional[Dict[str, Any]] = None,
        pronunciation: Optional[Dict[str, Any]] = None,
        style_rules: Optional[Dict[str, Any]] = None,
        world_rules: Optional[Dict[str, Any]] = None,
        approved_reference_assets: Optional[List[Dict[str, Any]]] = None,
        change_log: Optional[str] = None,
        created_by: Optional[uuid.UUID] = None,
    ) -> ProductionBible:
        """Create a new version of the production bible.

        Deactivates the current active version and creates a new one
        with the provided fields merged on top of the previous version.
        """
        current = await self.get_active_bible(session, project_id)

        if current is None:
            # No existing bible — create version 1
            return await self.create_bible(
                session=session,
                project_id=project_id,
                characters=characters,
                objects=objects,
                locations=locations,
                voices=voices,
                pronunciation=pronunciation,
                style_rules=style_rules,
                world_rules=world_rules,
                approved_reference_assets=approved_reference_assets,
                change_log=change_log,
                created_by=created_by,
            )

        # Deactivate current version
        current.is_active = False
        session.add(current)

        # Merge: new values override old, absent fields inherit from current
        new_version = current.version + 1
        bible = ProductionBible(
            project_id=project_id,
            version=new_version,
            is_active=True,
            characters=characters if characters is not None else current.characters,
            objects=objects if objects is not None else current.objects,
            locations=locations if locations is not None else current.locations,
            voices=voices if voices is not None else current.voices,
            pronunciation=pronunciation if pronunciation is not None else current.pronunciation,
            style_rules=style_rules if style_rules is not None else current.style_rules,
            world_rules=world_rules if world_rules is not None else current.world_rules,
            approved_reference_assets=approved_reference_assets
            if approved_reference_assets is not None
            else current.approved_reference_assets,
            change_log=change_log,
            created_by=created_by,
        )
        session.add(bible)
        await session.commit()
        await session.refresh(bible)
        return bible

    async def delete_bible(
        self, session: AsyncSession, project_id: uuid.UUID
    ) -> bool:
        """Delete all production bible versions for a project."""
        result = await session.exec(
            select(ProductionBible).where(ProductionBible.project_id == project_id)
        )
        bibles = result.all()
        for bible in bibles:
            await session.delete(bible)
        await session.commit()
        return True


# ── Voice Casting ──


class VoiceCastingService:
    """Service for deterministic project-scoped voice casting.

    Voice assignment is stable across reruns because it's stored in the DB
    keyed by (project_id, character_name), NOT derived from hash(character_name).
    """

    # Default voice pool per provider (fallback when no explicit voice_id given)
    DEFAULT_VOICE_POOL: Dict[str, List[str]] = {
        "elevenlabs": [
            "21m00Tcm4TlvDq8ikWAM",  # Rachel
            "AZnzlk1XvdvUeBnXmlld",  # Domi
            "EXAVITQu4vr4xnSDxMaL",  # Bella
            "ErXwobaYiN019PkySvjV",  # Antoni
            "MF3mGyEYCl7XYWbV9V6O",  # Elli
            "TxGEqnHWrfWFTfGW9XjX",  # Josh
            "VR6AewLTigWG4xSOukaG",  # Arnold
            "pNInz6obpgDQGcFmaJgB",  # Adam
            "yoZ06aMxZJJ28mfd3POQ",  # Sam
        ],
        "openai": ["alloy", "echo", "fable", "onyx", "nova", "shimmer"],
        "google": [
            "en-US-Standard-A",
            "en-US-Standard-B",
            "en-US-Standard-C",
            "en-US-Standard-D",
            "en-US-Standard-E",
            "en-US-Standard-F",
            "en-US-Standard-G",
            "en-US-Standard-H",
            "en-US-Standard-I",
            "en-US-Standard-J",
        ],
    }

    @staticmethod
    def _deterministic_index(project_id: uuid.UUID, character_name: str, pool_size: int) -> int:
        """Compute a deterministic index into a voice pool.

        Uses SHA-256 of (project_id + character_name) to produce a stable
        but project-scoped index. Different projects get different voices
        for the same character name.
        """
        seed = f"{project_id}:{character_name}"
        digest = hashlib.sha256(seed.encode()).digest()
        index = int.from_bytes(digest[:4], "big") % pool_size
        return index

    async def cast_voice(
        self,
        session: AsyncSession,
        project_id: uuid.UUID,
        character_name: str,
        provider: str = "elevenlabs",
        voice_id: Optional[str] = None,
        model: Optional[str] = None,
        voice_metadata: Optional[Dict[str, Any]] = None,
        lock: bool = False,
    ) -> VoiceCasting:
        """Cast a voice for a character in a project.

        If voice_id is provided, use it directly.
        Otherwise, deterministically select from the provider's default pool.
        The result is stored in the DB and is stable across reruns.

        Returns existing casting if one already exists (idempotent).
        """
        # Check for existing casting
        existing = await self.get_casting(session, project_id, character_name)
        if existing is not None:
            # Update if unlocked and new voice_id provided
            if not existing.is_locked and voice_id is not None:
                existing.voice_id = voice_id
                existing.provider = provider
                existing.model = model
                if voice_metadata:
                    existing.voice_metadata = voice_metadata
                existing.is_locked = lock
                existing.updated_at = datetime.now(timezone.utc)
                session.add(existing)
                await session.commit()
                await session.refresh(existing)
            return existing

        # Determine voice_id if not provided
        if voice_id is None:
            pool = self.DEFAULT_VOICE_POOL.get(provider, self.DEFAULT_VOICE_POOL["elevenlabs"])
            idx = self._deterministic_index(project_id, character_name, len(pool))
            voice_id = pool[idx]

        casting = VoiceCasting(
            project_id=project_id,
            character_name=character_name,
            voice_id=voice_id,
            provider=provider,
            model=model,
            voice_metadata=voice_metadata or {},
            is_locked=lock,
        )
        session.add(casting)
        await session.commit()
        await session.refresh(casting)
        return casting

    async def get_casting(
        self, session: AsyncSession, project_id: uuid.UUID, character_name: str
    ) -> Optional[VoiceCasting]:
        """Get the voice casting for a specific character in a project."""
        result = await session.exec(
            select(VoiceCasting)
            .where(VoiceCasting.project_id == project_id)
            .where(VoiceCasting.character_name == character_name)
        )
        return result.first()

    async def list_castings(
        self, session: AsyncSession, project_id: uuid.UUID
    ) -> List[VoiceCasting]:
        """List all voice castings for a project."""
        result = await session.exec(
            select(VoiceCasting)
            .where(VoiceCasting.project_id == project_id)
            .order_by(VoiceCasting.character_name)
        )
        return list(result.all())

    async def update_casting(
        self,
        session: AsyncSession,
        project_id: uuid.UUID,
        character_name: str,
        voice_id: Optional[str] = None,
        provider: Optional[str] = None,
        model: Optional[str] = None,
        voice_metadata: Optional[Dict[str, Any]] = None,
        lock: Optional[bool] = None,
    ) -> Optional[VoiceCasting]:
        """Update an existing voice casting. Refuses if locked."""
        casting = await self.get_casting(session, project_id, character_name)
        if casting is None:
            return None
        if casting.is_locked:
            raise ValueError(
                f"Voice casting for '{character_name}' is locked. Unlock first."
            )
        if voice_id is not None:
            casting.voice_id = voice_id
        if provider is not None:
            casting.provider = provider
        if model is not None:
            casting.model = model
        if voice_metadata is not None:
            casting.voice_metadata = voice_metadata
        if lock is not None:
            casting.is_locked = lock
        casting.updated_at = datetime.now(timezone.utc)
        session.add(casting)
        await session.commit()
        await session.refresh(casting)
        return casting

    async def delete_casting(
        self, session: AsyncSession, project_id: uuid.UUID, character_name: str
    ) -> bool:
        """Delete a voice casting entry."""
        casting = await self.get_casting(session, project_id, character_name)
        if casting is None:
            return False
        await session.delete(casting)
        await session.commit()
        return True

    async def bulk_cast(
        self,
        session: AsyncSession,
        project_id: uuid.UUID,
        character_names: List[str],
        provider: str = "elevenlabs",
        lock: bool = False,
    ) -> List[VoiceCasting]:
        """Cast voices for multiple characters at once."""
        results = []
        for name in character_names:
            casting = await self.cast_voice(
                session=session,
                project_id=project_id,
                character_name=name,
                provider=provider,
                lock=lock,
            )
            results.append(casting)
        return results


# ── Dialogue Manifest ──


class DialogueManifestService:
    """Service for immutable dialogue manifests.

    Links approved text → speaker → audio → subtitle → lip-sync → merge output.
    Records are immutable once finalized.
    """

    @staticmethod
    def _compute_content_hash(scene_id: str, speaker: str, text: str) -> str:
        """Compute a SHA-256 content hash for immutability verification."""
        payload = json.dumps(
            {"scene_id": scene_id, "speaker": speaker, "text": text},
            sort_keys=True,
        )
        return hashlib.sha256(payload.encode()).hexdigest()

    async def create_manifest(
        self,
        session: AsyncSession,
        project_id: uuid.UUID,
        scene_id: str,
        speaker: str,
        text: str,
        sequence_order: int = 0,
        video_generation_id: Optional[uuid.UUID] = None,
        voice_id: Optional[str] = None,
        voice_provider: Optional[str] = None,
        scene_state: Optional[Dict[str, Any]] = None,
        previous_frame_url: Optional[str] = None,
        continuity_frame_url: Optional[str] = None,
    ) -> DialogueManifest:
        """Create a new dialogue manifest entry.

        The content_hash ensures uniqueness — identical text+speaker+scene_id
        will produce the same hash, preventing duplicates.
        """
        content_hash = self._compute_content_hash(scene_id, speaker, text)

        # Check for existing entry with same hash
        existing = await session.exec(
            select(DialogueManifest).where(
                DialogueManifest.content_hash == content_hash
            )
        )
        if existing.first() is not None:
            return existing.first()

        manifest = DialogueManifest(
            project_id=project_id,
            video_generation_id=video_generation_id,
            content_hash=content_hash,
            scene_id=scene_id,
            speaker=speaker,
            text=text,
            sequence_order=sequence_order,
            voice_id=voice_id,
            voice_provider=voice_provider,
            scene_state=scene_state or {},
            previous_frame_url=previous_frame_url,
            continuity_frame_url=continuity_frame_url,
            status="pending",
            is_finalized=False,
        )
        session.add(manifest)
        await session.commit()
        await session.refresh(manifest)
        return manifest

    async def get_manifest(
        self, session: AsyncSession, manifest_id: uuid.UUID
    ) -> Optional[DialogueManifest]:
        """Get a dialogue manifest by ID."""
        result = await session.exec(
            select(DialogueManifest).where(DialogueManifest.id == manifest_id)
        )
        return result.first()

    async def get_manifest_by_hash(
        self, session: AsyncSession, content_hash: str
    ) -> Optional[DialogueManifest]:
        """Get a dialogue manifest by content hash."""
        result = await session.exec(
            select(DialogueManifest).where(
                DialogueManifest.content_hash == content_hash
            )
        )
        return result.first()

    async def list_manifests(
        self,
        session: AsyncSession,
        project_id: uuid.UUID,
        scene_id: Optional[str] = None,
        video_generation_id: Optional[uuid.UUID] = None,
    ) -> List[DialogueManifest]:
        """List dialogue manifests for a project, optionally filtered."""
        query = select(DialogueManifest).where(
            DialogueManifest.project_id == project_id
        )
        if scene_id is not None:
            query = query.where(DialogueManifest.scene_id == scene_id)
        if video_generation_id is not None:
            query = query.where(
                DialogueManifest.video_generation_id == video_generation_id
            )
        query = query.order_by(DialogueManifest.sequence_order)
        result = await session.exec(query)
        return list(result.all())

    async def link_audio(
        self,
        session: AsyncSession,
        manifest_id: uuid.UUID,
        audio_url: str,
        audio_duration_seconds: Optional[float] = None,
        audio_generation_id: Optional[uuid.UUID] = None,
    ) -> Optional[DialogueManifest]:
        """Link generated audio to a dialogue manifest entry."""
        manifest = await self.get_manifest(session, manifest_id)
        if manifest is None:
            return None
        if manifest.is_finalized:
            raise ValueError("Cannot modify a finalized dialogue manifest.")
        manifest.audio_url = audio_url
        manifest.audio_duration_seconds = audio_duration_seconds
        manifest.audio_generation_id = audio_generation_id
        manifest.status = "audio_linked"
        manifest.updated_at = datetime.now(timezone.utc)
        session.add(manifest)
        await session.commit()
        await session.refresh(manifest)
        return manifest

    async def link_subtitle(
        self,
        session: AsyncSession,
        manifest_id: uuid.UUID,
        subtitle_url: str,
        subtitle_format: str = "srt",
    ) -> Optional[DialogueManifest]:
        """Link generated subtitles to a dialogue manifest entry."""
        manifest = await self.get_manifest(session, manifest_id)
        if manifest is None:
            return None
        if manifest.is_finalized:
            raise ValueError("Cannot modify a finalized dialogue manifest.")
        manifest.subtitle_url = subtitle_url
        manifest.subtitle_format = subtitle_format
        manifest.status = "subtitle_linked"
        manifest.updated_at = datetime.now(timezone.utc)
        session.add(manifest)
        await session.commit()
        await session.refresh(manifest)
        return manifest

    async def link_lip_sync(
        self,
        session: AsyncSession,
        manifest_id: uuid.UUID,
        lip_sync_url: str,
        lip_sync_status: str = "completed",
    ) -> Optional[DialogueManifest]:
        """Link lip-sync output to a dialogue manifest entry."""
        manifest = await self.get_manifest(session, manifest_id)
        if manifest is None:
            return None
        if manifest.is_finalized:
            raise ValueError("Cannot modify a finalized dialogue manifest.")
        manifest.lip_sync_url = lip_sync_url
        manifest.lip_sync_status = lip_sync_status
        manifest.status = "lipsync_linked"
        manifest.updated_at = datetime.now(timezone.utc)
        session.add(manifest)
        await session.commit()
        await session.refresh(manifest)
        return manifest

    async def link_merge_output(
        self,
        session: AsyncSession,
        manifest_id: uuid.UUID,
        merge_output_url: str,
        merge_status: str = "completed",
    ) -> Optional[DialogueManifest]:
        """Link final merge output to a dialogue manifest entry."""
        manifest = await self.get_manifest(session, manifest_id)
        if manifest is None:
            return None
        if manifest.is_finalized:
            raise ValueError("Cannot modify a finalized dialogue manifest.")
        manifest.merge_output_url = merge_output_url
        manifest.merge_status = merge_status
        manifest.status = "merged"
        manifest.updated_at = datetime.now(timezone.utc)
        session.add(manifest)
        await session.commit()
        await session.refresh(manifest)
        return manifest

    async def finalize_manifest(
        self, session: AsyncSession, manifest_id: uuid.UUID
    ) -> Optional[DialogueManifest]:
        """Finalize a dialogue manifest — makes it immutable."""
        manifest = await self.get_manifest(session, manifest_id)
        if manifest is None:
            return None
        manifest.is_finalized = True
        manifest.status = "finalized"
        manifest.updated_at = datetime.now(timezone.utc)
        session.add(manifest)
        await session.commit()
        await session.refresh(manifest)
        return manifest

    async def preserve_scene_state(
        self,
        session: AsyncSession,
        project_id: uuid.UUID,
        scene_id: str,
        scene_state: Dict[str, Any],
        continuity_frame_url: Optional[str] = None,
    ) -> Optional[DialogueManifest]:
        """Preserve scene state for previous-frame chaining.

        Updates the most recent dialogue manifest for the given scene
        with the current scene state and continuity frame.
        """
        result = await session.exec(
            select(DialogueManifest)
            .where(DialogueManifest.project_id == project_id)
            .where(DialogueManifest.scene_id == scene_id)
            .order_by(DialogueManifest.sequence_order.desc())
            .limit(1)
        )
        manifest = result.first()
        if manifest is None:
            return None
        manifest.scene_state = scene_state
        if continuity_frame_url:
            manifest.continuity_frame_url = continuity_frame_url
        manifest.updated_at = datetime.now(timezone.utc)
        session.add(manifest)
        await session.commit()
        await session.refresh(manifest)
        return manifest

    async def get_previous_frame(
        self,
        session: AsyncSession,
        project_id: uuid.UUID,
        scene_id: str,
    ) -> Optional[Dict[str, Any]]:
        """Get the previous frame state for a scene (for chaining)."""
        result = await session.exec(
            select(DialogueManifest)
            .where(DialogueManifest.project_id == project_id)
            .where(DialogueManifest.scene_id == scene_id)
            .order_by(DialogueManifest.sequence_order.desc())
            .limit(1)
        )
        manifest = result.first()
        if manifest is None:
            return None
        return {
            "scene_state": manifest.scene_state,
            "continuity_frame_url": manifest.continuity_frame_url,
            "previous_frame_url": manifest.previous_frame_url,
        }


# ── Singleton instances ──

production_bible_service = ProductionBibleService()
voice_casting_service = VoiceCastingService()
dialogue_manifest_service = DialogueManifestService()
